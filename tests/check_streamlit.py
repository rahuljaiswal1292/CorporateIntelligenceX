import sys
import subprocess

print(f"Python Executable: {sys.executable}")
print(f"Version: {sys.version}")

try:
    import streamlit
    print(f"Streamlit Version: {streamlit.__version__}")
    print(f"Streamlit Location: {streamlit.__file__}")
except ImportError as e:
    print(f"Streamlit NOT FOUND: {e}")

# Try finding streamlit command
import shutil
cmd = shutil.which("streamlit")
print(f"Streamlit Command Path: {cmd}")
