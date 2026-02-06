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

def parse_text(text):
    data = {}
    
    # ดึงวันที่รายงาน
    date_match = re.search(r"ประจำวันที่\s*(.*)", text)
    data['date'] = date_match.group(1).strip() if date_match else datetime.now().strftime("%d %B %Y")
    
    # ข้อ 1: ปริมาณฝน
    rain_date_match = re.search(r"วันที่\s*(\d+.*?)\n(.*?)\n", text)
    data['rain_info'] = rain_date_match.group(2).strip() if rain_date_match else "ไม่พบข้อมูลปริมาณฝน"
    
    # ข้อ 2: ดึงค่าระดับน้ำและผลต่าง
    def extract_level(key_word, text):
        pattern = rf"{key_word}.*?ระดับน้ำ\s*[\+]\s*([\d\.\s]+).*?\(([\+\-\d\.\s]+)\s*ม\.\)"
        match = re.search(pattern, text, re.S | re.IGNORECASE)
        if match:
            val = float(match.group(1).replace(" ", ""))
            diff = float(match.group(2).replace(" ", ""))
            return val, diff
        return 0.0, 0.0

    # ดึงปริมาณน้ำไหลผ่าน (Q)
    def extract_flow(key_word, text):
        pattern = rf"{key_word}.*?(?:มีปริมาณน้ำไหลผ่าน|ปริมาณน้ำผ่าน|ปริมาณ)\s*([\d\.\-\s]+)\s*(?:ลบ\.ม\./วิ|ลบ\.ม\./วินาที|ลม\.ม/วินาที)"
        match = re.search(pattern, text, re.S | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "-"

    data['c7a'] = extract_level("C7A", text)
    data['c7a_q'] = extract_flow("C7A", text)
    
    data['wat'] = extract_level("วัดตูม", text)
    
    data['bak'] = extract_level("บางจัก", text)
    
    # ดึงข้อมูล ปตร.ยางมณี
    yang_match = re.search(r"ปตร\.ยางมณี\s*\+\s*([\d\.]+).*?ท้ายปตร\.\+\s*([\d\.]+).*?ปริมาณน้ำผ่าน\s*([\d\.]+)", text, re.S)
    if yang_match:
        data['yang_up'] = yang_match.group(1)
        data['yang_down'] = yang_match.group(2)
        data['yang_q'] = yang_match.group(3)
    else:
        data['yang_up'] = data['yang_down'] = data['yang_q'] = "-"

    # ข้อ 3 & 4: สถานการณ์อ่างเก็บน้ำและอุทกภัย
    res_match = re.search(r"3\..*?\n(.*?)\n", text, re.S)
    data['reservoir_status'] = res_match.group(1).strip() if res_match else "ปกติ"
    
    flood_match = re.search(r"4\..*?\n(.*?)\n", text, re.S)
    data['flood_status'] = flood_match.group(1).strip() if flood_match else "-"
    if data['flood_status'] in ["-", ""]: data['flood_status'] = "ไม่มีรายงานอุทกภัยในพื้นที่"

    return data

def draw_dashboard(data, font_path="THSarabunNew.ttf"):
    w, h = 1200, 1600 # เพิ่มความสูงเพื่อรองรับข้อมูลใหม่
    img = Image.new('RGB', (w, h), color='#1e1e2e')
    draw = ImageDraw.Draw(img)

    try:
        f_title = ImageFont.truetype(font_path, 60)
        f_sub = ImageFont.truetype(font_path, 40)
        f_label = ImageFont.truetype(font_path, 45)
        f_val = ImageFont.truetype(font_path, 70)
        f_diff = ImageFont.truetype(font_path, 35)
        f_info = ImageFont.truetype(font_path, 38)
    except:
        f_title = f_sub = f_label = f_val = f_diff = f_info = None

    # --- Header ---
    draw.rectangle([0, 0, w, 280], fill="#11111b")
    draw.text((w/2, 70), "รายงานสถานการณ์น้ำรายวัน จังหวัดอ่างทอง", fill="#89b4fa", font=f_title, anchor="mm")
    draw.text((w/2, 140), f"ข้อมูล {data['date']}", fill="#f9e2af", font=f_sub, anchor="mm")
    
    # ข้อมูลฝน (ข้อ 1)
    rain_box = [100, 185, w-100, 255]
    draw.rounded_rectangle(rain_box, radius=15, fill="#181825", outline="#313244", width=2)
    draw.text((w/2, 220), f"🌧 ปริมาณฝน: {data['rain_info']}", fill="#cdd6f4", font=f_info, anchor="mm")

    # --- Main Gauges (ระดับน้ำ 3 สถานีหลัก) ---
    col_w = w // 3
    for i, key in enumerate(['c7a', 'wat', 'bak']):
        st_info = STATIONS_CONFIG[key]
        st_val, st_diff = data[key]
        curr_x = (i * col_w) + (col_w / 2)
        
        # Card
        draw.rounded_rectangle([i*col_w+30, 300, (i+1)*col_w-30, 1050], radius=30, fill="#181825")
        draw.text((curr_x, 360), st_info['label'], fill="#cdd6f4", font=f_label, anchor="mm")

        # Gauge Tank
        t_x1, t_y1, t_x2, t_y2 = curr_x-60, 450, curr_x+60, 850
        draw.rectangle([t_x1-5, t_y1-5, t_x2+5, t_y2+5], fill="#313244")
        
        # Water Fill
        ratio = min(st_val / st_info['max'], 1.0)
        w_top = t_y2 - ((t_y2-t_y1) * ratio)
        draw.rectangle([t_x1, w_top, t_x2, t_y2], fill=st_info['color'])

        # Bank Level Line
        b_ratio = st_info['bank'] / st_info['max']
        b_y = t_y2 - ((t_y2-t_y1) * b_ratio)
        draw.line([t_x1-30, b_y, t_x2+30, b_y], fill="#f38ba8", width=6)
        draw.text((t_x2+40, b_y), f"ตลิ่ง {st_info['bank']:.2f}", fill="#f38ba8", font=f_diff, anchor="lm")

        # Result Values
        draw.text((curr_x, 920), f"+{st_val:.2f} ม.รทก.", fill="#cdd6f4", font=f_val, anchor="mm")
        diff_color = "#f38ba8" if st_diff > 0 else ("#89b4fa" if st_diff < 0 else "#bac2de")
        draw.text((curr_x, 980), f"({st_diff:+.2f} ม.)", fill=diff_color, font=f_diff, anchor="mm")

    # --- ส่วนข้อมูลเพิ่มเติม (Discharge & Status) ---
    # ปตร.ยางมณี & C7A Flow
    info_y = 1100
    draw.rounded_rectangle([50, info_y, w-50, info_y + 180], radius=20, fill="#11111b", outline="#313244")
    
    flow_text = f"📍 อัตราการไหล C.7A: {data['c7a_q']} ลบ.ม./วิ  |  📍 ปตร.ยางมณี: เหนือ +{data['yang_up']} / ท้าย +{data['yang_down']} (Q={data['yang_q']})"
    draw.text((w/2, info_y + 50), flow_text, fill="#a6e3a1", font=f_info, anchor="mm")
    
    # ข้อ 3 & 4 สถานะอื่นๆ
    draw.text((100, info_y + 110), f"🏗 อ่างเก็บน้ำ: {data['reservoir_status']}", fill="#bac2de", font=f_info, anchor="lm")
    draw.text((100, info_y + 155), f"⚠️ อุทกภัย: {data['flood_status']}", fill="#f9e2af", font=f_info, anchor="lm")

    # Footer
    draw.text((w/2, h-50), "โครงการชลประทานอ่างทอง สำนักงานชลประทานที่ 12", fill="#585b70", font=f_sub, anchor="mm")

    return img

# --- Streamlit UI ---
st.set_page_config(page_title="RID Ang Thong Dashboard", layout="wide")

st.title("🌊 RID Ang Thong Smart Dashboard v1.1")
st.markdown("ระบบแปลงรายงานข้อความ LINE เป็น Infographic ครบวงจร (ปริมาณฝน/ระดับน้ำ/อุทกภัย)")

col1, col2 = st.columns([1, 1.5])

with col1:
    report_input = st.text_area("วางข้อความรายงานที่นี่:", height=500, placeholder="คัดลอกข้อความรายงานประจำวันมาวางที่นี่...")
    process_btn = st.button("🚀 ประมวลผลและสร้างภาพ", use_container_width=True)

with col2:
    if process_btn and report_input:
        with st.spinner('กำลังประมวลผลข้อมูลและสร้างกราฟิก...'):
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
        st.info("💡 คำแนะนำ: วางข้อความรายงานจาก LINE ทางซ้ายมือ แล้วกดปุ่มประมวลผลเพื่อดูตัวอย่างภาพ")

st.divider()
st.caption("พัฒนาโดยระบบ AI เพื่อสนับสนุนงานวิศวกรรมชลประทานอ่างทอง | รองรับการทำงานผ่านมือถือและแท็บเล็ต")
