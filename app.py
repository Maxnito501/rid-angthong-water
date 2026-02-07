import streamlit as st
import re
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

# --- Configuration & Theme Settings ---
STATIONS_CONFIG = {
    'c7a': {'label': 'C.7A เจ้าพระยา', 'bank': 10.00, 'max': 12.0, 'color': '#0066cc', 'icon': '💧'},
    'wat': {'label': 'แม่น้ำน้อย (วัดตูม)', 'bank': 6.50, 'max': 8.0, 'color': '#28a745', 'icon': '💧'},
    'bak': {'label': 'แม่น้ำน้อย (บางจัก)', 'bank': 5.00, 'max': 6.5, 'color': '#ff8c00', 'icon': '💧'}
}

def get_thai_date():
    months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
    now = datetime.now()
    return f"{now.day} {months[now.month - 1]} {now.year + 543}"

def parse_report(manual_text, c7a_auto_data=None):
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

    return data

def draw_dashboard(data, font_path="THSarabunNew.ttf"):
    # Canvas Settings
    w, h = 1200, 1550
    bg_color = '#F0F2F5' # Modern Light Grey
    img = Image.new('RGB', (w, h), color=bg_color)
    draw = ImageDraw.Draw(img)

    try:
        f_title = ImageFont.truetype(font_path, 75)
        f_sub = ImageFont.truetype(font_path, 45)
        f_label = ImageFont.truetype(font_path, 48)
        f_val = ImageFont.truetype(font_path, 50)
        f_diff = ImageFont.truetype(font_path, 38)
        f_info = ImageFont.truetype(font_path, 40)
        f_rain_icon = ImageFont.truetype(font_path, 110)
        f_rain_val = ImageFont.truetype(font_path, 65)
        f_status_icon = ImageFont.truetype(font_path, 95)
    except:
        f_title = f_sub = f_label = f_val = f_diff = f_info = f_rain_icon = f_rain_val = f_status_icon = None

    # --- Modern Header (White card with accent) ---
    draw.rectangle([0, 0, w, 350], fill="#003366") # RID Dark Blue
    draw.text((w/2, 90), "RID ANG THONG UNITED", fill="#FFFFFF", font=f_sub, anchor="mm")
    draw.text((w/2, 175), "รายงานสถานการณ์น้ำรายวัน", fill="#FFFFFF", font=f_title, anchor="mm")
    draw.text((w/2, 260), f"ณ วันที่ {data['date']}", fill="#FFD700", font=f_sub, anchor="mm")
    
    # --- Hero Section: Rain (ข้อ 1) ---
    rain_card_y = 300
    draw.rounded_rectangle([w/2 - 250, rain_card_y, w/2 + 250, rain_card_y + 140], radius=40, fill="#FFFFFF", outline="#003366", width=3)
    icon_rain = "🌧️" if data['has_rain'] else "☀️"
    draw.text((w/2 - 120, rain_card_y + 70), icon_rain, fill="#003366", font=f_rain_icon, anchor="mm")
    draw.text((w/2 + 60, rain_card_y + 45), "ปริมาณฝนสะสม", fill="#555555", font=f_sub, anchor="mm")
    draw.text((w/2 + 60, rain_card_y + 100), data['rain_val'], fill="#003366", font=f_rain_val, anchor="mm")

    # --- Main Stations Section ---
    col_w = w // 3
    card_y = 480
    
    for i, key in enumerate(['c7a', 'wat', 'bak']):
        st_info = STATIONS_CONFIG[key]
        st_lvl, st_diff = data[key]
        curr_x = (i * col_w) + (col_w / 2)
        
        # Station Card
        draw.rounded_rectangle([i*col_w+25, card_y, (i+1)*col_w-25, 1180], radius=45, fill="#FFFFFF")
        
        # Station Label with Icon
        draw.text((curr_x, card_y + 60), f"📍 {st_info['label']}", fill="#003366", font=f_label, anchor="mm")

        # Gauge Design (Capsule Style)
        t_x1, t_y1, t_x2, t_y2 = curr_x-65, card_y+130, curr_x+65, 930
        draw.rounded_rectangle([t_x1-4, t_y1-4, t_x2+4, t_y2+4], radius=30, fill="#E9ECEF") # Tank Background
        
        fill_ratio = min(st_lvl / st_info['max'], 1.0)
        w_top = t_y2 - ((t_y2-t_y1) * fill_ratio)
        draw.rounded_rectangle([t_x1, max(w_top, t_y1), t_x2, t_y2], radius=30, fill=st_info['color'])

        # Modern Bank Line
        b_y = t_y2 - ((t_y2-t_y1) * (st_info['bank'] / st_info['max']))
        draw.line([t_x1-25, b_y, t_x2+25, b_y], fill="#FF4B4B", width=7)
        draw.text((curr_x, b_y - 25), f"ระดับตลิ่ง {st_info['bank']:.2f}", fill="#FF4B4B", font=f_diff, anchor="mm")

        # Data Texts
        draw.text((curr_x, 1000), f"+{st_lvl:.2f} ม.รทก.", fill="#333333", font=f_val, anchor="mm")
        
        color_diff = "#FF4B4B" if st_diff > 0 else ("#0066cc" if st_diff < 0 else "#888888")
        draw.text((curr_x, 1060), f"({st_diff:+.2f} ม.)", fill=color_diff, font=f_diff, anchor="mm")
        
        if key == 'c7a':
            draw.text((curr_x, 1120), f"🌊 {data.get('c7a_q', '-')} ลบ.ม./วิ", fill="#28A745", font=f_info, anchor="mm")

    # --- Bottom Action Cards (Status Logos) ---
    bot_y = 1220
    card_h = 240
    
    # Reservoir Card
    draw.rounded_rectangle([50, bot_y, w/2 - 25, bot_y + card_h], radius=45, fill="#FFFFFF")
    draw.text((w/4 + 10, bot_y + 80), "🚫", font=f_status_icon, anchor="mm")
    draw.text((w/4 + 10, bot_y + 170), "อ่างเก็บน้ำ", fill="#777777", font=f_label, anchor="mm")

    # Flood Card
    draw.rounded_rectangle([w/2 + 25, bot_y, w - 50, bot_y + card_h], radius=45, fill="#FFFFFF")
    draw.text((3*w/4 - 10, bot_y + 80), "✅", font=f_status_icon, anchor="mm")
    draw.text((3*w/4 - 10, bot_y + 170), "สถานการณ์อุทกภัย", fill="#28A745", font=f_label, anchor="mm")

    # Footer
    draw.text((w/2, h-60), "RID ANG THONG UNITED | โครงการชลประทานอ่างทอง", fill="#AAAAAA", font=f_sub, anchor="mm")
    return img

# --- Streamlit UI Layout ---
st.set_page_config(page_title="RID Ang Thong UNITED", layout="wide")

# Custom CSS to make Streamlit look more modern
st.markdown("""
    <style>
    .main { background-color: #F0F2F5; }
    .stButton>button { border-radius: 20px; background-color: #003366; color: white; border: none; height: 3em; font-weight: bold; }
    .stTextArea>div>div>textarea { border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ RID Ang Thong UNITED Dashboard")
st.markdown(f"**Modern Digital Transformation** | ประจำวันที่: {get_thai_date()}")

with st.sidebar:
    st.header("⚙️ ข้อมูลด่วน C.7A")
    c7a_lvl = st.number_input("ระดับน้ำ C.7A (+ม.รทก.)", value=1.46, format="%.2f")
    c7a_diff = st.number_input("เทียบเมื่อวาน (+/-)", value=0.02, format="%.2f")
    c7a_q = st.text_input("ปริมาณน้ำไหลผ่าน (ลบ.ม./วิ)", value="130")
    use_auto_c7a = st.checkbox("ใช้ข้อมูล C.7A จากฝั่งนี้", value=True)
    st.divider()
    st.info("💡 เวอร์ชัน v1.7: Modern UI & Iconography System")

col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("📝 คัดลอกข้อมูลจาก LINE")
    manual_input = st.text_area("วางข้อความรายงานที่นี่:", height=520, placeholder="คัดลอกรายงานประจำวันมาวางที่นี่...")
    process_btn = st.button("🚀 สร้างอินโฟกราฟิกแบบ Modern", use_container_width=True)

with col2:
    if process_btn:
        auto_data = {'level': c7a_lvl, 'diff': c7a_diff, 'q': c7a_q} if use_auto_c7a else None
        with st.spinner('กำลังสร้างงานกราฟิกระดับพรีเมียม...'):
            report_data = parse_report(manual_input, auto_data)
            final_img = draw_dashboard(report_data)
            st.image(final_img, caption="RID Ang Thong UNITED - Modern Interface", use_column_width=True)
            
            buf = io.BytesIO()
            final_img.save(buf, format="PNG")
            st.download_button("💾 ดาวน์โหลดภาพ PNG (High-Res)", data=buf.getvalue(), 
                               file_name=f"RID_United_Modern_{report_data['date']}.png", mime="image/png", use_container_width=True)
    else:
        st.info("💡 พี่โบ้วางข้อความรายงานทางซ้ายมือ แล้วกดปุ่มประมวลผลเพื่อดู Dashboard ครับ")

st.divider()
st.caption("Developed by RID Angthong United AI Partner 🛡️")
