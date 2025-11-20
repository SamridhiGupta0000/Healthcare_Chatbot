import streamlit as st
from backend import knowledge_base

st.set_page_config(page_title="MEDITALK", layout="wide")

# Theme (light/dark)
if "theme" not in st.session_state:
    st.session_state.theme = "light"
theme = st.radio("Choose Theme:", ("light", "dark"))
st.session_state.theme = theme

# Colors
if theme == "dark":
    bg, text, card, sidebar, input_bg, result_bg = (
        "#0a0a0a", "white", "#141414",
        "linear-gradient(180deg, #550a8a, #0f3d63)",
        "#1a1a1a", "#0f0f0f"
    )
else:
    bg, text, card, sidebar, input_bg, result_bg = (
        "#ffffff", "black", "#ffffff",
        "linear-gradient(180deg, #e5ff8a, #9fffd6)",
        "#f5f5f5", "#eef7ff"
    )

# Custom CSS
st.markdown(f"""
<style>
body {{
    background-color: {bg};
    color: {text};
    font-family: 'Poppins', sans-serif;
}}

.wrapper {{
    border-radius:20px;
    padding:20px;
}}

.title {{
    font-size:48px;
    font-weight:900;
    text-align:center;
    background: linear-gradient(90deg, red, orange, yellow, green, blue, indigo, violet);
    background-size: 400% 100%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: rainbow-text 6s linear infinite;
    margin-bottom:20px;
}}

@keyframes rainbow-text {{
    0% {{ background-position: 0% 50%; }}
    50% {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}

.main-container {{
    display:grid;
    grid-template-columns:1fr 2fr;
    gap:30px;
    margin-top:20px;
}}

.sidebar-box {{
    background:{sidebar};
    border-radius:20px;
    padding:40px 20px;
    color:white;
    text-align:center;
    box-shadow:0 0 20px rgba(0,0,0,0.25);
}}

.chat-box {{
    background:{card};
    padding:30px;
    border-radius:20px;
    box-shadow:0 0 20px rgba(0,0,0,0.15);
}}

.robot-icon {{
    font-size:85px;
    margin-bottom:10px;
}}

.result-section {{
    background:{result_bg};
    padding:20px;
    border-radius:15px;
    margin-top:20px;
}}

.primary-card {{
    background: linear-gradient(90deg,#e6f7ff,#ffffff);
    padding:18px;
    border-radius:12px;
    box-shadow:0 6px 18px rgba(0,0,0,0.08);
}}
</style>
""", unsafe_allow_html=True)

# Wrapper start
st.markdown("<div class='wrapper'>", unsafe_allow_html=True)
st.markdown("<div class='title'>💬 MEDITALK — Health Checker Chatbot</div>", unsafe_allow_html=True)
st.markdown("<div class='main-container'>", unsafe_allow_html=True)

# LEFT panel (robot)
st.markdown(f"""
<div class='sidebar-box'>
  <div class='robot-icon'>🤖🩺</div>
  <h2 style='margin:0; font-weight:900;'>Doctor Bot</h2>
  <p style='opacity:0.9;'>Your friendly AI health guide</p>
  <hr style="border:1px solid white; opacity:0.3;">
  <p>✔ Symptom analysis</p>
  <p>✔ Disease prioritization</p>
  <p>✔ Precautions & when to see doctor</p>
</div>
""", unsafe_allow_html=True)

# RIGHT panel (chat)
st.markdown("<div class='chat-box'>", unsafe_allow_html=True)

st.markdown("Describe your symptoms (natural language OK). Example: `i have fever and cough`")
symptoms = st.text_input("Symptoms:")
duration = st.text_input("Duration (e.g., 2 days):")
severity = st.selectbox("Severity:", ["Mostly Mild (L1–L2)", "Moderate (L3)", "Severe (L4)"])

if st.button("Analyze"):
    res = knowledge_base.match_disease(symptoms, duration)

    if not res["primary"]:
        st.warning("😕 No matching disease found. Try clearer words like 'fever', 'cough', 'headache' or add duration.")
    else:
        # Emergency banner
        if res["emergency"]:
            st.error("⚠️ Emergency signs detected:")
            for reason in res["emergency_reasons"]:
                st.write("• " + reason)

        # Primary card
        p = res["primary"]
        st.markdown(f"""
        <div class="primary-card">
            <h2>🩺 {p['disease']}</h2>
            <p><b>Matched:</b> {', '.join(p['matched'])}</p>
            <p><b>Duration:</b> {p['duration_days']} day(s)</p>
            <p><b>Score:</b> {p['score']}</p>
            <p style="margin-top:8px;"><b>Quick reassurance/advice:</b></p>
        </div>
        """, unsafe_allow_html=True)

        # Primary details
        st.markdown("<div class='result-section'>", unsafe_allow_html=True)
        st.markdown(f"**Description:**  \n{p['description']}")
        if p['precautions']:
            st.markdown("**Precautions / Care tips:**")
            for pc in p['precautions']:
                st.write("• " + pc)
        st.markdown("</div>", unsafe_allow_html=True)

        # Doctor advice
        if res["doctor_advice"]:
            st.info("**Doctor Advice:**")
            for d in res["doctor_advice"]:
                st.write("• " + d)

        # Secondary
        if res["secondary"]:
            st.markdown("### Other likely causes (secondary)")
            for s in res["secondary"]:
                st.markdown("---")
                st.markdown(f"**{s['disease']}** — Matched: {', '.join(s['matched'])} — Score: {s['score']}")
                if s['description']:
                    st.markdown(f"{s['description']}")
                if s['precautions']:
                    st.markdown("Precautions:")
                    for pc in s['precautions']:
                        st.write("• " + pc)

        # Other
        if res["other"]:
            with st.expander("Less likely / other possibilities (click to view)"):
                for o in res["other"]:
                    st.markdown("---")
                    st.markdown(f"**{o['disease']}** — Matched: {', '.join(o['matched'])} — Score: {o['score']}")
                    if o['description']:
                        st.markdown(f"{o['description']}")
                    if o['precautions']:
                        st.markdown("Precautions:")
                        for pc in o['precautions']:
                            st.write("• " + pc)

st.markdown("</div>", unsafe_allow_html=True)  # chat-box end
st.markdown("</div>", unsafe_allow_html=True)  # main-container end
st.markdown("</div>", unsafe_allow_html=True)  # wrapper end
