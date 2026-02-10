import os


def get_custom_css():
    """
    Returns the CSS string for the CorporateIntelligenceX dashboard.
    Colors:
    - Primary Navy: #002D62 (Emirates NBD Blue)
    - Gold: #FFB600 (Emirates NBD Gold)
    - Background: #F3F4F6
    """
    css_file_path = os.path.join(os.path.dirname(__file__), "style.css")
    try:
        with open(css_file_path, "r", encoding="utf-8") as f:
            return f"<style>{f.read()}</style>"
    except Exception as e:
        print(f"Error loading CSS: {e}")
        return ""
