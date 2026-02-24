import streamlit as st
import base64
from datetime import datetime


def get_image_base64(path):
    """Encodes a local image to base64 for use in HTML/CSS."""
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()


def format_val(val):
    """Formats numeric values into AED currency strings (B/M/K)."""
    if val is None:
        return "N/A"
    try:
        if isinstance(val, (int, float)):
            if val > 1_000_000_000:
                return f"AED {val/1_000_000_000:.1f}B"
            if val > 1_000_000:
                return f"AED {val/1_000_000:.1f}M"
            return f"AED {val:,.0f}"
        return str(val)
    except:
        return "N/A"


def add_log(agent_name, action):
    """Appends a timestamped log to the session state log history."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] **{agent_name}**: {action}"
    if "logs" not in st.session_state:
        st.session_state.logs = []
    st.session_state.logs.append(log_entry)
