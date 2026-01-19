import streamlit as st
from dotenv import load_dotenv
import os
from openai import OpenAI
from datetime import datetime
import csv
from pathlib import Path
import hashlib

USERS_FILE = "users.csv"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def user_exists(email):
    if not Path(USERS_FILE).exists():
        return False
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return any(email == row.split(",")[0] for row in f.readlines()[1:])

def create_user(email, password):
    file_exists = Path(USERS_FILE).exists()
    with open(USERS_FILE, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write("email,password,created_at\n")
        f.write(f"{email},{hash_password(password)},{datetime.utcnow()}\n")

def authenticate_user(email, password):
    if not Path(USERS_FILE).exists():
        return False
    hashed = hash_password(password)
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        for row in f.readlines()[1:]:
            e, p, _ = row.strip().split(",")
            if e == email and p == hashed:
                return True
    return False


# ---------- FILE PATHS ----------
FEEDBACK_FILE = Path("feedback.csv")
ANALYTICS_FILE = Path("analytics.csv")

def save_feedback(row):
    file_exists = FEEDBACK_FILE.exists()
    with open(FEEDBACK_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["time","helpful","comment","expert_mode"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def save_analytics(row):
    file_exists = ANALYTICS_FILE.exists()
    with open(ANALYTICS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["time","event"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Startup AI", layout="centered")
PLAN_FEATURES = {
    "free": {
        "expert_modes": [
            "Idea Validator",
            "MVP Architect",
            "Pricing Strategist",
            "GTM Advisor"
        ],
        "memory": True
    },
    "premium": {
        "expert_modes": [
            "Idea Validator",
            "MVP Architect",
            "Pricing Strategist",
            "GTM Advisor"
        ],
        "memory": True
    }
}


# ---------- GLOBAL CSS ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1 { font-weight: 700; }
.stChatMessage { font-size: 16px; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

# ---------- OPENAI CLIENT ----------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------- SESSION STATE ----------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_email" not in st.session_state:
    st.session_state.user_email = None

    if "logged_in" not in st.session_state:
       st.session_state.logged_in = False

if "user_email" not in st.session_state:
    st.session_state.user_email = "guest"

if "user_type" not in st.session_state:
    st.session_state.user_type = "guest"
    if "user_plan" not in st.session_state:
      st.session_state.user_plan = "free"   # free | premium

if "premium_unlocked" not in st.session_state:
    st.session_state.premium_unlocked = True  # TRUE = hidden premium (everyone free)



if "usage_count" not in st.session_state: st.session_state.usage_count = 0
if "feedback_submitted" not in st.session_state: st.session_state.feedback_submitted = False
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role":"system","content":"You are a brutally honest senior startup advisor. You ONLY help product-based startups. No services, freelancing, or agencies. Be practical, structured, and direct."}]
if "intake_step" not in st.session_state: st.session_state.intake_step = 0
if "product_context" not in st.session_state: st.session_state.product_context = {}
if "message_count" not in st.session_state: st.session_state.message_count = 0
if "first_visit_shown" not in st.session_state: st.session_state.first_visit_shown = False

# ---------- FIRST-TIME WELCOME POPUP WITH SHARE BUTTON ----------
if not st.session_state.first_visit_shown:
    st.session_state.first_visit_shown = True

    shareable_link = "https://your-app-link.streamlit.app/"  # <-- replace with your real deployed URL

    st.info(f"""
👋 **Welcome to Product Startup Assistant!**

I help founders build **product-based startups**.  

**How to start:**  
1️⃣ Answer a few questions about your product.  
2️⃣ Choose an *Expert Mode* from the sidebar.  
3️⃣ Ask your startup questions and get honest, structured advice.  

✨ **Tip:** Share this app with your friends building startups!
""")

    # ---------- COPY LINK BUTTON ----------
    if st.button("📎 Copy Shareable Link"):
        st.write(f"Copied to clipboard: {shareable_link}")
        st.experimental_set_query_params(link=shareable_link)  # optional tracking
        st.toast("✅ Link copied! Share it with your friends.")  # small popup notification


# ---------- SIDEBAR ----------
with st.sidebar:
    st.header("Controls")
    st.markdown("### Expert Mode")
    expert_mode = st.radio(
        "Choose advisor",
        ["Idea Validator","Pricing Strategist","marketing strategist"]
    )

    st.markdown("### Product Memory")
    if st.session_state.product_context:
        for k,v in st.session_state.product_context.items():
            st.write(f"**{k.replace('_',' ').title()}**: {v}")
    else:
        st.write("No product context yet.")

    if st.button(" Clear Chat"):
        st.session_state.messages = st.session_state.messages[:1]
        st.session_state.product_context = {}
        st.session_state.intake_step = 0
        st.session_state.message_count = 0
        st.session_state.usage_count = 0
        st.session_state.feedback_submitted = False
        st.success("Chat cleared")

st.markdown("---")
st.markdown("### Internal Stats")
st.caption(f"Feedback entries: {sum(1 for _ in open(FEEDBACK_FILE)) - 1}" if FEEDBACK_FILE.exists() else "No feedback yet")
st.caption(f"Messages sent: {sum(1 for _ in open(ANALYTICS_FILE)) - 1}" if ANALYTICS_FILE.exists() else "No usage data yet")

with st.sidebar:
    st.header("Account")

    if st.session_state.logged_in:
        st.success(f"Logged in as {st.session_state.user_email}")

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_email = "guest"
            st.session_state.user_type = "guest"
            st.rerun()

    else:
        st.info("You are using the app as a Guest")

        with st.expander("Login / Sign up (Optional)"):
            tab1, tab2 = st.tabs(["Login", "Sign up"])

            with tab1:
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_pass")

                if st.button("Login"):
                    if authenticate_user(email, password):
                        st.session_state.logged_in = True
                        st.session_state.user_email = email
                        st.session_state.user_type = "user"
                        st.success("Logged in")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")

            with tab2:
                email = st.text_input("Email", key="signup_email")
                password = st.text_input("Password", type="password", key="signup_pass")

                if st.button("Create account"):
                    if user_exists(email):
                        st.error("User already exists")
                    else:
                        create_user(email, password)
                        st.success("Account created. You can login now.")

# ---------- PREMIUM CTA (HIDDEN FOR NOW) ----------

# if not st.session_state.premium_unlocked:
#     st.markdown("---")
#     st.markdown("### Premium")
#     st.caption("Unlock advanced startup guidance")
#     st.button("Upgrade to Premium")


    

# ---------- TITLE ----------
st.title("Startup AI Assistant")
st.markdown("""
This assistant is **ONLY for product-based startups**.

It helps with:
- Idea validation  
- Pricing strategy  
- Go-to-market planning  

Answer a few questions first 👇
""")
st.markdown("---")

# ---------- DISPLAY CHAT ----------
for msg in st.session_state.messages[1:]:
    st.chat_message(msg["role"]).write(msg["content"])

# ---------- INTAKE QUESTIONS ----------
intake_questions = [
    ("product_name","What is your product name (or working title)?"),
    ("product_type","What type of product is this? (SaaS, App, Tool, Platform)"),
    ("target_user","Who is the target user? Be specific."),
    ("problem","What painful problem does this product solve?"),
    ("stage","What stage are you at? (Idea, MVP, Launched)"),
    ("goal","What do you want help with right now?"),
    ("place", "where do u wanna sell yor product. give me the name of the country name and other which could help me to undurstand.")
]

mode_prompts = {
    "Idea Validator": "Validate the idea. Be brutally honest.tell in simpelest way pssible.",
    "Pricing Strategist": "Suggest pricing based on value.",
    "markateing strategist": "Suggest early go-to-market tactics.give market strategies acording to the place and timeing and financial codition. "
}

# ---------- PLAN ACCESS CHECK (HIDDEN FOR NOW) ----------

allowed_modes = PLAN_FEATURES[st.session_state.user_plan]["expert_modes"]

# Premium lock (disabled for MVP launch)
if not st.session_state.premium_unlocked:
    if expert_mode not in allowed_modes:
        st.warning("🔒 This expert mode is part of Premium")
        st.stop()


# ---------- FIRST QUESTION ----------
if st.session_state.intake_step == 0 and len(st.session_state.messages)==1:
    q = intake_questions[0][1]
    st.session_state.messages.append({"role":"assistant","content":q})
    st.chat_message("assistant").write(q)

# ---------- USER INPUT ----------
user_input = st.chat_input("Describe your product idea or startup challenge")

if user_input:
    # Count usage only after intake
    if st.session_state.intake_step >= len(intake_questions):
        st.session_state.usage_count += 1

    save_analytics({"time": str(datetime.utcnow()), "event": "user_message"})
    st.session_state.message_count += 1
    st.session_state.messages.append({"role":"user","content":user_input})
    st.chat_message("user").write(user_input)

    # ----- INTAKE FLOW -----
    if st.session_state.intake_step < len(intake_questions):
        key,_ = intake_questions[st.session_state.intake_step]
        st.session_state.product_context[key] = user_input
        st.session_state.intake_step += 1

        if st.session_state.intake_step < len(intake_questions):
            reply = f"Got it.\n\n**Next:** {intake_questions[st.session_state.intake_step][1]}"
        else:
            reply = " Thanks. I understand your product.\n\nAsk anything now."

    else:
        # ----- CHAT REPLY -----
        try:
            with st.spinner("Thinking like a startup advisor..."):
                context = "\n".join([f"{k}: {v}" for k,v in st.session_state.product_context.items()])
                response = client.responses.create(
                    model="gpt-4.1-mini",
                    input=[{"role":"system","content":f"Expert mode: {expert_mode}\nBehavior: {mode_prompts[expert_mode]}\n\nProduct context:\n{context}"}] + st.session_state.messages,
                    temperature=0.4
                )
                reply = response.output_text
        except Exception as e:
            reply = f"⚠️ Error: {e}"

    st.session_state.messages.append({"role":"assistant","content":reply})
    st.chat_message("assistant").write(reply)

# ---------- DELAYED FEEDBACK ----------
if (st.session_state.intake_step >= len(intake_questions)
    and st.session_state.usage_count >= 3
    and not st.session_state.feedback_submitted):
    
    st.markdown("---")
    st.markdown("### 🙏 Quick feedback (takes 10 seconds)")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("👍 Helpful"):
            save_feedback({"time": str(datetime.utcnow()),"helpful": True,"comment":"","expert_mode": expert_mode})
            st.session_state.feedback_submitted = True
            st.success("Thanks! This really helps 🙌")

    with col2:
        comment = st.text_area("What was missing or unclear?", key="feedback_comment")
        if st.button("👎 Not helpful"):
            if comment.strip() == "":
                comment = "No comment provided"
            save_feedback({"time": str(datetime.utcnow()),"helpful": False,"comment":comment,"expert_mode": expert_mode})
            st.session_state.feedback_submitted = True
            st.success("Thanks for the honest feedback 🙏")
