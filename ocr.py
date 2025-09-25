import streamlit as st
import mysql.connector
import hashlib
import datetime
import pandas as pd

# ---- MySQL Config ----
db_config = {
 'host': 'srv1020.hstgr.io',       # Change if deployed
    'user': 'u830421930_soft',
    'password': 'BillingSoft12!@',
    'database': 'u830421930_soft'
}

# ---- Helper Functions ----
def get_db_connection():
    return mysql.connector.connect(**db_config)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100) UNIQUE,
            password VARCHAR(255),
            role ENUM('admin', 'student') DEFAULT 'student'
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            course_name VARCHAR(255),
            course_description TEXT,
            seats_available INT
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            course_id INT,
            registration_date DATE,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

def register_user(name, email, password):
    hashed_pw = hash_password(password)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (name, email, hashed_pw)
        )
        conn.commit()
        return True
    except mysql.connector.IntegrityError:
        return False
    finally:
        cursor.close()
        conn.close()

def authenticate_user(email, password):
    hashed_pw = hash_password(password)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s",
        (email, hashed_pw)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def get_courses():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()
    cursor.close()
    conn.close()
    return courses

def add_course(course_name, course_desc, seats):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO courses (course_name, course_description, seats_available) VALUES (%s, %s, %s)",
        (course_name, course_desc, seats)
    )
    conn.commit()
    cursor.close()
    conn.close()

def register_for_course(user_id, course_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM registrations WHERE user_id=%s AND course_id=%s",
        (user_id, course_id)
    )
    existing = cursor.fetchone()

    if existing:
        cursor.close()
        conn.close()
        return False

    cursor.execute(
        "INSERT INTO registrations (user_id, course_id, registration_date) VALUES (%s, %s, %s)",
        (user_id, course_id, datetime.date.today())
    )
    conn.commit()
    cursor.close()
    conn.close()
    return True

# ✅ New Helper Function: Get All Registrations with Details
def get_registrations():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.id, u.name AS student_name, c.course_name, r.registration_date
        FROM registrations r
        JOIN users u ON r.user_id = u.id
        JOIN courses c ON r.course_id = c.id
    """)
    registrations = cursor.fetchall()
    cursor.close()
    conn.close()
    return registrations

# ---- Main App ----
def main():
    st.title("🎓 Online Course Registration System")

    create_tables()

    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None

    if not st.session_state.logged_in:
        menu = ["Login", "Register"]
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Register":
            st.subheader("📝 Register New Account")
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type='password')

            if st.button("Create Account"):
                success = register_user(name, email, password)
                if success:
                    st.success("✅ Account created successfully! Please login.")
                else:
                    st.error("❌ Email already exists.")

        elif choice == "Login":
            st.subheader("🔐 Login")
            email = st.text_input("Email")
            password = st.text_input("Password", type='password')

            if st.button("Login"):
                user = authenticate_user(email, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                else:
                    st.error("❌ Invalid email or password.")

    else:
        user = st.session_state.user
        st.info(f"Logged in as: {user['name']} ({user['role']})")

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user = None

        # ➤ Admin Dashboard
        if user['role'] == 'admin':
            st.subheader("🛠️ Admin Dashboard")

            st.write("📚 Existing Courses")
            courses = get_courses()
            st.table(pd.DataFrame(courses))

            st.write("--- ➕ Add New Course ---")
            course_name = st.text_input("Course Name", key="course_name")
            course_desc = st.text_area("Course Description", key="course_desc")
            seats = st.number_input("Seats Available", min_value=1, step=1, key="seats")

            if st.button("Add Course"):
                if course_name.strip() == "" or course_desc.strip() == "":
                    st.warning("⚠️ Please fill in all course details.")
                else:
                    add_course(course_name, course_desc, seats)
                    st.success("✅ New course added successfully!")

            st.write("--- 📋 Registered Courses ---")
            registrations = get_registrations()
            if registrations:
                st.table(pd.DataFrame(registrations))
            else:
                st.info("No course registrations yet.")

        # ➤ Student Dashboard
        else:
            st.subheader("📚 Available Courses")

            courses = get_courses()
            st.table(pd.DataFrame(courses))

            selected_course_id = st.number_input("Enter Course ID to Register", min_value=1, key="selected_course_id")

            if st.button("Register for Course"):
                success = register_for_course(user['id'], selected_course_id)
                if success:
                    st.success("✅ Course registration successful!")
                else:
                    st.warning("⚠️ You are already registered for this course.")

if __name__ == '__main__':
    main()
