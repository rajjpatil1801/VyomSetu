import streamlit as st
import html_utils

def inject_styles():
    st.markdown(html_utils.compact("""
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
            padding: 0rem 2.5rem 3rem 2.5rem !important;
        }
        
        [data-testid="stSidebar"] {
            min-width: 300px !important;
            max-width: 300px !important;
            background-color: #FBF9F4;
            border-right: 1px solid #D8D3C5;
        }

        html { scroll-behavior: smooth; }

        /* Masthead */
        .masthead {
            margin-left: -2.5rem;
            margin-right: -2.5rem;
            background-color: #1C1F22;
            padding: 28px 40px;
            border-bottom: 3px solid #C8421B;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .masthead-left {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .masthead-text {
            display: flex;
            flex-direction: column;
        }
        .masthead-title {
            font-family: 'IBM Plex Sans', sans-serif;
            font-weight: 600;
            color: #F3F0E8;
            letter-spacing: -0.015em;
            line-height: 1.05;
        }
        .masthead-tagline {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            color: #A7A394;
            margin-top: 4px;
        }
        .masthead-desc {
            font-family: 'IBM Plex Sans', sans-serif;
            font-size: 15px;
            color: #A7A394;
            margin-top: 4px;
        }
        .masthead-right {
            display: flex;
            align-items: center;
        }
        .readout-cell {
            padding: 0 20px;
            border-left: 1px solid #3A3F46;
            display: flex;
            flex-direction: column;
        }
        .readout-cell:first-child {
            border-left: none;
        }
        .readout-label {
            font-family: 'IBM Plex Sans', sans-serif;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #A7A394;
        }
        .readout-value {
            font-family: 'IBM Plex Mono', monospace;
            color: #F3F0E8;
            margin-top: 4px;
        }

        @media (max-width: 1100px) {
            .masthead {
                flex-direction: column;
                align-items: flex-start;
                gap: 24px;
            }
            .masthead-right {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                row-gap: 16px;
                width: 100%;
            }
            .readout-cell {
                padding: 0 16px;
                border-left: 1px solid #3A3F46;
            }
            .readout-cell:nth-child(3n+1) {
                border-left: none;
                padding-left: 0;
            }
        }

        /* Tabs */
        .tab-strip {
            margin-left: -2.5rem;
            margin-right: -2.5rem;
            background-color: #F3F0E8;
            border-bottom: 1px solid #D8D3C5;
            position: sticky;
            top: 0;
            z-index: 999;
            height: 52px;
            display: flex;
            overflow-x: auto;
            scrollbar-width: thin;
        }
        .tab-strip::-webkit-scrollbar { height: 4px; }
        .tab-item {
            display: flex;
            align-items: center;
            padding: 0 18px;
            height: 100%;
            border-right: 1px solid #D8D3C5;
            text-decoration: none;
            cursor: pointer;
            transition: background 0.2s;
            flex-shrink: 0;
            position: relative;
        }
        .tab-item:hover { background-color: #FBF9F4; }
        .tab-item:focus-visible { outline: 2px solid #C8421B; outline-offset: -2px; }
        .tab-index { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #6B6A63; margin-right: 8px; }
        .tab-label { font-family: 'IBM Plex Sans', sans-serif; font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; color: #1C1F22; }
        .tab-item.active { background-color: #FBF9F4; }
        .tab-item.active .tab-label { font-weight: 600; }
        .tab-item.active .tab-index { color: #C8421B; }
        .tab-item.active::after {
            content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 3px; background-color: #C8421B;
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

        /* Segmented Control (View Radio) */
        #view-radio-marker + div[data-testid="stRadio"] div[role="radiogroup"] {
            display: flex;
            flex-direction: row;
            gap: 0;
            border: 1px solid #D8D3C5;
            border-radius: 2px;
            overflow: hidden;
            width: 100%;
        }
        #view-radio-marker + div[data-testid="stRadio"] div[role="radiogroup"] label {
            flex: 1;
            margin: 0;
            padding: 0;
            background-color: #FBF9F4;
            cursor: pointer;
            text-align: center;
            border-right: 1px solid #D8D3C5;
            align-items: center;
            justify-content: center;
        }
        #view-radio-marker + div[data-testid="stRadio"] div[role="radiogroup"] label:last-child {
            border-right: none;
        }
        /* Hide the native radio circle completely */
        #view-radio-marker + div[data-testid="stRadio"] div[role="radiogroup"] label > div:first-of-type {
            display: none !important;
        }
        #view-radio-marker + div[data-testid="stRadio"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] {
            font-family: 'IBM Plex Sans', sans-serif;
            font-size: 13px;
            color: #1C1F22;
            padding: 8px 0;
            margin: 0;
            width: 100%;
        }
        #view-radio-marker + div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
            background-color: #1C1F22;
        }
        #view-radio-marker + div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p {
            color: #FBF9F4;
        }
        /* Keyboard focus */
        #view-radio-marker + div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:focus-visible) {
            outline: 2px solid #C8421B;
            outline-offset: -2px;
        }

        </style>
        """), unsafe_allow_html=True)

def render_kpi(label: str, sublabel: str, value: str, subvalue: str = "", is_accent: bool = False):
    accent_class = "kpi-accent" if is_accent else ""
    st.markdown(html_utils.compact(f"""
        <div class="kpi-container">
            <div class="kpi-label">{label}</div>
            <div class="kpi-sublabel">{sublabel}</div>
            <div class="kpi-value {accent_class}">{value}</div>
            {f'<div class="kpi-subvalue">{subvalue}</div>' if subvalue else ''}
        </div>
    """), unsafe_allow_html=True)
    
def render_section_label(text: str):
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)

def render_caption(text: str):
    st.markdown(f'<div class="caption">{text}</div>', unsafe_allow_html=True)
