import streamlit as st
import re
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

# --- การตั้งค่าสถานี ---
STATIONS_CONFIG = {
    'c7a': {'label': 'C.7A เจ้าพระยา', 'bank': 10.00, 'max': 12.0, 'color': '#3498db'},
    'wat': {'label': 'แม่น้ำน้อย (วัดตูม)', 'bank': 6.50, 'max': 8.0, 'color': '#2ecc71'},
    'bak': {'label': 'แม่น้ำน้อย (บางจัก)', 'bank': 5.00, 'max': 6.5, 'color': '#e67e22'}
}

def parse_text(text):
    data = {}
    date_match = re.search(r"ประจำวันที่\s*(.*)", text)
    data['date'] = date_match.group(1).strip() if date_match else datetime.now().strftime("%d %B %Y")
    
    def extract(key_word, text):
        pattern = rf"{key_word}.*?ระดับน้ำ\s*[\+]\s*([\d\.\s]+).*?\(([\+\-\d\.\s]+)\s*ม\.\)"
        match = re.search(pattern, text, re.S | re.IGNORECASE)
        if match:
            val = float(match.group(1).replace(" ", ""))
            diff = float(match.group(2).replace(" ", ""))
            return val, diff
        return 0.0, 0.0

    data['c7a'] = extract("C7A", text)
    data['wat'] = extract("วัดตูม", text)
    data['bak'] = extract("บางจัก", text)
    return data

def draw_dashboard(data, font_path="THSarabunNew.ttf"):
    w, h = 1200, 1200
    img = Image.new('RGB', (w, h), color='#1e1e2e')
    draw = ImageDraw.Draw(img)

    try:
        f_title = ImageFont.truetype(font_path, 60)
        f_sub = ImageFont.truetype(font_path, 40)
        f_label = ImageFont.truetype(font_path, 45)
        f_val = ImageFont.truetype(font_path, 70)
        f_diff = ImageFont.truetype(font_path, 40)
    except:
        # กรณีหาฟอนต์ไม่เจอให้ใช้ฟอนต์พื้นฐาน
        f_title = f_sub = f_label = f_val = f_diff = None

    # Header
    draw.rectangle([0, 0, w, 220], fill="#11111b")
    draw.text((w/2, 80), "รายงานสถานการณ์น้ำรายวัน จ.อ่างทอง", fill="#89b4fa", font=f_title, anchor="mm")
    draw.text((w/2, 160), f"ข้อมูล {data['date']}", fill="#f9e2af", font=f_sub, anchor="mm")

    col_w = w // 3
    for i, key in enumerate(['c7a', 'wat', 'bak']):
        st_info = STATIONS_CONFIG[key]
        st_val, st_diff = data[key]
        curr_x = (i * col_w) + (col_w / 2)
        
        # Card
        draw.rounded_rectangle([i*col_w+30, 250, (i+1)*col_w-30, 1150], radius=30, fill="#181825")
        draw.text((curr_x, 320), st_info['label'], fill="#cdd6f4", font=f_label, anchor="mm")

        # Gauge Tank
        t_x1, t_y1, t_x2, t_y2 = curr_x-60, 420, curr_x+60, 950
        draw.rectangle([t_x1-5, t_y1-5, t_x2+5, t_y2+5], fill="#313244")
        
        # Water Level
        ratio = min(st_val / st_info['max'], 1.0)
        w_top = t_y2 - ((t_y2-t_y1) * ratio)
        draw.rectangle([t_x1, w_top, t_x2, t_y2], fill=st_info['color'])

        # Bank Level Line
        b_ratio = st_info['bank'] / st_info['max']
        b_y = t_y2 - ((t_y2-t_y1) * b_ratio)
        draw.line([t_x1-30, b_y, t_x2+30, b_y], fill="#f38ba8", width=6)
        draw.text((t_x2+40, b_y), f"ตลิ่ง {st_info['bank']:.2f}", fill="#f38ba8", font=f_diff, anchor="lm")

        # Result Values
        draw.text((curr_x, 1020), f"+{st_val:.2f} ม.รทก.", fill="#cdd6f4", font=f_val, anchor="mm")
        diff_color = "#f38ba8" if st_diff > 0 else ("#89b4fa" if st_diff < 0 else "#bac2de")
        draw.text((curr_x, 1090), f"({st_diff:+.2f} ม.)", fill=diff_color, font=f_diff, anchor="mm")

    return img

# --- Streamlit UI ---
st.set_page_config(page_title="RID Ang Thong Dashboard", layout="wide")

st.title("🌊 RID Ang Thong Smart Dashboard")
st.markdown("วางข้อความรายงานจาก LINE เพื่อสร้าง Infographic สำหรับผู้บริหาร")

col1, col2 = st.columns([1, 1.5])

with col1:
    report_input = st.text_area("วางข้อความที่นี่:", height=450, placeholder="คัดลอกรายงานจาก LINE มาวางที่นี่...")
    process_btn = st.button("ประมวลผลและสร้างรูปภาพ", use_container_width=True)

with col2:
    if process_btn and report_input:
        data = parse_text(report_input)
        img = draw_dashboard(data)
        
        # แสดงรูป Preview
        st.image(img, caption=f"พรีวิวรายงานประจำวันที่ {data['date']}", use_column_width=True)
        
        # เตรียมไฟล์สำหรับดาวน์โหลด
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        byte_im = buf.getvalue()
        
        st.download_button(
            label="💾 ดาวน์โหลดรูปภาพ PNG",
            data=byte_im,
            file_name=f"Water_Report_{data['date'].replace(' ', '_')}.png",
            mime="image/png",
            use_container_width=True
        )
    else:
        st.info("กรุณาวางข้อความและกดปุ่มด้านซ้ายเพื่อดูพรีวิว")

st.divider()
st.caption("พัฒนาโดยระบบ AI เพื่อยกระดับงานวิศวกรรมชลประทานอ่างทอง")
