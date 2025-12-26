import streamlit as st
import mysql.connector
from streamlit_autorefresh import st_autorefresh

# ---------------- DATABASE CONFIG ----------------
DB_CONFIG = {
    "host": "82.180.143.66",
    "user": "u263681140_students",
    "password": "testStudents@123",
    "database": "u263681140_students"
}

# ---------------- LOGIN CREDENTIALS ----------------
USERS = {
    "admin": {"password": "admin123", "role": "Admin"},
    "user": {"password": "user123", "role": "User"}
}

# ---------------- FUNCTIONS ----------------
def get_parking_status():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT S1, S2, S3, S4 FROM LiveParkingSystem LIMIT 1")
    data = cursor.fetchone()
    cursor.close()
    conn.close()
    return data

def slot_card(slot, value):
    if value == 1:
        st.markdown(
            f"""
            <div style="background:#d4edda;padding:20px;border-radius:10px;
                        text-align:center;font-size:18px;font-weight:bold;">
                🚗 {slot}<br>✅ Available
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(
            f"""
            <div style="background:#f8d7da;padding:20px;border-radius:10px;
                        text-align:center;font-size:18px;font-weight:bold;">
                🚗 {slot}<br>❌ Booked
            </div>
            """, unsafe_allow_html=True)

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------- LOGIN PAGE ----------------
if not st.session_state.logged_in:
    st.title("🔐 Live Parking System Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USERS and USERS[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.role = USERS[username]["role"]
            st.success(f"Logged in as {st.session_state.role}")
            st.rerun()
        else:
            st.error("Invalid username or password")

# ---------------- MAIN DASHBOARD ----------------
else:
    st_autorefresh(interval=5000, key="parking_refresh")

    st.title("🚗 Live Parking System")
    st.subheader(f"Role : {st.session_state.role}")

    data = get_parking_status()

    if data:
        available_count = sum(1 for v in data.values() if v == 1)

        st.markdown(
            f"""
            <div style="background:#cce5ff;padding:15px;border-radius:10px;
                        font-size:20px;font-weight:bold;text-align:center;">
                📊 Total Available Slots : {available_count}
            </div>
            """, unsafe_allow_html=True)

        st.write("")

        col1, col2 = st.columns(2)
        col3, col4 = st.columns(2)

        with col1:
            slot_card("S1", data["S1"])
        with col2:
            slot_card("S2", data["S2"])
        with col3:
            slot_card("S3", data["S3"])
        with col4:
            slot_card("S4", data["S4"])

    else:
        st.error("No parking data found")

    st.write("")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
