import os, json, random, base64, time, sqlite3
from datetime import datetime
from dotenv import load_dotenv
from sarvamai import SarvamAI
import streamlit as st
import httpx
import requests

st.set_page_config(page_title="Civic Helpdesk Bot", page_icon="🏙️", layout="centered")

# ---------------- Background & theme ----------------
def get_base64_image(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

bg_image = get_base64_image("background.png")

if bg_image:
    background_css = f"""
        background-image:
            linear-gradient(rgba(14, 17, 23, 0.55), rgba(14, 17, 23, 0.72)),
            url('data:image/png;base64,{bg_image}');
        background-size: cover;
        background-position: center top;
        background-attachment: fixed;
    """
else:
    background_css = "background-color: #0E1117;"

st.markdown(f"""
<style>
    .stApp {{ {background_css} }}
    .block-container {{
        margin-left: 22% !important;
        margin-right: 5% !important;
        max-width: 720px !important;
    }}
    .hero {{
        background: linear-gradient(135deg, rgba(15,31,61,0.94) 0%, rgba(28,35,51,0.94) 100%);
        padding: 40px 32px; border-radius: 16px; margin-bottom: 28px;
        border: 1px solid #2A3550; box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        backdrop-filter: blur(8px);
    }}
    .hero h1 {{ margin: 0; font-size: 32px; color: #FFFFFF; }}
    .hero p {{ color: #C5CDDB; margin-top: 8px; font-size: 15px; }}
    .emergency-card {{
        background: linear-gradient(135deg, rgba(139,26,26,0.55) 0%, rgba(28,35,51,0.94) 100%);
        border: 1px solid #7A2E2E; border-radius: 14px; padding: 20px; margin-bottom: 16px;
        backdrop-filter: blur(8px);
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: rgba(28, 35, 51, 0.94); border-radius: 14px; backdrop-filter: blur(8px);
    }}
    .stTextInput input {{
        border-radius: 10px; padding: 12px; border: 1px solid #2A3550;
        background-color: #1C2333; color: #FFFFFF;
    }}
    .stTextInput input:focus {{ border-color: #00D1B2; box-shadow: 0 0 0 1px #00D1B2; }}
    div[data-testid="stButton"] button {{
        border-radius: 10px; padding: 10px 28px; font-weight: 600;
        background-color: #00D1B2; color: #0E1117; border: none; transition: all 0.2s ease;
        width: 100%;
    }}
    div[data-testid="stButton"] button:hover {{ background-color: #00E5C7; transform: translateY(-1px); }}
    .emergency-btn button {{
        background-color: #7A2E2E !important; color: #FFFFFF !important;
        border: 1px solid #FF6B6B !important;
    }}
    .emergency-btn button:hover {{ background-color: #9C3838 !important; }}
    div[data-testid="stMarkdownContainer"] p {{ font-size: 16px; line-height: 1.6; }}
    label[data-testid="stWidgetLabel"] p {{ color: #E5E9F0 !important; font-weight: 500; }}
    div[data-testid="stExpander"] {{
        background-color: rgba(28,35,51,0.85); border-radius: 10px; border: 1px solid #2A3550;
        margin-bottom: 8px;
    }}

    @media (max-width: 768px) {{
        .block-container {{
            margin-left: 4% !important;
            margin-right: 4% !important;
            max-width: 100% !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }}
        .hero {{ padding: 24px 18px; }}
        .hero h1 {{ font-size: 22px !important; }}
        .hero p {{ font-size: 13px !important; }}
        .emergency-card p:first-child {{ font-size: 16px !important; }}
    }}
</style>

<div class="hero">
    <h1>🏙️ Civic Helpdesk Bot</h1>
    <p>Report civic issues in any language — powered by Sarvam AI</p>
</div>
""", unsafe_allow_html=True)

load_dotenv()
client = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))

LANGUAGES = {
    "Hindi": "hi-IN", "Bengali": "bn-IN", "Gujarati": "gu-IN", "Kannada": "kn-IN",
    "Malayalam": "ml-IN", "Marathi": "mr-IN", "Odia": "od-IN", "Punjabi": "pa-IN",
    "Tamil": "ta-IN", "Telugu": "te-IN", "English": "en-IN",
}

# ---------------- Persistent storage (with migration for existing DBs) ----------------
DB_PATH = "complaints.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id TEXT, category TEXT, description TEXT,
        timestamp TEXT, feedback TEXT
    )""")
    # Migrate: add new columns if this DB predates them
    for col_def in [
        "original_query TEXT",
        "ai_response TEXT",
        "translated_response TEXT",
        "language TEXT",
    ]:
        try:
            conn.execute(f"ALTER TABLE complaints ADD COLUMN {col_def}")
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()
    conn.close()

init_db()

def log_complaint(category, description, original_query):
    ticket_id = f"TICKET-{random.randint(1000,9999)}"
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO complaints
           (ticket_id, category, description, timestamp, feedback, original_query)
           VALUES (?,?,?,?,?,?)""",
        (ticket_id, category, description, datetime.now().strftime("%Y-%m-%d %H:%M"), None, original_query),
    )
    conn.commit()
    conn.close()
    return {"ticket_id": ticket_id, "category": category}

def update_complaint_response(ticket_id, ai_response, translated_response, language):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE complaints SET ai_response=?, translated_response=?, language=? WHERE ticket_id=?",
        (ai_response, translated_response, language, ticket_id),
    )
    conn.commit()
    conn.close()

def get_recent_complaints(limit=5):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT ticket_id, category, description, timestamp FROM complaints ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return rows

def get_all_complaints(search_term=""):
    conn = sqlite3.connect(DB_PATH)
    if search_term:
        like = f"%{search_term}%"
        rows = conn.execute(
            """SELECT ticket_id, category, description, timestamp, feedback,
                      original_query, ai_response, translated_response, language
               FROM complaints
               WHERE ticket_id LIKE ? OR category LIKE ? OR description LIKE ?
               ORDER BY id DESC""",
            (like, like, like),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT ticket_id, category, description, timestamp, feedback,
                      original_query, ai_response, translated_response, language
               FROM complaints ORDER BY id DESC"""
        ).fetchall()
    conn.close()
    return rows

def save_feedback(ticket_id, feedback):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE complaints SET feedback=? WHERE ticket_id=?", (feedback, ticket_id))
    conn.commit()
    conn.close()

# ---------------- Retry + caching ----------------
def call_with_retry(fn, *args, max_retries=3, base_delay=1.0, **kwargs):
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except (httpx.ConnectTimeout, httpx.ReadTimeout):
            if attempt == max_retries - 1:
                raise
            time.sleep(base_delay * (2 ** attempt))

@st.cache_data(show_spinner=False)
def translate_cached(text, target_lang_code):
    translated = call_with_retry(
        client.text.translate, input=text, source_language_code="en-IN",
        target_language_code=target_lang_code, speaker_gender="Male",
    )
    return translated.translated_text

# ---------------- IP-based location ----------------
@st.cache_data(show_spinner=False, ttl=3600)
def get_location_by_ip(ip_address):
    try:
        url = f"http://ip-api.com/json/{ip_address}" if ip_address else "http://ip-api.com/json/"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "success":
            return {
                "city": data.get("city", ""),
                "region": data.get("regionName", ""),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
            }
    except Exception:
        pass
    return None

def maps_link(lat, lon, query):
    return f"https://www.google.com/maps/search/{query}/@{lat},{lon},15z"

def maps_link_by_name(place_query):
    return f"https://www.google.com/maps/search/{place_query.replace(' ', '+')}"

tools = [{
    "type": "function",
    "function": {
        "name": "log_complaint",
        "description": "Log a civic complaint and generate a ticket",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["roads", "water", "electricity", "sanitation", "other"]},
                "description": {"type": "string"},
            },
            "required": ["category", "description"],
        },
    },
}]

def handle_complaint(user_text, target_lang_code, lang_name):
    messages = [
        {"role": "system", "content": "You are a civic helpdesk assistant. Always classify and log every complaint using the log_complaint tool before replying."},
        {"role": "user", "content": user_text},
    ]

    try:
        response = call_with_retry(
            client.chat.completions, model="sarvam-105b", messages=messages, tools=tools, tool_choice="auto"
        )
    except (httpx.ConnectTimeout, httpx.ReadTimeout):
        return None, "⚠️ Couldn't reach Sarvam's servers after retrying. Check your connection.", None

    message = response.choices[0].message

    if message.tool_calls:
        tool_call = message.tool_calls[0]
        args = json.loads(tool_call.function.arguments)
        result = log_complaint(args["category"], args["description"], user_text)

        messages.append({
            "role": "assistant",
            "tool_calls": [{
                "id": tool_call.id, "type": "function",
                "function": {"name": tool_call.function.name, "arguments": tool_call.function.arguments},
            }],
        })
        messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})

        final = call_with_retry(client.chat.completions, model="sarvam-105b", messages=messages, tools=tools)
        final_text = final.choices[0].message.content

        translated_text = None
        if target_lang_code != "en-IN":
            translated_text = translate_cached(final_text, target_lang_code)

        update_complaint_response(result["ticket_id"], final_text, translated_text, lang_name)
        return result, final_text, translated_text
    else:
        return None, message.content, None

# ---------------- Emergency Help section ----------------
st.markdown("""
<div class="emergency-card">
    <p style="color:#FF6B6B; font-weight:700; font-size:18px; margin-bottom:4px;">🚨 Need Immediate Emergency Help?</p>
    <p style="color:#C5CDDB; font-size:14px; margin-bottom:0;">
        Get your area and India's official emergency numbers instantly.
        This does not contact emergency services directly — for real emergencies, call <strong>112</strong> now.
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="emergency-btn">', unsafe_allow_html=True)
emergency_clicked = st.button("📍 Check My Local Emergency Info", key="emergency_check")
st.markdown('</div>', unsafe_allow_html=True)

if emergency_clicked:
    st.session_state["show_emergency"] = True

if st.session_state.get("show_emergency"):
    with st.spinner("Locating your area..."):
        client_ip = st.context.ip_address
        location_data = get_location_by_ip(client_ip)

    if location_data and location_data.get("city"):
        st.success(f"📍 Estimated location: {location_data['city']}, {location_data['region']}")
        lat, lon = location_data["lat"], location_data["lon"]
        hospital_link = maps_link(lat, lon, "hospital") if lat else maps_link_by_name(f"hospital near {location_data['city']}")
        police_link = maps_link(lat, lon, "police+station") if lat else maps_link_by_name(f"police station near {location_data['city']}")
    else:
        st.info("Couldn't auto-detect your area. Enter your city for accurate map links.")
        manual_city = st.text_input("Your city:", key="manual_city_input")
        hospital_link = maps_link_by_name(f"hospital near {manual_city}") if manual_city else None
        police_link = maps_link_by_name(f"police station near {manual_city}") if manual_city else None

    st.markdown("""
    <div style="background-color:rgba(28,35,51,0.95); padding:18px; border-radius:12px; border:1px solid #2A3550; margin-top:8px;">
        <p style="color:#00D1B2; font-weight:600; margin-bottom:8px;">National Emergency Numbers (India)</p>
        <p>🚨 <strong>112</strong> — All-in-one emergency (police, fire, ambulance)</p>
        <p>👮 <strong>100</strong> — Police</p>
        <p>🚒 <strong>101</strong> — Fire</p>
        <p>🚑 <strong>102 / 108</strong> — Ambulance</p>
        <p>👩 <strong>1091</strong> — Women's helpline</p>
    </div>
    """, unsafe_allow_html=True)

    if hospital_link and police_link:
        col1, col2 = st.columns(2)
        with col1:
            st.link_button("🏥 Nearest hospital", hospital_link)
        with col2:
            st.link_button("👮 Nearest police station", police_link)

st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)

# ---------------- Browse all tickets — click to view full detail ----------------
browse_toggle = st.button("📂 Browse All Logged Tickets", key="browse_toggle")
if browse_toggle:
    st.session_state["show_browse"] = not st.session_state.get("show_browse", False)

if st.session_state.get("show_browse"):
    search_term = st.text_input("Search by ticket ID, category, or keyword:", key="ticket_search")
    all_tickets = get_all_complaints(search_term)

    if all_tickets:
        st.caption(f"{len(all_tickets)} ticket(s) found — click any to view full details")
        for tid, cat, desc, ts, feedback, orig_query, ai_resp, trans_resp, lang in all_tickets:
            fb_icon = "👍" if feedback == "up" else "👎" if feedback == "down" else "—"
            with st.expander(f"{tid} · {cat} · {ts}"):
                st.markdown(f"**Category:** {cat}")
                st.markdown(f"**Feedback:** {fb_icon}")
                st.markdown("---")
                st.markdown("**Original query:**")
                st.markdown(orig_query if orig_query else "*Not recorded (logged before this feature was added)*")
                st.markdown("**AI response:**")
                st.markdown(ai_resp if ai_resp else "*Not recorded*")
                if trans_resp:
                    st.markdown(f"**Translated response ({lang}):**")
                    st.markdown(trans_resp)
    else:
        st.caption("No tickets found.")

# ---------------- Recent tickets sidebar ----------------
with st.sidebar:
    st.markdown("### 📋 Recent Tickets")
    recent = get_recent_complaints()
    if recent:
        for tid, cat, desc, ts in recent:
            short_desc = desc[:50] + ("..." if len(desc) > 50 else "")
            st.markdown(
                f"**{tid}** · {cat}  \n"
                f"<span style='color:#9CA3AF;font-size:12px'>{short_desc} · {ts}</span>",
                unsafe_allow_html=True,
            )
            st.divider()
    else:
        st.caption("No tickets yet.")

# ---------------- Main complaint form ----------------
with st.container(border=True):
    user_text = st.text_input("Describe your complaint:")
    selected_lang = st.selectbox("Reply language:", list(LANGUAGES.keys()), index=0)
    submitted = st.button("Submit", type="primary")

if submitted and user_text:
    with st.spinner("Processing..."):
        ticket, reply, translated_reply = handle_complaint(user_text, LANGUAGES[selected_lang], selected_lang)
    st.session_state["last_result"] = (ticket, reply, translated_reply, selected_lang)

if "last_result" in st.session_state:
    ticket, reply, translated_reply, lang_used = st.session_state["last_result"]

    if ticket:
        st.success(f"Ticket logged: {ticket['ticket_id']} ({ticket['category']})")

    st.markdown(f"""
    <div style="background-color:rgba(28,35,51,0.95); padding:20px; border-radius:12px; margin-top:10px; border: 1px solid #2A3550; backdrop-filter: blur(8px);">
        <p style="color:#00D1B2; font-weight:600; margin-bottom:6px;">Reply</p>
        <p>{reply}</p>
    </div>
    """, unsafe_allow_html=True)

    if translated_reply:
        st.markdown(f"""
        <div style="background-color:rgba(28,35,51,0.95); padding:20px; border-radius:12px; margin-top:10px; border: 1px solid #2A3550; backdrop-filter: blur(8px);">
            <p style="color:#00D1B2; font-weight:600; margin-bottom:6px;">Translated ({lang_used})</p>
            <p>{translated_reply}</p>
        </div>
        """, unsafe_allow_html=True)

    if ticket:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👍 Helpful", key=f"up_{ticket['ticket_id']}"):
                save_feedback(ticket["ticket_id"], "up")
                st.toast("Thanks for the feedback!")
        with col2:
            if st.button("👎 Not helpful", key=f"down_{ticket['ticket_id']}"):
                save_feedback(ticket["ticket_id"], "down")
                st.toast("Thanks, we'll improve.")