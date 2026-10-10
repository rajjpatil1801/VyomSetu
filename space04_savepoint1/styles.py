import streamlit as st

def inject_styles():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

        /* Hide Streamlit elements */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display:none;}
        button[title="View fullscreen"] {display: none !important;}
        [data-testid="StyledFullScreenButton"] {display: none !important;}
        
        /* Layout overrides */
        [data-testid="stMainBlockContainer"], .block-container {
            max-width: 100% !important;
            padding: 1.25rem 2.5rem 3rem 2.5rem !important;
        }
        
        [data-testid="stSidebar"] {
            min-width: 300px !important;
            max-width: 300px !important;
            background-color: #FBF9F4;
            border-right: 1px solid #D8D3C5;
        }

        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
            background: transparent;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background-color: #D8D3C5;
            border-radius: 3px;
        }
        
        /* Global typography */
        html, body, [class*="css"] {
            font-family: 'IBM Plex Sans', sans-serif;
            font-size: 16px;
            color: #1C1F22;
        }
        
        /* Monospace elements */
        .kpi-value, .mono-text, table, th, td {
            font-family: 'IBM Plex Mono', monospace !important;
        }
        
        /* Panels and containers */
        .stApp {
            background-color: #F3F0E8;
        }
        
        /* Remove shadows and rounded corners */
        * {
            box-shadow: none !important;
            border-radius: 0px !important;
        }
        
        /* Buttons */
        div[data-testid="stButton"] > button {
            background-color: #C8421B !important;
            color: #F3F0E8 !important;
            border: none !important;
            border-radius: 2px !important;
            font-family: 'IBM Plex Sans', sans-serif;
            font-weight: 500;
            padding: 0.5rem 1rem;
            width: 100%;
        }
        div[data-testid="stButton"] > button:hover {
            opacity: 0.9;
        }
        
        /* KPI styling */
        .kpi-container {
            border-bottom: 1px solid #D8D3C5;
            padding-bottom: 10px;
        }
        .kpi-label {
            font-size: 11px;
            color: #6B6A63;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 2px;
        }
        .kpi-sublabel {
            font-size: 11px;
            color: #6B6A63;
            margin-bottom: 6px;
        }
        .kpi-value {
            font-size: 24px;
            color: #1C1F22;
            line-height: 1.2;
        }
        .kpi-subvalue {
            font-size: 12px;
            color: #6B6A63;
            margin-top: 4px;
        }
        .kpi-accent {
            color: #C8421B;
        }
        
        /* Section labels */
        .section-label {
            font-size: 12px;
            color: #6B6A63;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 24px;
            margin-bottom: 8px;
            border-bottom: 1px solid #D8D3C5;
            padding-bottom: 4px;
        }
        
        /* Caption */
        .caption {
            font-size: 12px;
            color: #6B6A63;
            margin-top: 8px;
            margin-bottom: 24px;
            line-height: 1.4;
        }
        
        /* Tables */
        .stDataFrame {
            border: 1px solid #D8D3C5;
        }
        
        /* Expander */
        .streamlit-expanderHeader {
            background-color: transparent !important;
            border: none !important;
            border-bottom: 1px solid #D8D3C5 !important;
            font-family: 'IBM Plex Sans', sans-serif !important;
            font-size: 14px !important;
            color: #1C1F22 !important;
            padding-left: 0 !important;
        }
        .streamlit-expanderContent {
            border: none !important;
        }

        /* Header Layout */
        .header-container {
            display: flex;
            align-items: center;
            gap: 14px;
            padding-bottom: 12px;
            border-bottom: 1px solid #D8D3C5;
            margin-bottom: 24px;
        }
        .header-title-container {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        .header-title {
            font-size: 34px;
            font-weight: 600;
            color: #1C1F22;
            letter-spacing: -0.01em;
            line-height: 1.1;
        }
        .header-desc {
            font-size: 16px;
            color: #6B6A63;
        }
        .header-scenario {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 13px;
            color: #6B6A63;
            margin-top: 2px;
        }

        /* Priority Legend */
        .priority-legend {
            display: flex;
            gap: 16px;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 11px;
            color: #6B6A63;
            margin-bottom: 4px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .legend-box {
            width: 10px;
            height: 10px;
        }
        .legend-outlined-box {
            width: 10px;
            height: 10px;
            border: 2px solid #C8421B;
            background-color: transparent;
        }

        /* Chart headers */
        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-top: 16px;
            margin-bottom: 4px;
        }
        .chart-header-title {
            font-size: 12px;
            text-transform: uppercase;
            font-weight: 500;
            letter-spacing: 0.05em;
        }
        .chart-header-stats {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 12px;
            color: #6B6A63;
        }

        </style>
    """, unsafe_allow_html=True)

def render_kpi(label: str, sublabel: str, value: str, subvalue: str = "", is_accent: bool = False):
    accent_class = "kpi-accent" if is_accent else ""
    st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-label">{label}</div>
            <div class="kpi-sublabel">{sublabel}</div>
            <div class="kpi-value {accent_class}">{value}</div>
            {f'<div class="kpi-subvalue">{subvalue}</div>' if subvalue else ''}
        </div>
    """, unsafe_allow_html=True)
    
def render_section_label(text: str):
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)

def render_caption(text: str):
    st.markdown(f'<div class="caption">{text}</div>', unsafe_allow_html=True)
