import streamlit as st
import mysql.connector
from streamlit_autorefresh import st_autorefresh
from datetime import date, time
import bcrypt

# ---------------- DATABASE CONFIG ----------------
DB_CONFIG = {
    "host": "82.180.143.66",
    "user": "u263681140_students",
    "password": "testStudents@123",
    "database": "u263681140_students"
}

# ---------------- DB CONNECTION ----------------
def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# ---------------- PASSWORD UTILS ----------------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------------- AUTO CREATE TABLES ----------------
def create_tables():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Reg_Users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100),
        email VARCHAR(100) UNIQUE,
        password VARCHAR(255),
        mobile VARCHAR(15),
        role ENUM('Admin','User') DEFAULT 'User',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Live parking status
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS LiveParkingSystem (
        id INT AUTO_INCREMENT PRIMARY KEY,
        S1 INT DEFAULT 1,
        S2 INT DEFAULT 1,
        S3 INT DEFAULT 1,
        S4 INT DEFAULT 1
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM LiveParkingSystem")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO LiveParkingSystem (S1,S2,S3,S4) VALUES (1,1,1,1)")

    # Booking table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS slot_bookings (
        booking_id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100),
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

    # Slot control (ESP32)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS slot_control (
        slot_no VARCHAR(5) PRIMARY KEY,
        lock_status INT DEFAULT 0
    )
    """)

    for slot in ["S1","S2","S3","S4"]:
        cursor.execute(
            "INSERT IGNORE INTO slot_control (slot_no, lock_status) VALUES (%s,0)",
            (slot,)
        )

    conn.commit()
    conn.close()

create_tables()

# ---------------- AUTH ----------------
def authenticate_user(email, password):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Reg_Users WHERE email=%s", (email,))
    user = cursor.fetchone()
    conn.close()
    if user and verify_password(password, user["password"]):
        return user
    return None

def register_user(name, email, password, mobile):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Reg_Users (name, email, password, mobile)
        VALUES (%s,%s,%s,%s)
    """, (name, email, hash_password(password), mobile))
    conn.commit()
    conn.close()

# ---------------- DATA FUNCTIONS ----------------
def get_live_status():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT S1,S2,S3,S4 FROM LiveParkingSystem LIMIT 1")
    data = cursor.fetchone()
    conn.close()
    return data

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

# ---------------- UI HELPERS ----------------
def slot_card(slot, value):
    if value == 1:
        color, text = "#d4edda", "Available ✅"
    else:
        color, text = "#f8d7da", "Booked ❌"

    st.markdown(
        f"""
        <div style="background:{color};
                    padding:20px;
                    border-radius:12px;
                    text-align:center;
                    font-size:18px;
                    font-weight:bold;">
            🚗 {slot}<br>{text}
        </div>
        """, unsafe_allow_html=True
    )

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ================= AUTH PAGES =================
if not st.session_state.logged_in:
    st.title("🔐 Smart Parking System")

    menu = st.selectbox("Select", ["Login", "Register"])

    if menu == "Register":
        st.subheader("📝 User Registration")
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        mobile = st.text_input("Mobile Number")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")

        if st.button("Register"):
            if not all([name, email, mobile, password, confirm]):
                st.error("All fields required")
            elif password != confirm:
                st.error("Passwords do not match")
            else:
                try:
                    register_user(name, email, password, mobile)
                    st.success("Registration successful! Please login.")
                except:
                    st.error("Email already exists")

    if menu == "Login":
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            user = authenticate_user(email, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.username = user["name"]
                st.session_state.role = user["role"]
                st.rerun()
            else:
                st.error("Invalid credentials")

# ================= DASHBOARD =================
else:
    st_autorefresh(interval=5000, key="refresh")

    st.title("🚗 Live Parking System")
    st.write(f"👤 {st.session_state.username} ({st.session_state.role})")

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
            <div style="background:#cce5ff;padding:15px;border-radius:10px;
                        text-align:center;font-size:20px;font-weight:bold;">
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

    # -------- USER BOOK SLOT --------
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
                    st.success("Booking request sent")

        with pages[2]:
            st.subheader("📄 My Bookings")
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT slot_no, booking_date, start_time, end_time, booking_status
                FROM slot_bookings
                WHERE username=%s
                ORDER BY booking_date DESC
            """, (st.session_state.username,))
            rows = cursor.fetchall()
            conn.close()
            if rows:
                st.table(rows)
            else:
                st.info("No bookings found")

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
            for r in cursor.fetchall():
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
