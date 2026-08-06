import os, json, random, base64, time, sqlite3
from datetime import datetime
from dotenv import load_dotenv
from sarvamai import SarvamAI
import streamlit as st
import httpx
import requests
from streamlit_geolocation import streamlit_geolocation

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
        border: 1px solid #7A2E2E; border-radius: 14px; padding: 20px; margin-bottom: 24px;
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
    }}
    div[data-testid="stButton"] button:hover {{ background-color: #00E5C7; transform: translateY(-1px); }}
    div[data-testid="stMarkdownContainer"] p {{ font-size: 16px; line-height: 1.6; }}
    label[data-testid="stWidgetLabel"] p {{ color: #E5E9F0 !important; font-weight: 500; }}
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

# ---------------- Persistent storage ----------------
DB_PATH = "complaints.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id TEXT, category TEXT, description TEXT,
        timestamp TEXT, feedback TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

def log_complaint(category, description):
    ticket_id = f"TICKET-{random.randint(1000,9999)}"
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO complaints (ticket_id, category, description, timestamp, feedback) VALUES (?,?,?,?,?)",
        (ticket_id, category, description, datetime.now().strftime("%Y-%m-%d %H:%M"), None),
    )
    conn.commit()
    conn.close()
    return {"ticket_id": ticket_id, "category": category}

def get_recent_complaints(limit=5):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT ticket_id, category, description, timestamp FROM complaints ORDER BY id DESC LIMIT ?", (limit,)
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

# ---------------- Emergency location lookup ----------------
@st.cache_data(show_spinner=False)
def reverse_geocode(lat, lon):
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "CivicHelpdeskBot/1.0 (student hackathon practice project)"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        addr = data.get("address", {})
        area = addr.get("suburb") or addr.get("neighbourhood") or addr.get("village") or ""
        city = addr.get("city") or addr.get("town") or addr.get("county") or ""
        state = addr.get("state", "")
        parts = [p for p in [area, city, state] if p]
        return ", ".join(parts) if parts else data.get("display_name", "Location detected")
    except Exception:
        return None

def maps_link(lat, lon, query):
    return f"https://www.google.com/maps/search/{query}/@{lat},{lon},15z"

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

def handle_complaint(user_text, target_lang_code):
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
        result = log_complaint(args["category"], args["description"])

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

        if target_lang_code == "en-IN":
            return result, final_text, None

        translated_text = translate_cached(final_text, target_lang_code)
        return result, final_text, translated_text
    else:
        return None, message.content, None

# ---------------- Emergency Help section ----------------
st.markdown("""
<div class="emergency-card">
    <p style="color:#FF6B6B; font-weight:700; font-size:18px; margin-bottom:4px;">🚨 Need Immediate Emergency Help?</p>
    <p style="color:#C5CDDB; font-size:14px; margin-bottom:12px;">
        This shares your live location to show nearby help and India's official emergency numbers.
        It does not contact emergency services directly — for real emergencies, call <strong>112</strong> now.
    </p>
</div>
""", unsafe_allow_html=True)

with st.expander("📍 Share my location for local emergency info", expanded=False):
    st.caption("Your browser will ask for location permission — this stays in your session and is never stored.")
    location = streamlit_geolocation()

    if location and location.get("latitude"):
        lat, lon = location["latitude"], location["longitude"]
        place_name = reverse_geocode(lat, lon)

        if place_name:
            st.success(f"📍 Detected location: {place_name}")
        else:
            st.warning("Got your coordinates, but couldn't resolve an address (network issue). Showing general info.")

        st.markdown(f"""
        <div style="background-color:rgba(28,35,51,0.95); padding:18px; border-radius:12px; border:1px solid #2A3550; margin-top:8px;">
            <p style="color:#00D1B2; font-weight:600; margin-bottom:8px;">National Emergency Numbers (India)</p>
            <p>🚨 <strong>112</strong> — All-in-one emergency (police, fire, ambulance)</p>
            <p>👮 <strong>100</strong> — Police</p>
            <p>🚒 <strong>101</strong> — Fire</p>
            <p>🚑 <strong>102 / 108</strong> — Ambulance</p>
            <p>👩 <strong>1091</strong> — Women's helpline</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.link_button("🏥 Nearest hospital", maps_link(lat, lon, "hospital"))
        with col2:
            st.link_button("👮 Nearest police station", maps_link(lat, lon, "police+station"))
    else:
        st.info("Click the location icon above to share your position and see local emergency info.")

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
        ticket, reply, translated_reply = handle_complaint(user_text, LANGUAGES[selected_lang])
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