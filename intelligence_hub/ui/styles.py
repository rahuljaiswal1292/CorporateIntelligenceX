
def get_custom_css():
    """  
    Returns the CSS string for the CorporateIntelligenceX dashboard.
    Colors:
    - Primary Navy: #002D62 (Emirates NBD Blue)
    - Gold: #FFB600 (Emirates NBD Gold)
    - Background: #F3F4F6
    """
    return """
    <style>
        /* --- General App Structure --- */
        .stApp {
            background-color: #F8FAFC; /* Slightly cooler/brighter background */
            font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            color: #0F172A; /* Slate 900 - readable black */
            font-size: 16px; /* Increased base size */
        }

        /* --- Sidebar --- */
        section[data-testid="stSidebar"] {
            background-color: #002D62; 
            color: #FFFFFF;
        }
        section[data-testid="stSidebar"] div,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] span {
            color: #F1F5F9 !important; /* Brighter white/gray */
            font-size: 14px;
        }
        section[data-testid="stSidebar"] h1, 
        section[data-testid="stSidebar"] h2, 
        section[data-testid="stSidebar"] h3 {
            color: #FFFFFF !important;
            font-weight: 700;
        }

        /* --- Headers --- */
        h1, h2, h3 {
            color: #1E293B; /* Slate 800 */
            font-weight: 800; /* Bolder */
            letter-spacing: -0.02em;
        }
        h1 { font-size: 2.2rem !important; }
        h2 { font-size: 1.8rem !important; }
        h3 { font-size: 1.4rem !important; }
        
        /* --- Metric Cards --- */
        div[data-testid="stMetric"] {
            background-color: white;
            border: 1px solid #E2E8F0;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transition: transform 0.2s;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        /* --- Captions & Small Headers (Increased Visibility) --- */
        div[data-testid="stCaptionContainer"], .stCaption {
            font-size: 0.95rem !important; /* Larger per user request */
            color: #334155 !important; /* Slate 700 - Darker/Visible */
            font-weight: 800 !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 6px;
        }

        /* --- Search Bar & Inputs --- */
        div[data-testid="stTextInput"] input {
            background-color: #FFFFFF !important;
            color: #0F172A !important; /* Black/Dark Slate */
            caret-color: #0F172A !important; /* Cursor color */
            border: 1px solid #CBD5E1 !important;
        }
        /* Fix hidden 'X' clear button in text input */
        div[data-testid="stTextInput"] button[aria-label="Clear"] {
             color: #0F172A !important; /* Black X */
             fill: #0F172A !important;
        }
        div[data-testid="stTextInput"] {
            color: #0F172A !important;
        }

        /* --- Buttons --- */
        /* Primary Search Button (Navy Background with White Text) */
        div.stButton > button[kind="primary"] {
            background-color: #002D62 !important; 
            color: #FFFFFF !important; /* High Contrast White */
            font-weight: 700 !important;
            border: 2px solid #002D62 !important;
            border-radius: 6px;
            font-size: 1rem !important;
            padding: 0.5rem 1rem !important;
        }
        div.stButton > button[kind="primary"] p {
            color: #FFFFFF !important; /* Force child paragraph (icon/text) to white */
            fill: #FFFFFF !important; /* Force icon fill to white */
        }
        
        /* Other Buttons (Gold/Secondary) */
        div.stButton > button {
            background-color: #FFB600; 
            color: #002D62;
            font-weight: 600;
            border: 1px solid #CC9200;
             border-radius: 6px;
        }
        
        div.stButton > button:hover {
            opacity: 0.9;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        /* --- Alerts (st.info/success/warning) --- */
        div[data-testid="stAlert"] {
            background-color: #EFF6FF !important; /* Light Blue 50 */
            border: 1px solid #BFDBFE !important;
            color: #1E3A8A !important; /* Dark Blue Text */
        }
        div[data-testid="stAlert"] > div {
            color: #172554 !important; /* Deep Navy */
        }
        div[data-testid="stAlert"] p, 
        div[data-testid="stAlert"] li,
        div[data-testid="stAlert"] span,
        div[data-testid="stAlert"] strong {
            color: #172554 !important; /* Deep Navy - Enforce visibility */
            font-size: 1rem !important;
        }

        /* --- Tables (st.table) --- */
        table {
            width: 100%;
            border-collapse: collapse !important;
            border-radius: 8px;
            overflow: hidden;
            font-size: 0.95rem;
            border: 1px solid #E2E8F0;
        }
        thead tr th {
            background-color: #002D62 !important; /* ENBD Navy Header */
            color: #FFFFFF !important;
            font-weight: 800 !important;
            padding: 12px 15px !important;
            text-align: left !important;
            border-bottom: 2px solid #FFB600 !important; /* Gold border below header */
        }
        tbody tr td {
            color: #002D62 !important; /* Navy Text for Rows */
            padding: 10px 15px !important;
            border-bottom: 1px solid #E2E8F0;
            background-color: #FFF9E6 !important; /* Light Gold Background */
            font-weight: 600 !important;
        }
        tbody tr:nth-child(even) td {
            background-color: #FFF0C2 !important; /* Slightly darker Gold for alternating rows */
        }
        
        /* --- Dataframes (st.dataframe) Container --- */
        div[data-testid="stDataFrame"] {
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            overflow: hidden;
        }
        
        /* --- Rail Progress Tracker --- */
        .progress-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 30px 0;
            position: relative;
            padding: 0 10px;
        }
        .progress-track {
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 4px; /* Thinner sophisticated track */
            background-color: #E2E8F0;
            z-index: 0;
            border-radius: 999px;
            transform: translateY(-50%);
        }
        .progress-step {
            position: relative;
            z-index: 1;
            background-color: white;
            border: 2px solid #E2E8F0;
            color: #64748B;
            border-radius: 999px; /* Rounded pill */
            padding: 8px 24px;
            font-size: 0.95rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        }
        .progress-step.active {
            border-color: #FFB600; /* ENBD Gold */
            background-color: #FFF9E6; /* Light Gold BG */
            color: #002D62; /* ENBD Navy Text */
            transform: scale(1.05);
            box-shadow: 0 4px 6px -1px rgba(255, 182, 0, 0.3);
        }
        .progress-step.completed {
            border-color: #002D62; /* ENBD Navy */
            background-color: #002D62; /* Solid Navy */
            color: #FFFFFF; /* White Text - High Contrast */
        }
        .progress-step.completed .progress-step-icon {
            color: #FFB600; /* Gold Icon on Navy */
        }
        .progress-step-icon {
            font-size: 1.2rem;
            line-height: 1;
        }

        /* --- Insight Cards (Strict Brand Colors) --- */
        .insight-card {
            background-color: white;
            border: 1px solid #E2E8F0;
            border-left: 6px solid #002D62; /* Default Navy Accent */
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s;
        }
        .insight-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
        }
        
        .insight-card h4 {
            margin: 0 0 12px 0;
            color: #002D62; /* Navy Header */
            font-size: 1.15rem !important;
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Category Accents - Mapped to Brand Variations */
        /* We use variations of Gold/Navy/Neutral instead of Rainbow */
        .cat-lending { border-left-color: #002D62; } /* Navy */
        .cat-trade { border-left-color: #FFB600; }   /* Gold */
        .cat-ops { border-left-color: #002D62; }    /* Navy */
        .cat-kyc { border-left-color: #94A3B8; }     /* Slate (Neutral) */
        .cat-strategy { border-left-color: #FFB600; }/* Gold */

    </style>
    """
