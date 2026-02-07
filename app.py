import streamlit as st
import re
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

# --- Configuration & Theme Settings ---
STATIONS_CONFIG = {
    'c7a': {'label': 'ม.เจ้าพระยา (C.7A)', 'bank': 10.00, 'max': 12.0, 'color': '#007BFF'},
    'wat': {'label': 'ม.น้อย (วัดตูม)', 'bank': 6.50, 'max': 8.0, 'color': '#007BFF'},
    'bak': {'label': 'ม.น้อย (บางจัก)', 'bank': 5.00, 'max': 6.5, 'color': '#007BFF'}
}

BG_COLOR_HEX = '#B3E5FC' 
HEADER_COLOR = "#01579B" 
WATER_COLOR = "#007BFF" 

def get_thai_date():
    months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
    now = datetime.now()
    return f"{now.day} {months[now.month - 1]} {now.year + 543}"

def parse_report(manual_text, c7a_auto_data=None, manual_flood=False, manual_reservoir=False):
    data = {'date': get_thai_date()}
    
    if "ไม่มีฝน" in manual_text:
        data['rain_val'], data['has_rain'] = "-", False
    else:
        rain_match = re.search(r"(\d+\.?\d*)\s*ม\.ม\.", manual_text)
        data['rain_val'] = f"{rain_match.group(1)} มม." if rain_match else "-"
        data['has_rain'] = True if rain_match else False

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
    draw.rectangle([x-size//2, y-size//3, x+size//2, y+size//3], outline=color, width=3)
    draw.line([x, y-size//3, x, y+size//3], fill=color, width=3)
    draw.line([x+8, y-10, x+size//2-5, y-10], fill=color, width=2)
    draw.line([x+8, y+8, x+size//2-5, y+8], fill=color, width=2)

def draw_indicator(draw, x, y, size, color, direction="left"):
    if direction == "left":
        points = [(x, y), (x - size, y - size//1.5), (x - size, y + size//1.5)]
    else:
        points = [(x, y), (x + size, y - size//1.5), (x + size, y + size//1.5)]
    draw.polygon(points, fill=color)

def draw_staff_gauge_overflow(draw, x1, y1_max, x2, y2, max_val, bank_val, water_val, f_scale):
    """ฟังก์ชันวาดสตาฟเกจแบบน้ำล้นไม้ได้ (v1.16)"""
    total_draw_h = y2 - y1_max
    
    # คำนวณตำแหน่ง Y ของตลิ่ง (นี่คือหัวของไม้บรรทัดสตาฟเกจ)
    y_at_bank = y2 - (total_draw_h * (bank_val / max_val))
    
    # 1. วาดไม้บรรทัดสตาฟเกจ (วาดถึงแค่ระดับตลิ่งพอ)
    draw.rectangle([x1, y_at_bank, x2, y2], fill="#FFFFFF", outline="#000000", width=2)
    
    # 2. วาดขีดสเกลบนไม้บรรทัด (วาดถึงแค่ bank_val)
    num_ticks = int(bank_val * 10)
    for i in range(num_ticks + 1):
        tick_val = i / 10.0
        tick_y = y2 - (tick_val / max_val * total_draw_h)
        if i % 10 == 0:
            draw.line([x1, tick_y, x1 + 20, tick_y], fill="#000000", width=2)
            if tick_val > 0:
                draw.text((x1 + 25, tick_y), str(int(tick_val)), fill="#000000", font=f_scale, anchor="lm")
        elif i % 2 == 0:
            draw.line([x1, tick_y, x1 + 10, tick_y], fill="#000000", width=1)

    # 3. วาดระดับน้ำ (ถ้าน้ำสูงกว่า bank_val จะล้นไม้บรรทัดขึ้นมา)
    w_top = y2 - (total_draw_h * (water_val / max_val))
    if water_val > 0:
        # ระดับน้ำสีน้ำเงิน
        draw.rectangle([x1+2, max(w_top, y1_max), x2-2, y2-2], fill=WATER_COLOR)
        # ลูกศรชี้ระดับน้ำ (ชี้หน้าหลอด)
        draw_indicator(draw, x1 - 5, w_top, 20, WATER_COLOR, "left")

    # 4. วาดตลิ่งและลูกศรตลิ่ง (สีแดง)
    draw.line([x1, y_at_bank, x2, y_at_bank], fill="#FF1744", width=5)
    draw_indicator(draw, x1 - 5, y_at_bank, 20, "#FF1744", "left")
    
    return y_at_bank

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
        f_scale = ImageFont.truetype(font_path, 26)
    except:
        f_title = f_sub = f_label = f_val = f_diff = f_info = f_rain_val = f_alert = f_scale = None

    # Header
    draw.rectangle([0, 0, w, 360], fill=HEADER_COLOR)
    draw.text((w/2, 85), "โครงการชลประทานอ่างทอง สำนักงานชลประทานที่ 12", fill="#FFFFFF", font=f_sub, anchor="mm")
    draw.text((w/2, 175), "รายงานสถานการณ์น้ำรายวัน", fill="#FFFFFF", font=f_title, anchor="mm")
    draw.text((w/2, 265), f"ณ วันที่ {data['date']}", fill="#FFEA00", font=f_sub, anchor="mm")
    
    # Rain Section
    rain_card_y = 315
    draw.rounded_rectangle([w/2 - 280, rain_card_y, w/2 + 280, rain_card_y + 160], radius=45, fill="#FFFFFF", outline=HEADER_COLOR, width=5)
    draw_rain_icon(draw, w/2 - 190, rain_card_y + 80, 80, HEADER_COLOR)
    draw.text((w/2 + 60, rain_card_y + 50), "ฝนสูงสุด", fill=HEADER_COLOR, font=f_label, anchor="mm")
    rain_val_color = "#D32F2F" if data['has_rain'] else HEADER_COLOR
    draw.text((w/2 + 60, rain_card_y + 110), data['rain_val'], fill=rain_val_color, font=f_rain_val, anchor="mm")

    # Main Stations Section
    col_w = w // 3
    card_y = 510
    for i, key in enumerate(['c7a', 'wat', 'bak']):
        st_info = STATIONS_CONFIG[key]
        st_lvl, st_diff = data[key]
        curr_x = (i * col_w) + (col_w / 2)
        
        draw.rounded_rectangle([i*col_w+25, card_y, (i+1)*col_w-25, 1200], radius=50, fill="#FFFFFF")
        draw_location_pin(draw, curr_x - 130, card_y + 65, 40, HEADER_COLOR)
        draw.text((curr_x + 15, card_y + 65), st_info['label'], fill=HEADER_COLOR, font=f_label, anchor="mm")
        
        # วาด Staff Gauge (ความสูงหลอดจำกัดที่ตลิ่ง แต่น้ำล้นได้)
        # กำหนดเพดานวาดรูปน้ำไว้ที่ y_max (card_y+140) แต่ตัวไม้จบที่ y_at_bank
        t_x1, t_y1_max, t_x2, t_y2 = curr_x-40, card_y+140, curr_x+40, 950
        y_bank_pos = draw_staff_gauge_overflow(draw, t_x1, t_y1_max, t_x2, t_y2, st_info['max'], st_info['bank'], st_lvl, f_scale)
            
        # ตัวหนังสือ "ตลิ่ง" ด้านขวา
        draw.text((t_x2 + 10, y_bank_pos), f"ตลิ่ง +{st_info['bank']:.2f}", fill="#FF1744", font=f_diff, anchor="lm")

        # ข้อมูลระดับน้ำ
        draw.text((curr_x, 1020), f"+{st_lvl:.2f} ม.รทก.", fill="#0D47A1", font=f_val, anchor="mm")
        color_diff = "#D32F2F" if st_diff > 0 else ("#1976D2" if st_diff < 0 else "#424242")
        draw.text((curr_x, 1085), f"({st_diff:+.2f} ม.)", fill=color_diff, font=f_diff, anchor="mm")
        if key == 'c7a':
            draw.text((curr_x, 1145), f"{data.get('c7a_q', '-')} ลบ.ม./วิ", fill="#1B5E20", font=f_info, anchor="mm")

    # Bottom Cards
    bot_y = 1240
    card_h = 190
    draw.rounded_rectangle([50, bot_y, w/2 - 25, bot_y + card_h], radius=50, fill="#FFFFFF", outline="#BDBDBD", width=2)
    if data.get('has_reservoir', False):
        draw.text((w/4 - 100, bot_y + 95), "มี", fill="#D32F2F", font=f_alert, anchor="mm")
    else:
        draw_no_icon(draw, w/4 - 100, bot_y + 95, 70, "#D32F2F")
    draw.text((w/4 + 45, bot_y + 95), "อ่างเก็บน้ำ", fill=HEADER_COLOR, font=f_label, anchor="mm")

    draw.rounded_rectangle([w/2 + 25, bot_y, w - 50, bot_y + card_h], radius=50, fill="#FFFFFF", outline="#BDBDBD", width=2)
    if data.get('has_flood', False):
        draw.text((3*w/4 - 110, bot_y + 95), "มี", fill="#D32F2F", font=f_alert, anchor="mm")
    else:
        draw_no_icon(draw, 3*w/4 - 130, bot_y + 95, 70, "#D32F2F")
    draw.text((3*w/4 + 25, bot_y + 95), "อุทกภัย", fill=HEADER_COLOR, font=f_label, anchor="mm")

    # Footer
    draw.text((w/2 - 40, h-60), "Rid Angthong United ", fill=HEADER_COLOR, font=f_sub, anchor="mm")
    draw_report_book(draw, w/2 + 150, h-60, 50, HEADER_COLOR)
    return img

# --- Streamlit UI Layout ---
st.set_page_config(page_title="RID Ang Thong UNITED", layout="wide")
st.markdown(f"<style>.main {{ background-color: {BG_COLOR_HEX}; }} .stButton>button {{ border-radius: 20px; background-color: {HEADER_COLOR}; color: white; border: none; height: 3.5em; font-weight: bold; font-size: 16px; }} .stTextArea>div>div>textarea {{ border-radius: 15px; border: 2px solid {HEADER_COLOR}; font-size: 16px; }} </style>", unsafe_allow_html=True)

st.title("🛡️ Rid Angthong United Dashboard")
st.markdown(f"**Digital Monitoring & Reporting** | {get_thai_date()}")

with st.sidebar:
    st.header("⚙️ ข้อมูลสถานี C.7A")
    c7a_lvl = st.number_input("ระดับน้ำ C.7A (+ม.รทก.)", value=1.46, format="%.2f")
    c7a_diff = st.number_input("เทียบเมื่อวาน (+/-)", value=0.02, format="%.2f")
    c7a_q = st.text_input("ปริมาณน้ำไหลผ่าน (ลบ.ม./วิ)", value="130")
    st.divider()
    st.header("📍 สถานะภาพรวม")
    res_status = st.radio("สถานะอ่างเก็บน้ำ", ["ไม่มี", "มี"], index=0)
    flood_status = st.radio("สถานะอุทกภัย", ["ไม่มี", "มี"], index=0)
    st.divider()
    use_auto_c7a = st.checkbox("ใช้ข้อมูล C.7A จากฝั่งนี้", value=True)

col1, col2 = st.columns([1, 1.5])
with col1:
    st.subheader("📝 ข้อมูลจาก LINE")
    manual_input = st.text_area("วางข้อความรายงานที่นี่:", height=520, placeholder="คัดลอกรายงานประจำวันมาวางที่นี่...")
    process_btn = st.button("🚀 สร้าง Dashboard ล้นตลิ่ง v1.16", use_container_width=True)

with col2:
    if process_btn:
        auto_data = {'level': c7a_lvl, 'diff': c7a_diff, 'q': c7a_q} if use_auto_c7a else None
        with st.spinner('กำลังคำนวณระดับน้ำล้นตลิ่ง...'):
            report_data = parse_report(manual_input, auto_data, (flood_status == "มี"), (res_status == "มี"))
            final_img = draw_dashboard(report_data)
            st.image(final_img, caption="RID Ang Thong UNITED v1.16 - Overflow Gauge", use_column_width=True)
            buf = io.BytesIO()
            final_img.save(buf, format="PNG")
            st.download_button("💾 ดาวน์โหลดภาพ PNG", data=buf.getvalue(), file_name=f"RID_United_Overflow_v1.16_{report_data['date']}.png", mime="image/png", use_container_width=True)
    else:
        st.info("💡 พี่โบ้วางข้อความรายงานทางซ้ายมือ แล้วกดปุ่มประมวลผลครับ")

st.divider()
st.caption("Developed by Rid Angthong United 🛡️")
