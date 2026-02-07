import streamlit as st
import re
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

# --- Configuration & Theme Settings ---
STATIONS_CONFIG = {
    'c7a': {'label': 'ม.เจ้าพระยา (C.7A)', 'bank': 10.00, 'max': 12.0, 'color': '#007BFF'},
    'wat': {'label': 'ม.น้อย (วัดตูม)', 'bank': 6.50, 'max': 8.0, 'color': '#28A745'},
    'bak': {'label': 'ม.น้อย (บางจัก)', 'bank': 5.00, 'max': 6.5, 'color': '#E67E22'}
}

BG_COLOR_HEX = '#B3E5FC' 
HEADER_COLOR = "#01579B" 

def get_thai_date():
    months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
    now = datetime.now()
    return f"{now.day} {months[now.month - 1]} {now.year + 543}"

def parse_report(manual_text, c7a_auto_data=None, manual_flood=False, manual_reservoir=False):
    data = {'date': get_thai_date()}
    
    # 1. Rain Data
    if "ไม่มีฝน" in manual_text:
        data['rain_val'], data['has_rain'] = "-", False
    else:
        rain_match = re.search(r"(\d+\.?\d*)\s*ม\.ม\.", manual_text)
        data['rain_val'] = f"{rain_match.group(1)} มม." if rain_match else "-"
        data['has_rain'] = True if rain_match else False

    # 2. Water Level Data
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

    # 3. สถานะอ่างและอุทกภัย (ใช้ค่าจาก Sidebar ที่พี่โบ้เลือก)
    data['has_flood'] = manual_flood
    data['has_reservoir'] = manual_reservoir

    return data

# --- Custom Drawing Helpers ---
def draw_rain_icon(draw, x, y, size, color):
    draw.ellipse([x-size//2, y-size//3, x, y+size//4], fill=color)
    draw.ellipse([x-size//4, y-size//2, x+size//2, y+size//4], fill=color)
    for i in range(3):
        dx = (i-1) * (size//3)
        draw.line([x+dx, y+size//3, x+dx-5, y+size//2+5], fill=color, width=4)

def draw_no_icon(draw, x, y, size, color):
    draw.ellipse([x-size//2, y-size//2, x+size//2, y+size//2], outline=color, width=6)
    draw.line([x-size//3, y-size//3, x+size//3, y+size//3], fill=color, width=6)

def draw_location_pin(draw, x, y, size, color):
    draw.ellipse([x-size//4, y-size//2, x+size//4, y], fill=color)
    draw.polygon([x-size//4, y-size//4, x+size//4, y-size//4, x, y+size//4], fill=color)

def draw_report_book(draw, x, y, size, color):
    # วาดรูปหนังสือเปิดท้ายชื่อทีม
    draw.rectangle([x-size//2, y-size//3, x+size//2, y+size//3], outline=color, width=3)
    draw.line([x, y-size//3, x, y+size//3], fill=color, width=3)
    draw.line([x+10, y-10, x+size//2-5, y-10], fill=color, width=2)
    draw.line([x+10, y+10, x+size//2-5, y+10], fill=color, width=2)

def draw_dashboard(data, font_path="THSarabunNew.ttf"):
    w, h = 1200, 1550
    img = Image.new('RGB', (w, h), color=BG_COLOR_HEX)
    draw = ImageDraw.Draw(img)

    try:
        f_title = ImageFont.truetype(font_path, 80)
        f_sub = ImageFont.truetype(font_path, 45)
        f_label = ImageFont.truetype(font_path, 50) 
        f_val = ImageFont.truetype(font_path, 50) 
        f_diff = ImageFont.truetype(font_path, 40)
        f_info = ImageFont.truetype(font_path, 42)
        f_rain_val = ImageFont.truetype(font_path, 75)
        f_alert = ImageFont.truetype(font_path, 65)
    except:
        f_title = f_sub = f_label = f_val = f_diff = f_info = f_rain_val = f_alert = None

    # Header
    draw.rectangle([0, 0, w, 360], fill=HEADER_COLOR)
    draw.text((w/2, 85), "โครงการชลประทานอ่างทอง สำนักงานชลประทานที่ 12", fill="#FFFFFF", font=f_sub, anchor="mm")
    draw.text((w/2, 175), "รายงานสถานการณ์น้ำรายวัน", fill="#FFFFFF", font=f_title, anchor="mm")
    draw.text((w/2, 265), f"ณ วันที่ {data['date']}", fill="#FFEA00", font=f_sub, anchor="mm")
    
    # Rain Section
    rain_card_y = 315
    draw.rounded_rectangle([w/2 - 280, rain_card_y, w/2 + 280, rain_card_y + 160], radius=45, fill="#FFFFFF", outline=HEADER_COLOR, width=5)
    draw_rain_icon(draw, w/2 - 180, rain_card_y + 80, 80, HEADER_COLOR)
    draw.text((w/2 + 60, rain_card_y + 50), "ฝนสูงสุด", fill=HEADER_COLOR, font=f_label, anchor="mm")
    rain_color = "#D32F2F" if data['has_rain'] else HEADER_COLOR
    draw.text((w/2 + 60, rain_card_y + 110), data['rain_val'], fill=rain_color, font=f_rain_val, anchor="mm")

    # Main Stations Section
    col_w = w // 3
    card_y = 510
    for i, key in enumerate(['c7a', 'wat', 'bak']):
        st_info = STATIONS_CONFIG[key]
        st_lvl, st_diff = data[key]
        curr_x = (i * col_w) + (col_w / 2)
        draw.rounded_rectangle([i*col_w+25, card_y, (i+1)*col_w-25, 1200], radius=50, fill="#FFFFFF")
        draw_location_pin(draw, curr_x - 125, card_y + 65, 40, HEADER_COLOR)
        draw.text((curr_x + 20, card_y + 65), st_info['label'], fill=HEADER_COLOR, font=f_label, anchor="mm")
        
        # Gauge Drawing
        t_x1, t_y1, t_x2, t_y2 = curr_x-70, card_y+140, curr_x+70, 950
        draw.rounded_rectangle([t_x1-5, t_y1-5, t_x2+5, t_y2+5], radius=40, fill="#F5F5F5", outline="#BDBDBD", width=3) 
        fill_ratio = min(st_lvl / st_info['max'], 1.0)
        w_top = t_y2 - ((t_y2-t_y1) * fill_ratio)
        if st_lvl > 0:
            draw.rounded_rectangle([t_x1, max(w_top, t_y1), t_x2, t_y2], radius=35, fill=st_info['color'])
            
        # Bank Line: เปลี่ยนเป็น "ตลิ่ง +10.00"
        b_y = t_y2 - ((t_y2-t_y1) * (st_info['bank'] / st_info['max']))
        draw.line([t_x1-35, b_y, t_x2+35, b_y], fill="#FF1744", width=10)
        draw.text((curr_x, b_y - 30), f"ตลิ่ง +{st_info['bank']:.2f}", fill="#FF1744", font=f_diff, anchor="mm")

        draw.text((curr_x, 1020), f"+{st_lvl:.2f} ม.รทก.", fill="#0D47A1", font=f_val, anchor="mm")
        color_diff = "#D32F2F" if st_diff > 0 else ("#1976D2" if st_diff < 0 else "#424242")
        draw.text((curr_x, 1085), f"({st_diff:+.2f} ม.)", fill=color_diff, font=f_diff, anchor="mm")
        if key == 'c7a':
            draw.text((curr_x, 1145), f"{data.get('c7a_q', '-')} ลบ.ม./วิ", fill="#1B5E20", font=f_info, anchor="mm")

    # --- Bottom Action Cards ---
    bot_y = 1240
    card_h = 190
    
    # อ่างเก็บน้ำ
    draw.rounded_rectangle([50, bot_y, w/2 - 25, bot_y + card_h], radius=50, fill="#FFFFFF", outline="#BDBDBD", width=2)
    if data.get('has_reservoir', False):
        draw.text((w/4 - 100, bot_y + 95), "มี", fill="#D32F2F", font=f_alert, anchor="mm")
    else:
        draw_no_icon(draw, w/4 - 100, bot_y + 95, 70, "#D32F2F")
    draw.text((w/4 + 40, bot_y + 95), "อ่างเก็บน้ำ", fill=HEADER_COLOR, font=f_label, anchor="mm")

    # อุทกภัย
    draw.rounded_rectangle([w/2 + 25, bot_y, w - 50, bot_y + card_h], radius=50, fill="#FFFFFF", outline="#BDBDBD", width=2)
    if data.get('has_flood', False):
        draw.text((3*w/4 - 110, bot_y + 95), "มี", fill="#D32F2F", font=f_alert, anchor="mm")
    else:
        draw_no_icon(draw, 3*w/4 - 130, bot_y + 95, 70, "#D32F2F")
    draw.text((3*w/4 + 20, bot_y + 95), "อุทกภัย", fill=HEADER_COLOR, font=f_label, anchor="mm")

    # Footer
    draw.text((w/2 - 30, h-60), "Rid Angthong United ", fill=HEADER_COLOR, font=f_sub, anchor="mm")
    draw_report_book(draw, w/2 + 150, h-60, 50, HEADER_COLOR)

    return img

# --- Streamlit UI Layout ---
st.set_page_config(page_title="RID Ang Thong UNITED", layout="wide")

st.markdown(f"""
    <style>
    .main {{ background-color: {BG_COLOR_HEX}; }}
    .stButton>button {{ border-radius: 20px; background-color: {HEADER_COLOR}; color: white; border: none; height: 3.5em; font-weight: bold; font-size: 16px; }}
    .stTextArea>div>div>textarea {{ border-radius: 15px; border: 2px solid {HEADER_COLOR}; font-size: 16px; }}
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Rid Angthong United Dashboard")
st.markdown(f"**Digital Monitoring & Reporting** | {get_thai_date()}")

with st.sidebar:
    st.header("⚙️ ข้อมูลสถานี C.7A")
    c7a_lvl = st.number_input("ระดับน้ำ C.7A (+ม.รทก.)", value=1.46, format="%.2f")
    c7a_diff = st.number_input("เทียบเมื่อวาน (+/-)", value=0.02, format="%.2f")
    c7a_q = st.text_input("ปริมาณน้ำไหลผ่าน (ลบ.ม./วิ)", value="130")
    
    st.divider()
    st.header("📍 สถานะภาพรวม")
    # เมนูด้านซ้ายให้พี่โบ้เลือกเอง
    res_status = st.radio("สถานะอ่างเก็บน้ำ", ["ไม่มี", "มี"], index=0)
    flood_status = st.radio("สถานะอุทกภัย", ["ไม่มี", "มี"], index=0)
    
    st.divider()
    use_auto_c7a = st.checkbox("ใช้ข้อมูล C.7A จากฝั่งนี้", value=True)

col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("📝 ข้อมูลจาก LINE")
    manual_input = st.text_area("วางข้อความรายงานที่นี่:", height=520, placeholder="คัดลอกรายงานประจำวันมาวางที่นี่...")
    process_btn = st.button("🚀 ประมวลผลและสร้าง Dashboard", use_container_width=True)

with col2:
    if process_btn:
        auto_data = {'level': c7a_lvl, 'diff': c7a_diff, 'q': c7a_q} if use_auto_c7a else None
        with st.spinner('กำลังสร้างงานกราฟิกระดับพรีเมียม...'):
            # ดึงค่าจาก Sidebar ไปใส่ในรูป
            report_data = parse_report(manual_input, auto_data, (flood_status == "มี"), (res_status == "มี"))
            final_img = draw_dashboard(report_data)
            st.image(final_img, caption="RID Ang Thong UNITED v1.13", use_column_width=True)
            buf = io.BytesIO()
            final_img.save(buf, format="PNG")
            st.download_button("💾 ดาวน์โหลดภาพ PNG", data=buf.getvalue(), 
                               file_name=f"RID_United_v1.13_{report_data['date']}.png", mime="image/png", use_container_width=True)
    else:
        st.info("💡 พี่โบ้วางข้อความรายงานทางซ้ายมือ แล้วกดปุ่มประมวลผลได้เลยครับ")

st.divider()
st.caption("Developed by Rid Angthong United 🛡️")
