import streamlit as st
import mysql.connector
from streamlit_autorefresh import st_autorefresh
from datetime import date, time

# ---------------- DATABASE CONFIG ----------------
DB_CONFIG = {
    "host": "82.180.143.66",
    "user": "u263681140_students",
    "password": "testStudents@123",
    "database": "u263681140_students"
}

# ---------------- USERS (DEMO) ----------------
USERS = {
    "admin": {"password": "admin123", "role": "Admin"},
    "user": {"password": "user123", "role": "User"}
}

# ---------------- DB CONNECTION ----------------
def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# ---------------- AUTO TABLE CREATION ----------------
def create_tables():
    conn = get_db()
    cursor = conn.cursor()

    # Live parking status table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS LiveParkingSystem (
        id INT AUTO_INCREMENT PRIMARY KEY,
        S1 INT DEFAULT 1,
        S2 INT DEFAULT 1,
        S3 INT DEFAULT 1,
        S4 INT DEFAULT 1
    )
    """)

    # Insert default row if empty
    cursor.execute("SELECT COUNT(*) FROM LiveParkingSystem")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO LiveParkingSystem (S1,S2,S3,S4)
            VALUES (1,1,1,1)
        """)

    # Slot booking table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS slot_bookings (
        booking_id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50),
        slot_no VARCHAR(5),
        booking_date DATE,
        start_time TIME,
        end_time TIME,
        booking_status ENUM(
            'BOOKED','APPROVED','REJECTED','CANCELLED','COMPLETED'
        ) DEFAULT 'BOOKED',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Slot control table (ESP32)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS slot_control (
        slot_no VARCHAR(5) PRIMARY KEY,
        lock_status INT DEFAULT 0
    )
    """)

    # Insert slots if not exists
    for slot in ["S1","S2","S3","S4"]:
        cursor.execute("""
            INSERT IGNORE INTO slot_control (slot_no, lock_status)
            VALUES (%s, 0)
        """, (slot,))

    conn.commit()
    conn.close()

# ---------------- INITIALIZE DB ----------------
create_tables()

# ---------------- FETCH LIVE STATUS ----------------
def get_live_status():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT S1,S2,S3,S4 FROM LiveParkingSystem LIMIT 1")
    data = cursor.fetchone()
    conn.close()
    return data

# ---------------- SLOT CARD UI ----------------
def slot_card(slot, value):
    if value == 1:
        color = "#d4edda"
        status = "Available ✅"
    else:
        color = "#f8d7da"
        status = "Booked ❌"

    st.markdown(
        f"""
        <div style="background:{color};
                    padding:20px;
                    border-radius:12px;
                    text-align:center;
                    font-size:18px;
                    font-weight:bold;">
            🚗 {slot}<br>{status}
        </div>
        """, unsafe_allow_html=True
    )

# ---------------- BOOKING OVERLAP CHECK ----------------
def check_overlap(slot, b_date, start, end):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM slot_bookings
        WHERE slot_no=%s
        AND booking_date=%s
        AND booking_status IN ('BOOKED','APPROVED')
        AND (%s < end_time AND %s > start_time)
    """, (slot, b_date, start, end))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

# ---------------- BOOK SLOT ----------------
def book_slot(username, slot, b_date, start, end):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO slot_bookings
        (username, slot_no, booking_date, start_time, end_time)
        VALUES (%s,%s,%s,%s,%s)
    """, (username, slot, b_date, start, end))
    conn.commit()
    conn.close()

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ================= LOGIN =================
if not st.session_state.logged_in:
    st.title("🔐 Live Parking System Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USERS and USERS[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = USERS[username]["role"]
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid credentials")

# ================= DASHBOARD =================
else:
    st_autorefresh(interval=5000, key="refresh")

    st.title("🚗 Live Parking System")
    st.write(f"👤 Role: **{st.session_state.role}**")

    tabs = ["Live Status"]
    if st.session_state.role == "User":
        tabs += ["Book Slot", "My Bookings"]
    if st.session_state.role == "Admin":
        tabs += ["Admin Approval"]
    tabs += ["Logout"]

    pages = st.tabs(tabs)

    # -------- LIVE STATUS --------
    with pages[0]:
        data = get_live_status()
        available = sum(1 for v in data.values() if v == 1)

        st.markdown(
            f"""
            <div style="background:#cce5ff;
                        padding:15px;
                        border-radius:10px;
                        text-align:center;
                        font-size:20px;
                        font-weight:bold;">
                📊 Available Slots : {available}
            </div>
            """, unsafe_allow_html=True
        )

        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)
        with c1: slot_card("S1", data["S1"])
        with c2: slot_card("S2", data["S2"])
        with c3: slot_card("S3", data["S3"])
        with c4: slot_card("S4", data["S4"])

    # -------- USER BOOKING --------
    if st.session_state.role == "User":
        with pages[1]:
            st.subheader("🅿️ Book Slot")
            slot = st.selectbox("Slot", ["S1","S2","S3","S4"])
            b_date = st.date_input("Date", min_value=date.today())
            start = st.time_input("Start Time", time(9,0))
            end = st.time_input("End Time", time(10,0))

            if st.button("Book"):
                if start >= end:
                    st.error("Invalid time")
                elif check_overlap(slot, b_date, start, end):
                    st.error("Slot already booked")
                else:
                    book_slot(st.session_state.username, slot, b_date, start, end)
                    st.success("Booking sent for admin approval")

    # -------- ADMIN APPROVAL --------
    if st.session_state.role == "Admin":
        with pages[1]:
            st.subheader("🛠 Admin Approval")
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM slot_bookings
                WHERE booking_status='BOOKED'
            """)
            rows = cursor.fetchall()

            for r in rows:
                with st.expander(f"Booking #{r['booking_id']} - {r['slot_no']}"):
                    st.write(r)
                    if st.button("Approve", key=f"a{r['booking_id']}"):
                        cursor.execute("""
                            UPDATE slot_bookings
                            SET booking_status='APPROVED'
                            WHERE booking_id=%s
                        """,(r['booking_id'],))
                        conn.commit()
                        st.success("Approved")

            conn.close()

    # -------- LOGOUT --------
    with pages[-1]:
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
