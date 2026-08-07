import os, json, random, base64, time, sqlite3
from datetime import datetime
from dotenv import load_dotenv
from sarvamai import SarvamAI
import streamlit as st
import httpx
import requests
import feedparser
from urllib.parse import quote

st.set_page_config(page_title="Civic Helpdesk Bot", page_icon="🏙️", layout="centered")

# ---------------- Theme system ----------------
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

THEMES = {
    "dark": {
        "overlay_1": "rgba(14, 17, 23, 0.55)", "overlay_2": "rgba(14, 17, 23, 0.72)",
        "fallback_bg": "#0E1117",
        "hero_grad_1": "rgba(15,31,61,0.94)", "hero_grad_2": "rgba(28,35,51,0.94)",
        "card_bg": "rgba(28,35,51,0.94)", "card_bg_solid": "rgba(28,35,51,0.95)",
        "card_bg_light": "rgba(28,35,51,0.85)",
        "text_primary": "#FFFFFF", "text_secondary": "#C5CDDB", "text_body": "#E5E9F0",
        "border": "#2A3550", "input_bg": "#1C2333", "input_text": "#FFFFFF",
        "muted": "#9CA3AF",
    },
    "light": {
        "overlay_1": "rgba(255, 255, 255, 0.72)", "overlay_2": "rgba(255, 255, 255, 0.85)",
        "fallback_bg": "#F4F6FB",
        "hero_grad_1": "rgba(255,255,255,0.95)", "hero_grad_2": "rgba(232,238,248,0.95)",
        "card_bg": "rgba(255,255,255,0.92)", "card_bg_solid": "rgba(255,255,255,0.96)",
        "card_bg_light": "rgba(255,255,255,0.85)",
        "text_primary": "#0F1F3D", "text_secondary": "#4B5563", "text_body": "#1F2937",
        "border": "#D8DEEA", "input_bg": "#F3F5F9", "input_text": "#0F1F3D",
        "muted": "#6B7280",
    },
}

T = THEMES[st.session_state["theme"]]
ACCENT = "#00D1B2"

# ---------------- Background image ----------------
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
            linear-gradient({T['overlay_1']}, {T['overlay_2']}),
            url('data:image/png;base64,{bg_image}');
        background-size: cover;
        background-position: center top;
        background-attachment: fixed;
    """
else:
    background_css = f"background-color: {T['fallback_bg']};"

st.markdown(f"""
<style>
    .stApp {{ {background_css} }}
    .block-container {{
        margin-left: 22% !important;
        margin-right: 5% !important;
        max-width: 720px !important;
    }}
    .hero {{
        background: linear-gradient(135deg, {T['hero_grad_1']} 0%, {T['hero_grad_2']} 100%);
        padding: 40px 32px; border-radius: 16px; margin-bottom: 20px;
        border: 1px solid {T['border']}; box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        backdrop-filter: blur(8px);
    }}
    .hero h1 {{ margin: 0; font-size: 32px; color: {T['text_primary']}; }}
    .hero p {{ color: {T['text_secondary']}; margin-top: 8px; font-size: 15px; }}
    .emergency-card {{
        background: linear-gradient(135deg, rgba(139,26,26,0.45) 0%, {T['card_bg']} 100%);
        border: 1px solid #7A2E2E; border-radius: 14px; padding: 20px; margin-bottom: 16px;
        backdrop-filter: blur(8px);
    }}
    .cyber-card {{
        background: linear-gradient(135deg, rgba(30,58,95,0.55) 0%, {T['card_bg']} 100%);
        border: 1px solid #2E5A7A; border-radius: 14px; padding: 20px; margin-bottom: 16px;
        backdrop-filter: blur(8px);
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {T['card_bg']}; border-radius: 14px; backdrop-filter: blur(8px);
    }}
    .stTextInput input {{
        border-radius: 10px; padding: 12px; border: 1px solid {T['border']};
        background-color: {T['input_bg']}; color: {T['input_text']};
    }}
    .stTextInput input:focus {{ border-color: {ACCENT}; box-shadow: 0 0 0 1px {ACCENT}; }}
    div[data-testid="stButton"] button {{
        border-radius: 10px; padding: 10px 28px; font-weight: 600;
        background-color: {ACCENT}; color: #0E1117; border: none; transition: all 0.2s ease;
        width: 100%;
    }}
    div[data-testid="stButton"] button:hover {{ background-color: #00E5C7; transform: translateY(-1px); }}
    .emergency-btn button {{
        background-color: #7A2E2E !important; color: #FFFFFF !important;
        border: 1px solid #FF6B6B !important;
    }}
    .emergency-btn button:hover {{ background-color: #9C3838 !important; }}
    .cyber-btn button {{
        background-color: #1E3A5F !important; color: #FFFFFF !important;
        border: 1px solid #4A90D9 !important;
    }}
    .cyber-btn button:hover {{ background-color: #2A4E7A !important; }}
    .danger-btn button {{
        background-color: #7A2E2E !important; color: #FFFFFF !important;
        border: 1px solid #FF6B6B !important; width: auto !important; padding: 6px 16px !important;
    }}
    div[data-testid="stMarkdownContainer"] p {{ font-size: 16px; line-height: 1.6; color: {T['text_body']}; }}
    label[data-testid="stWidgetLabel"] p {{ color: {T['text_body']} !important; font-weight: 500; }}
    div[data-testid="stExpander"] {{
        background-color: {T['card_bg_light']}; border-radius: 10px; border: 1px solid {T['border']};
        margin-bottom: 8px;
    }}
    .news-card {{
        background-color: {T['card_bg_light']}; border: 1px solid {T['border']}; border-radius: 10px;
        padding: 12px 14px; margin-bottom: 8px; display: flex; align-items: center; gap: 10px;
    }}
    .theme-toggle-row {{ display: flex; justify-content: flex-end; margin-bottom: 6px; }}

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
        .emergency-card p:first-child, .cyber-card p:first-child {{ font-size: 16px !important; }}
    }}
</style>
""", unsafe_allow_html=True)

# ---------------- Top control row: theme toggle ----------------
top_spacer, top_toggle_col = st.columns([5, 1.4])
with top_toggle_col:
    is_light = st.toggle("☀️ Light" if st.session_state["theme"] == "dark" else "☀️ Light",
                          value=(st.session_state["theme"] == "light"), key="theme_switch")
    new_theme = "light" if is_light else "dark"
    if new_theme != st.session_state["theme"]:
        st.session_state["theme"] = new_theme
        st.rerun()

st.markdown(f"""
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

# ---------------- Persistent storage (with migration) ----------------
DB_PATH = "complaints.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id TEXT, category TEXT, description TEXT,
        timestamp TEXT, feedback TEXT
    )""")
    for col_def in ["original_query TEXT", "ai_response TEXT", "translated_response TEXT", "language TEXT"]:
        try:
            conn.execute(f"ALTER TABLE complaints ADD COLUMN {col_def}")
        except sqlite3.OperationalError:
            pass
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

def delete_complaint(ticket_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM complaints WHERE ticket_id=?", (ticket_id,))
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
                "city": data.get("city", ""), "region": data.get("regionName", ""),
                "lat": data.get("lat"), "lon": data.get("lon"),
            }
    except Exception:
        pass
    return None

def maps_link(lat, lon, query):
    return f"https://www.google.com/maps/search/{query}/@{lat},{lon},15z"

def maps_link_by_name(place_query):
    return f"https://www.google.com/maps/search/{place_query.replace(' ', '+')}"

# ---------------- NEW: Local health & civic news (Google News RSS, no key needed) ----------------
@st.cache_data(show_spinner=False, ttl=1800)
def get_local_news(city):
    query = f"{city} health OR civic OR municipal" if city else "India civic health news"
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:6]:
            title_lower = entry.title.lower()
            icon = "🏥" if any(w in title_lower for w in ["health", "hospital", "disease", "medical"]) else "🏙️"
            items.append({
                "title": entry.title,
                "link": entry.link,
                "source": entry.get("source", {}).get("title", "News"),
                "icon": icon,
            })
        return items
    except Exception:
        return []

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
    <p style="font-size:14px; margin-bottom:0;">
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

detected_city = None

if st.session_state.get("show_emergency"):
    with st.spinner("Locating your area..."):
        client_ip = st.context.ip_address
        location_data = get_location_by_ip(client_ip)

    if location_data and location_data.get("city"):
        detected_city = location_data["city"]
        st.success(f"📍 Estimated location: {location_data['city']}, {location_data['region']}")
        lat, lon = location_data["lat"], location_data["lon"]
        hospital_link = maps_link(lat, lon, "hospital") if lat else maps_link_by_name(f"hospital near {location_data['city']}")
        police_link = maps_link(lat, lon, "police+station") if lat else maps_link_by_name(f"police station near {location_data['city']}")
    else:
        st.info("Couldn't auto-detect your area. Enter your city for accurate map links.")
        manual_city = st.text_input("Your city:", key="manual_city_input")
        detected_city = manual_city if manual_city else None
        hospital_link = maps_link_by_name(f"hospital near {manual_city}") if manual_city else None
        police_link = maps_link_by_name(f"police station near {manual_city}") if manual_city else None

    st.markdown("""
    <div style="background-color:rgba(28,35,51,0.15); padding:18px; border-radius:12px; border:1px solid #7A2E2E; margin-top:8px;">
        <p style="font-weight:600; margin-bottom:8px; color:#FF8888;">National Emergency Numbers (India)</p>
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

st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

# ---------------- NEW: Cybersecurity contact section ----------------
st.markdown("""
<div class="cyber-card">
    <p style="font-weight:700; font-size:18px; margin-bottom:4px;">🛡️ Report a Cybercrime</p>
    <p style="font-size:14px; margin-bottom:0;">
        Fraud, hacking, online harassment, or data theft? Contact India's official cybersecurity channels.
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="cyber-btn">', unsafe_allow_html=True)
cyber_clicked = st.button("🛡️ Show Cybersecurity Contacts", key="cyber_check")
st.markdown('</div>', unsafe_allow_html=True)

if cyber_clicked:
    st.session_state["show_cyber"] = not st.session_state.get("show_cyber", False)

if st.session_state.get("show_cyber"):
    st.markdown("""
    <div style="background-color:rgba(30,58,95,0.15); padding:18px; border-radius:12px; border:1px solid #2E5A7A; margin-top:8px;">
        <p style="font-weight:600; margin-bottom:8px; color:#6FB3E0;">Official Cybersecurity Contacts (India)</p>
        <p>📞 <strong>1930</strong> — National Cyber Crime Helpline</p>
        <p>🌐 <strong>cybercrime.gov.in</strong> — National Cyber Crime Reporting Portal</p>
        <p>🖥️ <strong>cert-in.org.in</strong> — CERT-In (Indian Computer Emergency Response Team)</p>
    </div>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("🌐 Report on cybercrime.gov.in", "https://www.cybercrime.gov.in")
    with col2:
        st.link_button("🖥️ Visit CERT-In", "https://www.cert-in.org.in")

st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

# ---------------- NEW: Local health & civic news dropdown ----------------
with st.expander("📰 Local Health & Civic News", expanded=False):
    news_city = detected_city or st.session_state.get("news_city_override")
    if not news_city:
        news_city = st.text_input("City for news (leave blank for general India news):", key="news_city_override")

    with st.spinner("Fetching latest news..."):
        news_items = get_local_news(news_city)

    if news_items:
        for item in news_items:
            st.markdown(f"""
            <div class="news-card">
                <div style="font-size:28px;">{item['icon']}</div>
                <div style="flex:1;">
                    <p style="margin:0; font-weight:600; font-size:14px;">{item['title']}</p>
                    <p style="margin:0; font-size:12px; color:{T['muted']};">{item['source']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.link_button(f"Read: {item['title'][:40]}{'...' if len(item['title']) > 40 else ''}", item["link"], key=f"news_{item['link'][:50]}")
    else:
        st.caption("Couldn't load news right now — try again shortly.")

st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

# ---------------- Browse all tickets — view + delete ----------------
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

                st.markdown("---")
                confirm_key = f"confirm_del_{tid}"
                if not st.session_state.get(confirm_key):
                    st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                    if st.button("🗑️ Delete this ticket", key=f"del_{tid}"):
                        st.session_state[confirm_key] = True
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.warning("Delete this ticket permanently? This can't be undone.")
                    dcol1, dcol2 = st.columns(2)
                    with dcol1:
                        if st.button("✅ Yes, delete", key=f"confirm_{tid}"):
                            delete_complaint(tid)
                            st.session_state.pop(confirm_key, None)
                            st.toast(f"{tid} deleted.")
                            st.rerun()
                    with dcol2:
                        if st.button("Cancel", key=f"cancel_{tid}"):
                            st.session_state.pop(confirm_key, None)
                            st.rerun()
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
                f"<span style='color:{T['muted']};font-size:12px'>{short_desc} · {ts}</span>",
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
    <div style="background-color:{T['card_bg_solid']}; padding:20px; border-radius:12px; margin-top:10px; border: 1px solid {T['border']}; backdrop-filter: blur(8px);">
        <p style="color:{ACCENT}; font-weight:600; margin-bottom:6px;">Reply</p>
        <p>{reply}</p>
    </div>
    """, unsafe_allow_html=True)

    if translated_reply:
        st.markdown(f"""
        <div style="background-color:{T['card_bg_solid']}; padding:20px; border-radius:12px; margin-top:10px; border: 1px solid {T['border']}; backdrop-filter: blur(8px);">
            <p style="color:{ACCENT}; font-weight:600; margin-bottom:6px;">Translated ({lang_used})</p>
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