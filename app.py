import streamlit as st
import re
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

# --- การตั้งค่าสถานีและเกณฑ์วิศวกรรม ---
STATIONS_CONFIG = {
    'c7a': {'label': 'C.7A เจ้าพระยา', 'bank': 10.00, 'max': 12.0, 'color': '#3498db'},
    'wat': {'label': 'แม่น้ำน้อย (วัดตูม)', 'bank': 6.50, 'max': 8.0, 'color': '#2ecc71'},
    'bak': {'label': 'แม่น้ำน้อย (บางจัก)', 'bank': 5.00, 'max': 6.5, 'color': '#e67e22'}
}

def get_thai_date():
    """ดึงวันที่ปัจจุบันรูปแบบไทย"""
    months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
    now = datetime.now()
    return f"{now.day} {months[now.month - 1]} {now.year + 543}"

def parse_report(manual_text, c7a_auto_data=None):
    """ฟังก์ชันดึงข้อมูลแบบผสม (Manual + Auto)"""
    data = {'date': get_thai_date()}
    
    # 1. จัดการข้อมูลฝน
    if "ไม่มีฝน" in manual_text:
        data['rain_val'], data['has_rain'] = "-", False
    else:
        rain_match = re.search(r"(\d+\.?\d*)\s*ม\.ม\.", manual_text)
        data['rain_val'] = f"{rain_match.group(1)} มม." if rain_match else "-"
        data['has_rain'] = True if rain_match else False

    # 2. จัดการระดับน้ำ (Regex)
    def extract_val(key, text):
        p_lvl = rf"{key}.*?ระดับน้ำ\s*[\+]\s*([\d\.\s]+).*?\(([\+\-\d\.\s]+)\s*ม\.\)"
        p_q = rf"{key}.*?(?:มีปริมาณน้ำไหลผ่าน|ปริมาณน้ำผ่าน|ปริมาณ)\s*([\d\.\-\s,]+)\s*(?:ลบ\.ม\./วิ|ลบ\.ม\./วินาที|ลม\.ม/วินาที)"
        m_lvl = re.search(p_lvl, text, re.S | re.IGNORECASE)
        m_q = re.search(p_q, text, re.S | re.IGNORECASE)
        lvl = float(m_lvl.group(1).replace(" ", "")) if m_lvl else 0.0
        diff = float(m_lvl.group(2).replace(" ", "")) if m_lvl else 0.0
        q = m_q.group(1).strip() if m_q else "-"
        return lvl, diff, q

    data['wat'] = extract_val("วัดตูม", manual_text)[:2]
    data['bak'] = extract_val("บางจัก", manual_text)[:2]

    if c7a_auto_data:
        data['c7a'] = (c7a_auto_data['level'], c7a_auto_data['diff'])
        data['c7a_q'] = c7a_auto_data['q']
    else:
        c7a_vals = extract_val("C7A", manual_text)
        data['c7a'] = (c7a_vals[0], c7a_vals[1])
        data['c7a_q'] = c7a_vals[2]

    res_match = re.search(r"3\..*?\n(.*?)\n", manual_text, re.S)
    data['reservoir_status'] = res_match.group(1).replace("ดังนี้", "").strip() if res_match else "ไม่มีอ่างเก็บน้ำในพื้นที่"
    
    flood_match = re.search(r"4\..*?\n(.*?)\n", manual_text, re.S)
    data['flood_status'] = flood_match.group(1).replace("ดังนี้", "").strip() if flood_match else "ปกติ (ไม่มีรายงานอุทกภัย)"
    return data

def get_status_color(lvl, bank):
    """คำนวณสีสถานะตามระดับความเสี่ยง (Presentation Logic)"""
    if lvl >= bank:
        return "#f38ba8" # สีแดง (ล้นตลิ่ง)
    elif lvl >= bank * 0.8:
        return "#f9e2af" # สีเหลือง (เฝ้าระวัง)
    return "#89b4fa"     # สีฟ้า (ปกติ)

def draw_dashboard(data, font_path="THSarabunNew.ttf"):
    w, h = 1200, 1500
    img = Image.new('RGB', (w, h), color='#1e1e2e')
    draw = ImageDraw.Draw(img)

    try:
        f_title = ImageFont.truetype(font_path, 65)
        f_sub = ImageFont.truetype(font_path, 40)
        f_label = ImageFont.truetype(font_path, 45)
        f_val = ImageFont.truetype(font_path, 45)
        f_diff = ImageFont.truetype(font_path, 35)
        f_info = ImageFont.truetype(font_path, 38)
        f_rain_icon = ImageFont.truetype(font_path, 90)
        f_rain_val = ImageFont.truetype(font_path, 50)
        f_status_icon = ImageFont.truetype(font_path, 65)
    except:
        f_title = f_sub = f_label = f_val = f_diff = f_info = f_rain_icon = f_rain_val = f_status_icon = None

    # Header Section
    draw.rectangle([0, 0, w, 320], fill="#11111b")
    draw.text((w/2, 70), "รายงานสถานการณ์น้ำรายวัน จังหวัดอ่างทอง", fill="#89b4fa", font=f_title, anchor="mm")
    draw.text((w/2, 135), f"ณ วันที่ {data['date']}", fill="#f9e2af", font=f_sub, anchor="mm")
    
    # Rain Graphic
    rain_x, rain_y = w/2, 230
    icon = "🌧" if data['has_rain'] else "☁️"
    draw.text((rain_x, rain_y), icon, fill="#89b4fa", font=f_rain_icon, anchor="mm")
    draw.text((rain_x, rain_y + 60), data['rain_val'], fill="#ffffff", font=f_rain_val, anchor="mm")
    draw.text((rain_x - 140, rain_y + 35), "ปริมาณฝน", fill="#585b70", font=f_sub, anchor="rm")

    # Stations Gauges
    col_w = w // 3
    for i, key in enumerate(['c7a', 'wat', 'bak']):
        st_info = STATIONS_CONFIG[key]
        st_lvl, st_diff = data[key]
        curr_x = (i * col_w) + (col_w / 2)
        
        # Risk color
        current_status_color = get_status_color(st_lvl, st_info['bank'])
        
        draw.rounded_rectangle([i*col_w+30, 350, (i+1)*col_w-30, 1080], radius=30, fill="#181825")
        draw.text((curr_x, 410), st_info['label'], fill="#cdd6f4", font=f_label, anchor="mm")

        t_x1, t_y1, t_x2, t_y2 = curr_x-60, 500, curr_x+60, 850
        draw.rectangle([t_x1-5, t_y1-5, t_x2+5, t_y2+5], fill="#313244")
        fill_ratio = min(st_lvl / st_info['max'], 1.0)
        w_top = t_y2 - ((t_y2-t_y1) * fill_ratio)
        draw.rectangle([t_x1, w_top, t_x2, t_y2], fill=current_status_color)

        b_y = t_y2 - ((t_y2-t_y1) * (st_info['bank'] / st_info['max']))
        draw.line([t_x1-30, b_y, t_x2+30, b_y], fill="#f38ba8", width=6)
        draw.text((t_x2+40, b_y), f"ตลิ่ง {st_info['bank']:.2f}", fill="#f38ba8", font=f_diff, anchor="lm")

        draw.text((curr_x, 920), f"+{st_lvl:.2f} ม.รทก.", fill="#cdd6f4", font=f_val, anchor="mm")
        color_diff = "#f38ba8" if st_diff > 0 else ("#89b4fa" if st_diff < 0 else "#bac2de")
        draw.text((curr_x, 975), f"({st_diff:+.2f} ม.)", fill=color_diff, font=f_diff, anchor="mm")
        
        if key == 'c7a':
            draw.text((curr_x, 1030), f"{data.get('c7a_q', '-')} ลบ.ม./วิ", fill="#a6e3a1", font=f_info, anchor="mm")

    # Bottom Cards
    info_y = 1130
    draw.rounded_rectangle([50, info_y, w/2 - 20, info_y + 220], radius=25, fill="#11111b", outline="#313244")
    draw.text((w/4 + 10, info_y + 60), "🚫", font=f_status_icon, anchor="mm")
    draw.text((w/4 + 10, info_y + 130), "อ่างเก็บน้ำ", fill="#89b4fa", font=f_label, anchor="mm")
    draw.text((w/4 + 10, info_y + 190), data['reservoir_status'], fill="#bac2de", font=f_info, anchor="mm")

    draw.rounded_rectangle([w/2 + 20, info_y, w - 50, info_y + 220], radius=25, fill="#11111b", outline="#313244")
    draw.text((3*w/4 - 10, info_y + 60), "✅", font=f_status_icon, anchor="mm")
    draw.text((3*w/4 - 10, info_y + 130), "สถานการณ์อุทกภัย", fill="#a6e3a1", font=f_label, anchor="mm")
    draw.text((3*w/4 - 10, info_y + 190), data['flood_status'], fill="#bac2de", font=f_info, anchor="mm")

    draw.text((w/2, h-60), "โครงการชลประทานอ่างทอง สำนักงานชลประทานที่ 12", fill="#585b70", font=f_sub, anchor="mm")
    return img

# --- Application UI ---
st.set_page_config(page_title="RID Ang Thong v1.6 Presentation", layout="wide")

st.title("🌊 RID Ang Thong Smart Dashboard v1.6")
st.subheader("Presentation Edition")

with st.sidebar:
    st.header("🏢 Concept Presentation")
    st.markdown("""
    **วิสัยทัศน์โครงการ:**
    1. **Digitization:** เปลี่ยนรายงานกระดาษ/LINE เป็น Data Visualization ทันที
    2. **Risk Analysis:** ระบบประเมินความเสี่ยงอัตโนมัติด้วยสี (Blue/Yellow/Red)
    3. **Scalability:** รองรับการต่อเชื่อมเซนเซอร์โทรมาตร (Telemetry) ในอนาคต
    
    *--- ข้อมูลสถานี C.7A ---*
    """)
    c7a_lvl = st.number_input("ระดับน้ำ C.7A (+ม.รทก.)", value=1.46, format="%.2f")
    c7a_diff = st.number_input("เทียบเมื่อวาน (+/-)", value=0.02, format="%.2f")
    c7a_q = st.text_input("ปริมาณน้ำไหลผ่าน (ลบ.ม./วิ)", value="130")
    use_auto_c7a = st.checkbox("ใช้ข้อมูล C.7A จากฝั่งนี้", value=True)

col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("📝 คัดลอกข้อมูลรายงาน")
    manual_input = st.text_area("วางข้อความจาก LINE:", height=500, placeholder="วางรายงานที่นี่...")
    process_btn = st.button("🚀 สร้าง Dashboard นำเสนอ", use_container_width=True)

with col2:
    if process_btn:
        auto_data = {'level': c7a_lvl, 'diff': c7a_diff, 'q': c7a_q} if use_auto_c7a else None
        with st.spinner('กำลังประมวลผลวิสัยทัศน์...'):
            report_data = parse_report(manual_input, auto_data)
            final_img = draw_dashboard(report_data)
            st.image(final_img, caption="สรุปสถานการณ์น้ำรายวัน (อัตโนมัติ)", use_column_width=True)
            buf = io.BytesIO()
            final_img.save(buf, format="PNG")
            st.download_button("💾 ดาวน์โหลดไฟล์นำเสนอ (PNG)", data=buf.getvalue(), 
                               file_name=f"RID_Presentation_{report_data['date']}.png", use_container_width=True)
    else:
        st.info("💡 พร้อมสำหรับการนำเสนอ: วางข้อมูลและกดปุ่มเพื่อเริ่มระบบ")

st.divider()
st.caption("RID Ang Thong Smart Solution | คู่คิดวิศวกรยุคใหม่")
