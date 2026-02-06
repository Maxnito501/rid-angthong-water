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
    """ฟังก์ชันสำหรับดึงวันที่ปัจจุบันในรูปแบบภาษาไทย"""
    months = [
        "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    now = datetime.now()
    day = now.day
    month = months[now.month - 1]
    year = now.year + 543
    return f"{day} {month} {year}"

def parse_text(text):
    data = {}
    
    # ใช้ค่าวันที่ปัจจุบันเป็นหลักตามที่พี่โบ้สั่ง
    data['date'] = get_thai_date()
    
    # ข้อ 1: ปริมาณฝน
    if "ไม่มีฝน" in text:
        data['rain_val'] = "-"
        data['has_rain'] = False
    else:
        rain_match = re.search(r"(\d+\.?\d*)\s*ม\.ม\.", text)
        if rain_match:
            data['rain_val'] = f"{rain_match.group(1)} มม."
            data['has_rain'] = True
        else:
            data['rain_val'] = "-"
            data['has_rain'] = False
    
    # ข้อ 2: ดึงค่าระดับน้ำและผลต่าง
    def extract_level(key_word, text):
        pattern = rf"{key_word}.*?ระดับน้ำ\s*[\+]\s*([\d\.\s]+).*?\(([\+\-\d\.\s]+)\s*ม\.\)"
        match = re.search(pattern, text, re.S | re.IGNORECASE)
        if match:
            val = float(match.group(1).replace(" ", ""))
            diff = float(match.group(2).replace(" ", ""))
            return val, diff
        return 0.0, 0.0

    def extract_flow(key_word, text):
        pattern = rf"{key_word}.*?(?:มีปริมาณน้ำไหลผ่าน|ปริมาณน้ำผ่าน|ปริมาณ)\s*([\d\.\-\s]+)\s*(?:ลบ\.ม\./วิ|ลบ\.ม\./วินาที|ลม\.ม/วินาที)"
        match = re.search(pattern, text, re.S | re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            return val if val != "-" else "-"
        return "-"

    data['c7a'] = extract_level("C7A", text)
    data['c7a_q'] = extract_flow("C7A", text)
    data['wat'] = extract_level("วัดตูม", text)
    data['bak'] = extract_level("บางจัก", text)

    # ข้อ 3 & 4: สถานการณ์อ่างเก็บน้ำและอุทกภัย
    res_match = re.search(r"3\..*?\n(.*?)\n", text, re.S)
    res_status = res_match.group(1).strip() if res_match else "ไม่มีอ่างเก็บน้ำในพื้นที่"
    # ตัดคำว่า "ดังนี้" ออกจากข้อความถ้ามีหลุดมา
    data['reservoir_status'] = res_status.replace("ดังนี้", "").strip()
    
    flood_match = re.search(r"4\..*?\n(.*?)\n", text, re.S)
    flood_status = flood_match.group(1).strip() if flood_match else "-"
    if flood_status in ["-", "", "ดังนี้"]: 
        data['flood_status'] = "ปกติ (ไม่มีรายงานอุทกภัย)"
    else:
        data['flood_status'] = flood_status.replace("ดังนี้", "").strip()

    return data

def draw_dashboard(data, font_path="THSarabunNew.ttf"):
    w, h = 1200, 1500
    img = Image.new('RGB', (w, h), color='#1e1e2e')
    draw = ImageDraw.Draw(img)

    try:
        f_title = ImageFont.truetype(font_path, 60)
        f_sub = ImageFont.truetype(font_path, 40)
        f_label = ImageFont.truetype(font_path, 45)
        f_val = ImageFont.truetype(font_path, 45)
        f_diff = ImageFont.truetype(font_path, 35)
        f_info = ImageFont.truetype(font_path, 38)
        f_rain_icon = ImageFont.truetype(font_path, 80)
        f_rain_val = ImageFont.truetype(font_path, 50)
        f_status_icon = ImageFont.truetype(font_path, 60)
    except:
        f_title = f_sub = f_label = f_val = f_diff = f_info = f_rain_icon = f_rain_val = f_status_icon = None

    # --- Header ---
    draw.rectangle([0, 0, w, 320], fill="#11111b")
    draw.text((w/2, 60), "รายงานสถานการณ์น้ำรายวัน จังหวัดอ่างทอง", fill="#89b4fa", font=f_title, anchor="mm")
    # เปลี่ยนจาก "ข้อมูล" เป็น "ณ วันที่" ตามที่พี่โบ้สั่ง
    draw.text((w/2, 120), f"ณ วันที่ {data['date']}", fill="#f9e2af", font=f_sub, anchor="mm")
    
    # --- ข้อ 1: ปริมาณฝน ---
    rain_box_x = w/2
    rain_box_y = 220
    icon_rain = "🌧" if data['has_rain'] else "☁️"
    draw.text((rain_box_x, rain_box_y), icon_rain, fill="#89b4fa", font=f_rain_icon, anchor="mm")
    draw.text((rain_box_x, rain_box_y + 60), data['rain_val'], fill="#ffffff", font=f_rain_val, anchor="mm")
    draw.text((rain_box_x - 120, rain_box_y + 30), "ปริมาณฝน", fill="#585b70", font=f_sub, anchor="rm")

    # --- Main Gauges (ระดับน้ำ 3 สถานี) ---
    col_w = w // 3
    for i, key in enumerate(['c7a', 'wat', 'bak']):
        st_info = STATIONS_CONFIG[key]
        st_val, st_diff = data[key]
        curr_x = (i * col_w) + (col_w / 2)
        
        draw.rounded_rectangle([i*col_w+30, 350, (i+1)*col_w-30, 1080], radius=30, fill="#181825")
        draw.text((curr_x, 410), st_info['label'], fill="#cdd6f4", font=f_label, anchor="mm")

        t_x1, t_y1, t_x2, t_y2 = curr_x-60, 500, curr_x+60, 850
        draw.rectangle([t_x1-5, t_y1-5, t_x2+5, t_y2+5], fill="#313244")
        
        ratio = min(st_val / st_info['max'], 1.0)
        w_top = t_y2 - ((t_y2-t_y1) * ratio)
        draw.rectangle([t_x1, w_top, t_x2, t_y2], fill=st_info['color'])

        b_ratio = st_info['bank'] / st_info['max']
        b_y = t_y2 - ((t_y2-t_y1) * b_ratio)
        draw.line([t_x1-30, b_y, t_x2+30, b_y], fill="#f38ba8", width=6)
        draw.text((t_x2+40, b_y), f"ตลิ่ง {st_info['bank']:.2f}", fill="#f38ba8", font=f_diff, anchor="lm")

        draw.text((curr_x, 920), f"+{st_val:.2f} ม.รทก.", fill="#cdd6f4", font=f_val, anchor="mm")
        diff_color = "#f38ba8" if st_diff > 0 else ("#89b4fa" if st_diff < 0 else "#bac2de")
        draw.text((curr_x, 975), f"({st_diff:+.2f} ม.)", fill=diff_color, font=f_diff, anchor="mm")
        
        if key == 'c7a':
            flow_val = data.get('c7a_q', '-')
            draw.text((curr_x, 1030), f"{flow_val} ลบ.ม./วิ", fill="#a6e3a1", font=f_info, anchor="mm")

    # --- ส่วนข้อมูลสรุปด้านล่าง (Infographic Style) ---
    info_y = 1130
    # Card อ่างเก็บน้ำ
    draw.rounded_rectangle([50, info_y, w/2 - 20, info_y + 220], radius=25, fill="#11111b", outline="#313244")
    draw.text((w/4 + 15, info_y + 60), "🚫", font=f_status_icon, anchor="mm")
    draw.text((w/4 + 15, info_y + 130), "อ่างเก็บน้ำ", fill="#89b4fa", font=f_label, anchor="mm")
    draw.text((w/4 + 15, info_y + 185), data['reservoir_status'], fill="#bac2de", font=f_info, anchor="mm")

    # Card สถานการณ์อุทกภัย
    draw.rounded_rectangle([w/2 + 20, info_y, w - 50, info_y + 220], radius=25, fill="#11111b", outline="#313244")
    draw.text((3*w/4 - 15, info_y + 60), "✅", font=f_status_icon, anchor="mm")
    draw.text((3*w/4 - 15, info_y + 130), "สถานการณ์อุทกภัย", fill="#a6e3a1", font=f_label, anchor="mm")
    draw.text((3*w/4 - 15, info_y + 185), data['flood_status'], fill="#bac2de", font=f_info, anchor="mm")

    # Footer
    draw.text((w/2, h-60), "โครงการชลประทานอ่างทอง สำนักงานชลประทานที่ 12", fill="#585b70", font=f_sub, anchor="mm")

    return img

# --- Streamlit UI ---
st.set_page_config(page_title="RID Ang Thong Dashboard", layout="wide")

st.title("🌊 RID Ang Thong Smart Dashboard v1.4")
st.markdown(f"ระบบรายงานน้ำประจำตำบล (คู่คิดพี่โบ้) | อัปเดตล่าสุด: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

col1, col2 = st.columns([1, 1.5])

with col1:
    report_input = st.text_area("วางข้อความรายงานที่นี่:", height=550, placeholder="คัดลอกข้อความรายงานประจำวันมาวางที่นี่...")
    process_btn = st.button("🚀 ประมวลผลและสร้างภาพ", use_container_width=True)

with col2:
    if process_btn and report_input:
        with st.spinner('กำลังสร้างกราฟิก...'):
            data = parse_text(report_input)
            img = draw_dashboard(data)
            
            st.image(img, caption=f"พรีวิวรายงานประจำวันที่ {data['date']}", use_column_width=True)
            
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.download_button(
                label="💾 ดาวน์โหลดรูปภาพ PNG",
                data=byte_im,
                file_name=f"RID_AngThong_Report_{data['date'].replace(' ', '_')}.png",
                mime="image/png",
                use_container_width=True
            )
    else:
        st.info("💡 พี่โบ้วางข้อความรายงานทางซ้ายมือ แล้วกดปุ่มประมวลผลได้เลยครับ")

st.divider()
st.caption("พัฒนาโดยคู่คิด AI เพื่อสนับสนุนงานวิศวกรรมชลประทานอ่างทอง")
