import os
import psycopg2
import streamlit as st


def _get_db_conn():
    """Return a new psycopg2 connection using DATABASE_URL from the environment."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        # Fallback: read from .env file if python-dotenv is not loaded
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DATABASE_URL="):
                        url = line.split("=", 1)[1]
                        break
    return psycopg2.connect(url)

ROLE_PERMISSIONS = {
    "Super Admin": "Full access to all records, downloads, filters, and assistant tools.",
    "Project Manager": "Can monitor project performance, risks, and operational records.",
    "Employee": "Restricted access. Financial data, budgets, downloads, and the AI assistant are not available.",
}


def initialize_session():
    defaults = {
        "logged_in": False,
        "user": None,
        "chat_history": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def authenticate(user_id, password):
    try:
        conn = _get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT password, name, role FROM user_login_credentials WHERE user_id = %s",
            (user_id.strip(),)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and row[0] == password:
            return {"user_id": user_id.strip(), "password": row[0], "name": row[1], "role": row[2]}
    except Exception as e:
        st.error(f"Database error during authentication: {e}")
    return None


def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.chat_history = []
    st.rerun()


def show_login_portal():
    st.title("Bharat ICT Telecom Project Dashboard")
    st.markdown("### Secure Role-Based Login Portal")
    st.info("Sign in with your user ID and password to continue.")

    left_col, _ = st.columns([1.1, 0.9])

    with left_col:
        with st.form("login_form"):
            user_id = st.text_input("User ID")
            password = st.text_input("Password", type="password")
            login_clicked = st.form_submit_button("Login", width='stretch')

        if login_clicked:
            user = authenticate(user_id, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.session_state.chat_history = []
                st.success(f"Welcome {user['name']} • {user['role']}")
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")
                st.stop()
        else:
            st.stop()
