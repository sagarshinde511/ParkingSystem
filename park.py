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

# ---------------- FETCH LIVE STATUS ----------------
def get_live_status():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT S1,S2,S3,S4 FROM LiveParkingSystem LIMIT 1")
    data = cursor.fetchone()
    conn.close()
    return data

# ---------------- SLOT CARD ----------------
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
    query = """
    SELECT COUNT(*) FROM slot_bookings
    WHERE slot_no=%s
    AND booking_date=%s
    AND booking_status IN ('BOOKED','APPROVED')
    AND (%s < end_time AND %s > start_time)
    """
    cursor.execute(query, (slot, b_date, start, end))
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

# ================= LOGIN PAGE =================
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
    st.write(f"👤 Logged in as **{st.session_state.role}**")

    tabs = ["Live Status"]

    if st.session_state.role == "User":
        tabs.extend(["Book Slot", "My Bookings"])

    if st.session_state.role == "Admin":
        tabs.append("Admin Approval")

    tabs.append("Logout")

    selected_tab = st.tabs(tabs)

    # ---------------- LIVE STATUS ----------------
    with selected_tab[0]:
        data = get_live_status()

        if data:
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

            col1, col2 = st.columns(2)
            col3, col4 = st.columns(2)

            with col1: slot_card("S1", data["S1"])
            with col2: slot_card("S2", data["S2"])
            with col3: slot_card("S3", data["S3"])
            with col4: slot_card("S4", data["S4"])

    # ---------------- USER BOOK SLOT ----------------
    if st.session_state.role == "User":
        with selected_tab[1]:
            st.subheader("🅿️ Book Slot (Advance)")

            slot = st.selectbox("Select Slot", ["S1","S2","S3","S4"])
            b_date = st.date_input("Booking Date", min_value=date.today())
            start_time = st.time_input("Start Time", time(9,0))
            end_time = st.time_input("End Time", time(10,0))

            if st.button("Book Slot"):
                if start_time >= end_time:
                    st.error("Invalid time range")
                elif check_overlap(slot, b_date, start_time, end_time):
                    st.error("Slot already booked")
                else:
                    book_slot(st.session_state.username, slot, b_date, start_time, end_time)
                    st.success("Booking request sent for admin approval")

        # ---------------- MY BOOKINGS ----------------
        with selected_tab[2]:
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

    # ---------------- ADMIN APPROVAL ----------------
    if st.session_state.role == "Admin":
        with selected_tab[1]:
            st.subheader("🛠 Admin Booking Approval")

            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM slot_bookings
                WHERE booking_status='BOOKED'
            """)
            bookings = cursor.fetchall()

            for b in bookings:
                with st.expander(f"Booking #{b['booking_id']} | {b['slot_no']}"):
                    st.write(b)

                    col1, col2 = st.columns(2)
                    if col1.button("Approve", key=f"a{b['booking_id']}"):
                        cursor.execute("""
                            UPDATE slot_bookings
                            SET booking_status='APPROVED'
                            WHERE booking_id=%s
                        """,(b['booking_id'],))
                        conn.commit()
                        st.success("Approved")

                    if col2.button("Reject", key=f"r{b['booking_id']}"):
                        cursor.execute("""
                            UPDATE slot_bookings
                            SET booking_status='REJECTED'
                            WHERE booking_id=%s
                        """,(b['booking_id'],))
                        conn.commit()
                        st.warning("Rejected")

            conn.close()

    # ---------------- LOGOUT ----------------
    with selected_tab[-1]:
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
