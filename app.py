import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import re
from dotenv import load_dotenv

from utils.cleaner import load_dataset, clean_dataset, get_trust_label, df_to_excel_bytes
from utils.intelligence import (
    detect_columns, compute_revenue_risk_index,
    get_revenue_summary, get_revenue_by_column,
    get_monthly_revenue, get_return_rate_by_column,
    get_discount_impact, get_proactive_alerts,
    get_top_risk_orders, get_intervention_recommendation,
    get_risk_tier_summary,
)
from utils.analyst import ask_analyst, generate_executive_brief
from utils.report import generate_pdf_report
from utils.vitality import (
    compute_retail_vitality_index, get_vitality_tier_summary,
    get_champion_customers, get_dormant_customers,
    get_avg_rvi_by_segment, get_vitality_intervention,
)
from utils.scheduler import (
    start_email_scheduler, send_intelligence_email,
    detect_anomalies, get_email_config,
)
from sklearn.linear_model import LinearRegression

load_dotenv()

st.set_page_config(
    page_title="NEXUS Retail | Revenue Intelligence",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

_defaults = {
    "df_clean": None, "df_with_risk": None, "col_map": None,
    "trust_report": None, "chat_history": [], "analytics_summary": "",
    "executive_brief": None, "executive_brief_date": None, "cust_df": None,
    "kpi_summary": {}, "alerts": [], "scheduler_started": False,
    "email_result": None, "prev_kpis": {},
    "mistral_api_key": os.getenv("MISTRAL_API_KEY", ""),
    "theme": "dark",
    "email_sender":     os.getenv("EMAIL_SENDER", ""),
    "email_password":   os.getenv("EMAIL_PASSWORD", ""),
    "email_recipients": os.getenv("EMAIL_RECIPIENTS", ""),
    "analyst_input":    "",
    "pdf_bytes":        None,
    "pdf_filename":     "",
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

DARK = {
    "bg": "#0F172A", "surface": "#1E1B4B", "surface2": "#2D2A5E",
    "border": "#3730A3", "text": "#F1F5F9", "text2": "#A78BFA",
    "primary": "#7C3AED", "primary_soft": "#A78BFA", "teal": "#0F766E",
    "danger": "#F43F5E", "warning": "#F59E0B", "success": "#10B981",
    "sidebar": "#1E1B4B", "cb": "#0F172A", "ct": "#A78BFA",
    "cg": "#2D2A5E", "cl": "#3730A3",
}
LIGHT = {
    "bg": "#F1F5F9", "surface": "#FFFFFF", "surface2": "#EDE9FE",
    "border": "#DDD6FE", "text": "#0F172A", "text2": "#334155",
    "primary": "#7C3AED", "primary_soft": "#7C3AED", "teal": "#0F766E",
    "danger": "#E11D48", "warning": "#D97706", "success": "#059669",
    "sidebar": "#1E1B4B", "cb": "#FFFFFF", "ct": "#334155",
    "cg": "#E2E8F0", "cl": "#CBD5E1",
}
T = LIGHT if st.session_state.theme == "light" else DARK

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
html, body, [class*="css"], .stApp {{
    font-family: 'Inter', sans-serif !important;
    background-color: {T['bg']} !important;
    color: {T['text']} !important;
}}
.block-container {{ padding: 1.8rem 2.5rem 3rem !important; max-width: 1400px; }}
section[data-testid="stSidebar"] {{
    background: {T['sidebar']} !important;
    border-right: 1px solid #3730A3 !important;
}}
section[data-testid="stSidebar"] * {{ color: #F1F5F9 !important; }}
section[data-testid="stSidebar"] .stButton > button {{
    background: #7C3AED !important; color: #fff !important;
    border: none !important; border-radius: 8px !important; font-weight: 600 !important;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{ background: #6D28D9 !important; }}
section[data-testid="stSidebar"] .stRadio label {{
    background: rgba(124,58,237,0.10) !important;
    border: 1px solid rgba(124,58,237,0.3) !important;
    border-radius: 8px !important; padding: 8px 12px !important;
    font-size: 0.85rem !important; color: #A78BFA !important; transition: all 0.15s;
}}
section[data-testid="stSidebar"] .stRadio label:hover {{
    background: rgba(124,58,237,0.28) !important; color: #fff !important;
}}
section[data-testid="stSidebar"] hr {{ border-color: #3730A3 !important; opacity: 0.4; }}
section[data-testid="stSidebar"] .stTextInput input {{
    background: rgba(15,23,42,0.7) !important;
    border: 1px solid #3730A3 !important; color: #F1F5F9 !important; border-radius: 8px !important;
}}
section[data-testid="stSidebar"] .stExpander {{
    background: rgba(124,58,237,0.08) !important;
    border: 1px solid rgba(124,58,237,0.3) !important; border-radius: 10px !important;
}}
section[data-testid="stSidebar"] .stMultiSelect > div > div {{
    background: rgba(15,23,42,0.7) !important;
    border: 1px solid #3730A3 !important; border-radius: 8px !important;
}}
section[data-testid="stSidebar"] .stMultiSelect span[data-baseweb="tag"] {{
    background: #7C3AED !important; color: #fff !important; border-radius: 6px !important;
}}
section[data-testid="stSidebar"] .stMultiSelect span[data-baseweb="tag"] span {{ color: #fff !important; }}
section[data-testid="stSidebar"] .stMultiSelect svg {{ fill: #F1F5F9 !important; }}
section[data-testid="stSidebar"] [data-baseweb="popover"] {{ background: #1E1B4B !important; }}
section[data-testid="stSidebar"] [data-baseweb="popover"] li {{ color: #F1F5F9 !important; background: #1E1B4B !important; }}
section[data-testid="stSidebar"] [data-baseweb="popover"] li:hover {{ background: rgba(124,58,237,0.3) !important; }}
section[data-testid="stSidebar"] .stSelectbox > div > div {{
    background: rgba(15,23,42,0.7) !important;
    border: 1px solid #3730A3 !important; color: #F1F5F9 !important; border-radius: 8px !important;
}}
section[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] > div > div {{ background: #3730A3 !important; }}
section[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] > div > div > div {{ background: #7C3AED !important; }}
section[data-testid="stSidebar"] .stSlider [role="slider"] {{ background: #A78BFA !important; border: 2px solid #7C3AED !important; }}
section[data-testid="stSidebar"] .stSlider [data-testid="stTickBar"] div {{ color: #A78BFA !important; }}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] {{
    background: rgba(15,23,42,0.5) !important;
    border: 1px dashed #3730A3 !important; border-radius: 10px !important; padding: 8px !important;
}}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] section {{ background: transparent !important; }}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
    background: rgba(124,58,237,0.06) !important;
    border: 1px dashed rgba(124,58,237,0.4) !important; border-radius: 8px !important;
}}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {{ color: #A78BFA !important; }}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {{
    background: #7C3AED !important; color: #fff !important; border: none !important;
}}
section[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {{
    background: rgba(124,58,237,0.12) !important;
    border: 1px solid rgba(124,58,237,0.3) !important;
    border-radius: 8px !important; color: #F1F5F9 !important;
}}
section[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] * {{ color: #F1F5F9 !important; }}
.eyebrow {{ font-size: 0.66rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: {T['primary_soft']}; margin-bottom: 4px; }}
.page-title {{ font-family: 'Space Grotesk', sans-serif; font-size: 2rem; font-weight: 700; color: {T['text']} !important; letter-spacing: -0.5px; margin-bottom: 4px; }}
.page-sub {{ font-size: 0.86rem; color: {T['text2']}; margin-bottom: 1.4rem; }}
.kpi-card {{ background: {T['surface']}; border: 1px solid {T['border']}; border-radius: 14px; padding: 18px 16px 14px; position: relative; overflow: hidden; transition: transform 0.15s, box-shadow 0.15s; min-height: 130px; }}
.kpi-card::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, {T['primary']}, {T['primary_soft']}); }}
.kpi-card.t-teal::before   {{ background: linear-gradient(90deg,#0F766E,#14B8A6); }}
.kpi-card.t-danger::before {{ background: linear-gradient(90deg,#BE123C,#F43F5E); }}
.kpi-card.t-warn::before   {{ background: linear-gradient(90deg,#B45309,#F59E0B); }}
.kpi-card.t-ok::before     {{ background: linear-gradient(90deg,#047857,#10B981); }}
.kpi-label {{ font-size: 0.67rem; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; color: {T['text2']}; margin-bottom: 8px; }}
.kpi-value {{ font-family: 'Space Grotesk', sans-serif; font-size: 1.55rem; font-weight: 700; color: {T['text']} !important; line-height: 1.1; letter-spacing: -0.5px; }}
.kpi-unit {{ font-size: 0.9rem; color: {T['text2']}; font-weight: 500; }}
.kpi-sub  {{ font-size: 0.7rem; color: {T['text2']}; margin-top: 5px; }}
.kpi-badge {{ display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 0.62rem; font-weight: 700; margin-top: 7px; }}
.b-purple {{ background:rgba(124,58,237,0.15); color:#A78BFA; }}
.b-ok     {{ background:rgba(16,185,129,0.15);  color:#10B981; }}
.b-warn   {{ background:rgba(245,158,11,0.15);  color:#F59E0B; }}
.b-danger {{ background:rgba(244,63,94,0.15);   color:#F43F5E; }}
.b-teal   {{ background:rgba(15,118,110,0.15);  color:#14B8A6; }}
.alert-wrap {{ background: {T['surface']}; border: 1px solid {T['border']}; border-radius: 12px; padding: 14px 16px; margin: 8px 0; display: flex; gap: 14px; align-items: flex-start; }}
.alert-wrap.crit {{ border-left: 4px solid #F43F5E; }}
.alert-wrap.warn {{ border-left: 4px solid #F59E0B; }}
.alert-wrap.info {{ border-left: 4px solid #7C3AED; }}
.alert-icon  {{ font-size: 1.4rem; line-height: 1; flex-shrink: 0; }}
.alert-title {{ font-weight: 600; font-size: 0.875rem; color: {T['text']}; }}
.alert-msg   {{ font-size: 0.8rem; color: {T['text2']}; margin-top: 3px; line-height: 1.5; }}
.divider {{ border: none; border-top: 1px solid {T['border']}; margin: 1.8rem 0; opacity: 0.5; }}
.section-label {{ font-size: 0.63rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: {T['primary_soft']}; margin-bottom: 0.75rem; }}
.insight-tile {{ background: {T['surface']}; border: 1px solid {T['border']}; border-radius: 12px; padding: 16px 12px; text-align: center; min-height: 110px; }}
.insight-val {{ font-family:'Space Grotesk',sans-serif; font-size:1.2rem; font-weight:700; }}
.insight-lbl {{ font-size:0.66rem; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; color:{T['text2']}; margin-top:5px; }}
.insight-sub {{ font-size:0.67rem; color:{T['primary_soft']}; margin-top:3px; }}
.feature-card {{ background: {T['surface']}; border: 1px solid {T['border']}; border-radius: 14px; padding: 22px 18px; transition: border-color 0.2s, box-shadow 0.2s; }}
.feature-card:hover {{ border-color:#7C3AED; box-shadow:0 8px 28px rgba(124,58,237,0.2); }}
.chat-user {{ background:rgba(124,58,237,0.10); border:1px solid rgba(124,58,237,0.22); padding:12px 16px; border-radius:12px 12px 4px 12px; margin:8px 0; font-size:0.875rem; color:{T['text']}; }}
.chat-ai {{ background:rgba(15,118,110,0.09); border:1px solid rgba(15,118,110,0.22); padding:12px 16px; border-radius:12px 12px 12px 4px; margin:8px 0; font-size:0.875rem; color:{T['text']}; line-height:1.65; }}
.report-card {{ background:{T['surface']}; border:1px solid {T['border']}; border-radius:14px; padding:24px 28px; margin-bottom:16px; }}
h1,h2,h3,h4,h5,h6 {{ color:{T['text']} !important; }}
.stMarkdown p {{ color:{T['text2']}; }}
.stDataFrame {{ border-radius:10px; overflow:hidden; }}
.stSelectbox label,.stTextInput label {{ color:{T['text2']} !important; font-size:0.82rem; }}
.stSelectbox > div > div {{ background:{T['surface']} !important; border-color:{T['border']} !important; color:{T['text']} !important; border-radius:8px; }}
.stTextInput input,.stTextArea textarea {{ background:{T['surface']} !important; border-color:{T['border']} !important; color:{T['text']} !important; border-radius:8px; }}
.stExpander {{ background:{T['surface']} !important; border:1px solid {T['border']} !important; border-radius:10px !important; }}
.stExpander summary {{ color:{T['text']} !important; }}
.stButton > button, .stDownloadButton > button {{ background:{T['surface2']}; color:{T['text']}; border:1px solid {T['border']}; border-radius:8px; font-weight:500; transition:all 0.15s; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ background:{T['primary']}; color:#fff; border-color:{T['primary']}; }}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{ background:linear-gradient(135deg,#7C3AED,#6D28D9) !important; color:#fff !important; border:none !important; font-weight:600 !important; }}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {{ background:linear-gradient(135deg,#6D28D9,#5B21B6) !important; }}
.stSuccess {{ background:rgba(16,185,129,0.12) !important; border-color:#10B981 !important; }}
.stWarning {{ background:rgba(245,158,11,0.12)  !important; border-color:#F59E0B !important; }}
.stError   {{ background:rgba(244,63,94,0.12)   !important; border-color:#F43F5E !important; }}
.stInfo    {{ background:rgba(124,58,237,0.10)  !important; border-color:#7C3AED !important; }}
.stCaption {{ color:{T['text2']} !important; }}
#MainMenu, footer, header {{ visibility:hidden; }}
</style>
""", unsafe_allow_html=True)

# ── SCHEDULER ─────────────────────────────────────────────────────────────────
if not st.session_state.scheduler_started:
    def _state():
        return {
            "df": st.session_state.get("df_with_risk"),
            "col_map": st.session_state.get("col_map"),
            "kpi_summary": st.session_state.get("kpi_summary", {}),
            "alerts": st.session_state.get("alerts", []),
            "ai_brief": st.session_state.get("executive_brief", "") or "",
        }
    start_email_scheduler(_state)
    st.session_state.scheduler_started = True

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:4px 0 16px;">
        <div style="font-family:'Space Grotesk',sans-serif;font-size:1.25rem;font-weight:700;color:#F1F5F9;letter-spacing:-0.3px;">🛒 NEXUS Retail</div>
        <div style="font-size:0.66rem;color:#A78BFA;letter-spacing:1.8px;text-transform:uppercase;margin-top:3px;">Revenue Intelligence OS</div>
        <div style="display:inline-block;background:rgba(124,58,237,0.2);border:1px solid rgba(124,58,237,0.4);color:#A78BFA;font-size:0.63rem;padding:2px 9px;border-radius:20px;font-weight:700;margin-top:8px;">v2.0 · AI-Powered</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:0.63rem;letter-spacing:1.8px;text-transform:uppercase;color:#A78BFA;margin-bottom:5px;">Appearance</div>', unsafe_allow_html=True)
    theme_choice = st.radio("Theme", ["🌑 Dark", "☀️ Light", "💻 System"],
        index=0 if st.session_state.theme == "dark" else 1,
        horizontal=True, label_visibility="collapsed")
    new_theme = "light" if "Light" in theme_choice else "dark"
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

    st.markdown("---")

    with st.expander("🔑 API Key", expanded=not bool(st.session_state.mistral_api_key)):
        api_key_input = st.text_input("Mistral API Key", value=st.session_state.mistral_api_key,
            type="password", placeholder="sk-...", label_visibility="collapsed")
        if api_key_input != st.session_state.mistral_api_key:
            st.session_state.mistral_api_key = api_key_input
            os.environ["MISTRAL_API_KEY"] = api_key_input
        if st.session_state.mistral_api_key:
            st.success("API key active", icon="🔐")
        else:
            st.caption("Free key → [console.mistral.ai](https://console.mistral.ai)")

    st.markdown("---")

    st.markdown('<div style="font-size:0.63rem;letter-spacing:1.8px;text-transform:uppercase;color:#A78BFA;margin-bottom:6px;">Dataset</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload", type=["csv","xlsx","xls"],
        label_visibility="collapsed", help="Any retail CSV or Excel — NEXUS auto-detects all columns.")
    if uploaded_file:
        st.markdown(f'<div style="font-size:0.74rem;color:#A78BFA;margin:-4px 0 8px;">📄 {uploaded_file.name}</div>', unsafe_allow_html=True)
        if st.button("🚀 Run Full Analysis", type="primary", use_container_width=True):
            with st.spinner("Analysing…"):
                try:
                    raw_df  = load_dataset(uploaded_file)
                    clean_df, trust_report = clean_dataset(raw_df)
                    col_map = detect_columns(clean_df)
                    df_risk = compute_revenue_risk_index(clean_df, col_map)
                    st.session_state.df_clean     = clean_df
                    st.session_state.df_with_risk = df_risk
                    st.session_state.col_map      = col_map
                    st.session_state.trust_report = trust_report
                    st.session_state.chat_history = []
                    st.session_state.analyst_input = ""
                    cust_df = compute_retail_vitality_index(df_risk, col_map)
                    st.session_state.cust_df = cust_df
                    summary_obj = get_revenue_summary(df_risk, col_map)
                    alerts_obj  = get_proactive_alerts(df_risk, col_map)
                    if cust_df is not None and "RVI_Score" in cust_df.columns:
                        summary_obj["avg_rvi"] = round(cust_df["RVI_Score"].mean(), 1)
                    st.session_state.kpi_summary = summary_obj
                    st.session_state.alerts      = alerts_obj
                    anomalies = detect_anomalies(df_risk, col_map, st.session_state.get("prev_kpis", {}))
                    if anomalies and st.session_state.mistral_api_key:
                        brief   = st.session_state.get("executive_brief") or ""
                        excerpt = (brief[:300]+"...") if len(brief)>300 else brief
                        send_intelligence_email(kpi_summary=summary_obj, alerts=alerts_obj,
                            ai_brief_excerpt=excerpt or "Anomaly detected.",
                            recommended_action=anomalies[0], is_anomaly=True)
                    st.session_state.prev_kpis = summary_obj
                    parts = []
                    if summary_obj.get("total_net_revenue"):
                        parts.append(f"Net revenue: ₦{summary_obj['total_net_revenue']:,.0f}")
                    if summary_obj.get("profit_margin_pct"):
                        parts.append(f"Margin: {summary_obj['profit_margin_pct']}%")
                    if summary_obj.get("return_rate_pct"):
                        parts.append(f"Return rate: {summary_obj['return_rate_pct']}%")
                    st.session_state.analytics_summary = " | ".join(parts)
                    st.success("Analysis complete!")
                except Exception as e:
                    st.error(str(e))

    st.markdown("---")
    if st.session_state.df_with_risk is not None:
        st.markdown('<div style="font-size:0.63rem;letter-spacing:1.8px;text-transform:uppercase;color:#A78BFA;margin-bottom:6px;">Navigation</div>', unsafe_allow_html=True)
        page = st.radio("nav", [
            "🏠 Command Center", "🧬 Customer Vitality", "🔬 Deep Analysis",
            "💬 Ask NEXUS Retail", "📋 Executive Brief",
            "📧 Email Intelligence", "📥 Export Report",
        ], label_visibility="collapsed")
    else:
        page = "🏠 Command Center"

    if st.session_state.df_with_risk is not None:
        st.markdown("---")
        _cmap = st.session_state.col_map or {}
        _fdf  = st.session_state.df_with_risk
        with st.expander("🧮 Filters & Slicers", expanded=False):
            _date_col = _cmap.get("order_date")
            if _date_col and _date_col in _fdf.columns:
                _dates = pd.to_datetime(_fdf[_date_col], errors="coerce").dropna()
                if len(_dates) > 0:
                    _min_d, _max_d = _dates.min().date(), _dates.max().date()
                    if _min_d < _max_d:
                        st.markdown('<div style="font-size:0.68rem;letter-spacing:1.2px;text-transform:uppercase;color:#A78BFA;margin-bottom:4px;">📅 Date Range</div>', unsafe_allow_html=True)
                        st.session_state["flt_date_range"] = st.slider(
                            "Date range", min_value=_min_d, max_value=_max_d,
                            value=st.session_state.get("flt_date_range", (_min_d, _max_d)),
                            label_visibility="collapsed", key="flt_date_slider")
                    else:
                        st.session_state["flt_date_range"] = (_min_d, _max_d)
            for _key, _label in [("channel","🛍️ Sales Channel"),("customer_segment","👥 Customer Segment"),("region","🌍 Region"),("product_category","📦 Product Category")]:
                _col = _cmap.get(_key)
                if _col and _col in _fdf.columns:
                    _opts = sorted(_fdf[_col].dropna().astype(str).unique().tolist())
                    if 1 < len(_opts) <= 60:
                        st.markdown(f'<div style="font-size:0.68rem;letter-spacing:1.2px;text-transform:uppercase;color:#A78BFA;margin:8px 0 4px;">{_label}</div>', unsafe_allow_html=True)
                        st.session_state[f"flt_{_key}"] = st.multiselect(_label, _opts,
                            default=st.session_state.get(f"flt_{_key}", []),
                            label_visibility="collapsed", key=f"flt_ms_{_key}", placeholder="All")
            if "Risk_Tier" in _fdf.columns:
                _risk_opts = [r for r in ["High Value","Stable","At Risk","Profit Drain"] if r in _fdf["Risk_Tier"].astype(str).unique()]
                if _risk_opts:
                    st.markdown('<div style="font-size:0.68rem;letter-spacing:1.2px;text-transform:uppercase;color:#A78BFA;margin:8px 0 4px;">🎯 Risk Tier</div>', unsafe_allow_html=True)
                    st.session_state["flt_risk_tier"] = st.multiselect("Risk Tier", _risk_opts,
                        default=st.session_state.get("flt_risk_tier", []),
                        label_visibility="collapsed", key="flt_ms_risk_tier", placeholder="All")
            if st.button("↺ Reset Filters", use_container_width=True, key="flt_reset"):
                for _k in list(st.session_state.keys()):
                    if _k.startswith("flt_"):
                        del st.session_state[_k]
                st.rerun()

    st.markdown("---")
    st.markdown('<div style="font-size:0.68rem;color:#475569;line-height:1.75;">NEXUS Retail v2.0<br>Powered by Mistral AI<br>RRI · RVI · Email Intelligence</div>', unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────────────
def page_header(eyebrow_txt, title_txt, sub_txt):
    st.markdown(f'<div class="eyebrow">{eyebrow_txt}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-title">{title_txt}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">{sub_txt}</div>', unsafe_allow_html=True)

def divider():
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

def section_lbl(txt):
    st.markdown(f'<div class="section-label">{txt}</div>', unsafe_allow_html=True)

def kpi_card(accent, label, value, sub, badge_cls, badge_txt):
    st.markdown(f"""<div class="kpi-card {accent}"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div><span class="kpi-badge {badge_cls}">{badge_txt}</span></div>""", unsafe_allow_html=True)

def insight_tile(value, label, sub, color):
    st.markdown(f"""<div class="insight-tile"><div class="insight-val" style="color:{color};">{value}</div><div class="insight-lbl">{label}</div><div class="insight-sub">{sub}</div></div>""", unsafe_allow_html=True)

def alert_card(icon, title, msg, lvl):
    cls = "crit" if lvl=="critical" else "warn" if lvl=="warning" else "info"
    st.markdown(f"""<div class="alert-wrap {cls}"><div class="alert-icon">{icon}</div><div><div class="alert-title">{title}</div><div class="alert-msg">{msg}</div></div></div>""", unsafe_allow_html=True)

def chart_layout():
    return dict(plot_bgcolor=T["cb"], paper_bgcolor=T["cb"],
        font=dict(family="Inter", color=T["ct"]),
        title_font=dict(family="Space Grotesk", color=T["text"], size=14),
        margin=dict(t=50, b=28, l=10, r=10), legend=dict(font_color=T["ct"]))

def sf(fig, height=360):
    fig.update_layout(height=height, **chart_layout())
    fig.update_xaxes(showgrid=False, linecolor=T["cl"], tickfont_color=T["ct"])
    fig.update_yaxes(gridcolor=T["cg"], linecolor=T["cl"], tickfont_color=T["ct"])
    return fig

def fmt_ngn(v):
    if v is None: return "—"
    if v >= 1_000_000: return f"₦{v/1_000_000:.1f}M"
    if v >= 1_000:     return f"₦{v/1_000:.0f}K"
    return f"₦{v:,.0f}"

def fmt_pct(v, d=1):
    return f"{v:.{d}f}%" if v is not None else "—"

PS = [[0,"#3730A3"],[0.5,"#7C3AED"],[1,"#A78BFA"]]
TS = [[0,"#134E4A"],[0.5,"#0F766E"],[1,"#14B8A6"]]
RS = [[0,"#F43F5E"],[0.5,"#F59E0B"],[1,"#10B981"]]

# ── LANDING ───────────────────────────────────────────────────────────────────
if st.session_state.df_with_risk is None:
    st.markdown(f"""
<div style="padding:2.5rem 0 1.5rem;">
    <div style="font-size:0.66rem;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#A78BFA;margin-bottom:10px;">Revenue Intelligence Platform · Nigerian Retail</div>
    <div style="font-family:'Space Grotesk',sans-serif;font-size:2.9rem;font-weight:700;color:{T['text']};letter-spacing:-1.5px;line-height:1.05;">
        Turn retail data into<br>
        <span style="background:linear-gradient(135deg,#7C3AED,#A78BFA);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">revenue clarity</span>
    </div>
    <div style="font-size:0.98rem;color:{T['text2']};margin-top:14px;max-width:520px;line-height:1.65;">
        Upload any retail dataset. NEXUS Retail cleans it, scores every order for risk, scores every customer for health, and pinpoints where money is leaking — in seconds.
    </div>
</div>""", unsafe_allow_html=True)
    st.markdown(f"""
<div style="display:flex;gap:40px;padding:20px 0;flex-wrap:wrap;border-top:1px solid {T['border']};border-bottom:1px solid {T['border']};margin-bottom:2.5rem;">
    <div><div style="font-family:'Space Grotesk',sans-serif;font-size:1.55rem;font-weight:700;color:{T['text']};">₦68.5M</div><div style="font-size:0.72rem;color:{T['text2']};margin-top:2px;">Net revenue analysed</div></div>
    <div><div style="font-family:'Space Grotesk',sans-serif;font-size:1.55rem;font-weight:700;color:{T['text']};">1,506</div><div style="font-size:0.72rem;color:{T['text2']};margin-top:2px;">Orders processed</div></div>
    <div><div style="font-family:'Space Grotesk',sans-serif;font-size:1.55rem;font-weight:700;color:#F43F5E;">174</div><div style="font-size:0.72rem;color:{T['text2']};margin-top:2px;">Loss-making orders</div></div>
    <div><div style="font-family:'Space Grotesk',sans-serif;font-size:1.55rem;font-weight:700;color:#A78BFA;">339</div><div style="font-size:0.72rem;color:{T['text2']};margin-top:2px;">Customers scored</div></div>
    <div><div style="font-family:'Space Grotesk',sans-serif;font-size:1.55rem;font-weight:700;color:{T['teal']};">2</div><div style="font-size:0.72rem;color:{T['text2']};margin-top:2px;">Derived metrics</div></div>
</div>""", unsafe_allow_html=True)
    features = [
        ("🔍","AI Data Cleaning","Fixes duplicates, label inconsistencies, missing values. Returns a Data Trust Score.","purple"),
        ("🎯","Revenue Risk Index","Every order scored 0–100 across 5 signals. Segments: High Value → Profit Drain.","purple"),
        ("🧬","Customer Vitality","Every customer scored 0–100 for health. Segments: Champion → Dormant.","teal"),
        ("🔮","Predictive Insights","Revenue forecast, churn risk, repeat share — computed automatically on upload.","purple"),
        ("💬","AI Analyst","Ask revenue questions in plain English. Mistral AI answers from your live data.","teal"),
        ("📧","Email Intelligence","Monday 8AM HTML briefings + instant anomaly alerts when thresholds breach.","purple"),
    ]
    cols = st.columns(3)
    for i, (icon, title, desc, accent) in enumerate(features):
        with cols[i % 3]:
            st.markdown(f"""<div class="feature-card" style="margin-bottom:12px;"><div style="font-size:1.8rem;margin-bottom:10px;">{icon}</div><div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:0.9rem;color:{T['text']};margin-bottom:6px;">{title}</div><div style="font-size:0.8rem;color:{T['text2']};line-height:1.55;">{desc}</div></div>""", unsafe_allow_html=True)
    st.markdown(f"""
<div style="background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.28);border-radius:12px;padding:18px 22px;margin-top:12px;">
    <div style="font-weight:700;font-size:0.86rem;color:#A78BFA;margin-bottom:8px;">Get started in 3 steps</div>
    <div style="font-size:0.82rem;color:{T['text2']};line-height:1.85;">
        1 · Add your Mistral API key in the sidebar — free at <a href="https://console.mistral.ai" target="_blank" style="color:#7C3AED;">console.mistral.ai</a><br>
        2 · Upload your retail dataset (CSV or Excel — any column names work)<br>
        3 · Click <strong style="color:{T['text']};">Run Full Analysis</strong>
    </div>
</div>""", unsafe_allow_html=True)
    st.stop()

# ── SHARED ────────────────────────────────────────────────────────────────────
df           = st.session_state.df_with_risk
col_map      = st.session_state.col_map
trust_report = st.session_state.trust_report

_active_filters = []
_df_filtered = df.copy()
_date_col = col_map.get("order_date")
_dr = st.session_state.get("flt_date_range")
if _date_col and _date_col in _df_filtered.columns and _dr:
    _dser = pd.to_datetime(_df_filtered[_date_col], errors="coerce")
    _start, _end = pd.Timestamp(_dr[0]), pd.Timestamp(_dr[1])
    _full_min, _full_max = _dser.min(), _dser.max()
    if not (pd.isna(_full_min) or (_start <= _full_min and _end >= _full_max)):
        _df_filtered = _df_filtered[(_dser >= _start) & (_dser <= _end)]
        _active_filters.append(f"📅 {_dr[0]:%b %d, %Y} – {_dr[1]:%b %d, %Y}")
for _key, _icon in [("channel","🛍️"),("customer_segment","👥"),("region","🌍"),("product_category","📦")]:
    _col = col_map.get(_key)
    _sel = st.session_state.get(f"flt_{_key}")
    if _col and _col in _df_filtered.columns and _sel:
        _df_filtered = _df_filtered[_df_filtered[_col].astype(str).isin(_sel)]
        _active_filters.append(f"{_icon} {', '.join(_sel) if len(_sel)<=3 else f'{len(_sel)} selected'}")
_risk_sel = st.session_state.get("flt_risk_tier")
if "Risk_Tier" in _df_filtered.columns and _risk_sel:
    _df_filtered = _df_filtered[_df_filtered["Risk_Tier"].astype(str).isin(_risk_sel)]
    _active_filters.append(f"🎯 {', '.join(_risk_sel)}")
df = _df_filtered
_cust_df_full = st.session_state.get("cust_df")
_cust_id_col  = col_map.get("customer_id")
if _cust_df_full is not None and _cust_id_col and _cust_id_col in df.columns and _cust_id_col in _cust_df_full.columns:
    _surviving_ids = set(df[_cust_id_col].astype(str).unique())
    cust_df_view = _cust_df_full[_cust_df_full[_cust_id_col].astype(str).isin(_surviving_ids)]
else:
    cust_df_view = _cust_df_full
st.session_state["_cust_df_view"] = cust_df_view
if _active_filters:
    _chips = "".join(f'<span style="display:inline-block;background:rgba(124,58,237,0.15);border:1px solid rgba(124,58,237,0.35);color:{T["primary_soft"]};font-size:0.72rem;font-weight:600;padding:3px 10px;border-radius:20px;margin:0 6px 6px 0;">{c}</span>' for c in _active_filters)
    st.markdown(f'<div style="margin-bottom:14px;"><span style="font-size:0.66rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:{T["text2"]};margin-right:8px;">🧮 Active Filters</span>{_chips}<span style="font-size:0.72rem;color:{T["text2"]};margin-left:4px;">· {len(df):,} of {len(st.session_state.df_with_risk):,} rows</span></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# PAGE 1 — COMMAND CENTER
# ════════════════════════════════════════════════════════════════════════════
if page == "🏠 Command Center":
    page_header("Revenue Intelligence", "Command Center",
        "Live overview — alerts and predictive signals fire automatically on upload.")
    summary      = get_revenue_summary(df, col_map)
    trust_score  = trust_report.get("trust_score", 0) if trust_report else 0
    trust_lbl, _ = get_trust_label(trust_score) if isinstance(trust_score,(int,float)) else ("N/A","")
    avg_rri      = round(df["RRI_Score"].mean(),1) if "RRI_Score" in df.columns else 0
    net_rev    = summary.get("total_net_revenue")
    gross_rev  = summary.get("total_gross_revenue")
    profit     = summary.get("total_profit")
    margin     = summary.get("profit_margin_pct")
    ret_rate   = summary.get("return_rate_pct")
    tot_orders = summary.get("total_orders", len(df))
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    with k1: kpi_card("","Total Orders",f"{tot_orders:,}","Dataset records","b-purple","FY 2025")
    with k2: kpi_card("","Net Revenue",fmt_ngn(net_rev),"After returns & discounts","b-purple",f"Gross {fmt_ngn(gross_rev)}")
    with k3:
        m_acc = "t-ok" if (margin or 0)>15 else "t-warn"
        kpi_card(m_acc,"Profit Margin",fmt_pct(margin),f"Total profit {fmt_ngn(profit)}","b-ok" if (margin or 0)>15 else "b-warn","✓ Above 20%" if (margin or 0)>15 else "⚠ Below 20%")
    with k4:
        r_acc = "t-danger" if (ret_rate or 0)>5 else "t-ok"
        kpi_card(r_acc,"Return Rate",fmt_pct(ret_rate),"Industry benchmark 7.4%","b-danger" if (ret_rate or 0)>5 else "b-ok","⚠ Above 5%" if (ret_rate or 0)>5 else "✓ Healthy")
    with k5: kpi_card("t-warn" if avg_rri>30 else "t-ok","Avg Risk Score",f'{avg_rri}<span class="kpi-unit">/100</span>',"Revenue Risk Index","b-warn" if avg_rri>30 else "b-ok","Elevated" if avg_rri>30 else "Normal")
    with k6: kpi_card("t-ok" if trust_score>=75 else "t-warn","Data Trust Score",f'{trust_score}<span class="kpi-unit">/100</span>',"Cleaning quality","b-ok" if trust_score>=75 else "b-warn",trust_lbl)
    divider()
    alerts = get_proactive_alerts(df, col_map)
    if alerts:
        section_lbl("INTELLIGENCE ALERTS — AUTO-GENERATED")
        for a in alerts:
            alert_card(a["icon"], a["title"], a["message"], a["level"])
    divider()
    section_lbl("PREDICTIVE INTELLIGENCE — 5 SIGNALS")
    p1,p2,p3,p4,p5 = st.columns(5)
    monthly = get_monthly_revenue(df, col_map)
    with p1:
        if monthly is not None and len(monthly)>=3:
            try:
                X = np.arange(len(monthly)).reshape(-1,1)
                y = monthly["Net Revenue"].values
                m = LinearRegression().fit(X,y)
                nxt = m.predict([[len(monthly)]])[0]
                insight_tile(fmt_ngn(max(nxt,0)),"Revenue Forecast",f"{'📈' if m.coef_[0]>0 else '📉'} projected next month",T["primary_soft"])
            except: insight_tile("—","Revenue Forecast","Insufficient data",T["text2"])
        else: insight_tile("—","Revenue Forecast","Need ≥3 months",T["text2"])
    cust_live = st.session_state.get("_cust_df_view")
    with p2:
        if cust_live is not None and "Vitality_Tier" in cust_live.columns:
            total_c = len(cust_live); dorm_n = (cust_live["Vitality_Tier"]=="Dormant").sum()
            churn_pct = round(dorm_n/total_c*100,1)
            insight_tile(f"{dorm_n}","Churn Risk",f"⚠ {churn_pct}% dormant",T["danger"] if churn_pct>20 else T["warning"])
        else: insight_tile("—","Churn Risk","RVI not computed",T["text2"])
    with p3:
        if cust_live is not None and "Vitality_Tier" in cust_live.columns:
            total_c = len(cust_live); champ_n = (cust_live["Vitality_Tier"]=="Champion").sum()
            insight_tile(str(champ_n),"Champions",f"🏆 {round(champ_n/total_c*100,1)}% of base",T["success"])
        else: insight_tile("—","Champions","RVI not computed",T["text2"])
    rep_col = col_map.get("repeat_flag"); net_col = col_map.get("net_revenue")
    with p4:
        if rep_col and net_col and rep_col in df.columns and net_col in df.columns:
            rep_rev = df[df[rep_col].astype(str).str.lower().isin(["yes","true","1","repeat"])][net_col].sum()
            tot_rev = df[net_col].sum()
            insight_tile(fmt_pct(round(rep_rev/tot_rev*100,1) if tot_rev>0 else 0),"Repeat Revenue","of total net revenue",T["teal"])
        else: insight_tile("—","Repeat Revenue","No repeat column",T["text2"])
    chan_col = col_map.get("channel"); profit_col = col_map.get("profit")
    with p5:
        if chan_col and net_col and profit_col and all(c in df.columns for c in [chan_col,net_col,profit_col]):
            cm = df.groupby(chan_col).apply(lambda x: x[profit_col].sum()/x[net_col].sum()*100 if x[net_col].sum()>0 else 0)
            insight_tile(str(cm.idxmax()),"Best Margin Channel",f"💰 {round(cm.max(),1)}% margin",T["teal"])
        else: insight_tile("—","Best Margin Channel","Column not found",T["text2"])
    divider()
    date_col = col_map.get("order_date")
    if rep_col and date_col and net_col and all(c in df.columns for c in [rep_col,date_col,net_col]):
        dc = df.copy(); dc[date_col] = pd.to_datetime(dc[date_col], errors="coerce")
        dc["_month"] = dc[date_col].dt.to_period("M").astype(str)
        dc["_repeat"] = dc[rep_col].astype(str).str.lower().isin(["yes","true","1","repeat"])
        rm = dc[dc["_repeat"]].groupby("_month")[net_col].sum()
        nm = dc[~dc["_repeat"]].groupby("_month")[net_col].sum()
        mo = sorted(set(rm.index)|set(nm.index))
        fig_rn = go.Figure()
        fig_rn.add_trace(go.Bar(x=mo,y=[rm.get(m,0) for m in mo],name="Repeat",marker_color="#7C3AED"))
        fig_rn.add_trace(go.Bar(x=mo,y=[nm.get(m,0) for m in mo],name="New",marker_color="#A78BFA",opacity=0.55))
        fig_rn.update_layout(barmode="stack",title="Repeat vs New Customer Revenue by Month",legend=dict(orientation="h",y=1.12))
        st.plotly_chart(sf(fig_rn,340),use_container_width=True)
    divider(); section_lbl("REVENUE ANALYTICS — 6 VIEWS")
    c1,c2 = st.columns(2)
    with c1:
        d = get_revenue_by_column(df,col_map,"channel")
        if d is not None:
            fig1 = px.bar(d,x=d.columns[0],y="Total Revenue",title="Net Revenue by Sales Channel",color="Total Revenue",color_continuous_scale=PS,text="Total Revenue")
            fig1.update_traces(texttemplate="₦%{text:,.0f}",textposition="outside",textfont_size=9)
            st.plotly_chart(sf(fig1),use_container_width=True)
    with c2:
        if monthly is not None:
            fig2 = px.area(monthly,x="Month",y="Net Revenue",title="Monthly Revenue Trend",color_discrete_sequence=["#7C3AED"])
            fig2.update_traces(fill="tozeroy",fillcolor="rgba(124,58,237,0.12)",line_width=2)
            st.plotly_chart(sf(fig2),use_container_width=True)
    c1,c2 = st.columns(2)
    with c1:
        if "Risk_Tier" in df.columns:
            ts_ = get_risk_tier_summary(df)
            fig3 = px.pie(ts_,names="Risk Tier",values="Count",title="Order Revenue Risk Distribution",
                color="Risk Tier",color_discrete_map={"Profit Drain":"#F43F5E","At Risk":"#F59E0B","Stable":"#A78BFA","High Value":"#10B981"},hole=0.52)
            fig3.update_traces(textposition="outside",textinfo="percent+label",textfont_color=T["ct"])
            st.plotly_chart(sf(fig3),use_container_width=True)
    with c2:
        cd = get_revenue_by_column(df,col_map,"product_category")
        if cd is not None:
            fig4 = px.bar(cd.head(8),x="Total Revenue",y=cd.columns[0],orientation="h",title="Revenue by Product Category",color="Total Revenue",color_continuous_scale=TS)
            st.plotly_chart(sf(fig4),use_container_width=True)
    c1,c2 = st.columns(2)
    with c1:
        sd = get_revenue_by_column(df,col_map,"customer_segment")
        if sd is not None:
            fig5 = px.bar(sd,x=sd.columns[0],y="Avg Order Value",title="Avg Order Value by Segment",color="Avg Order Value",color_continuous_scale=PS,text="Avg Order Value")
            fig5.update_traces(texttemplate="₦%{text:,.0f}",textposition="outside")
            st.plotly_chart(sf(fig5),use_container_width=True)
    with c2:
        rc = get_return_rate_by_column(df,col_map,"product_category")
        if rc is not None:
            fig6 = px.bar(rc,x=rc.columns[0],y="Return Rate %",title="Return Rate by Category",color="Return Rate %",color_continuous_scale=RS,text="Return Rate %")
            fig6.update_traces(texttemplate="%{text:.1f}%",textposition="outside")
            st.plotly_chart(sf(fig6),use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# PAGE 2 — CUSTOMER VITALITY
# ════════════════════════════════════════════════════════════════════════════
elif page == "🧬 Customer Vitality":
    page_header("Customer Intelligence","Customer Vitality","Retail Vitality Index — every customer scored 0–100 for health and churn risk.")
    cust_df = st.session_state.get("_cust_df_view")
    if cust_df is None or "RVI_Score" not in cust_df.columns:
        st.info("Upload a dataset and run analysis to compute customer vitality scores."); st.stop()
    ts_  = get_vitality_tier_summary(cust_df)
    avg_ = round(cust_df["RVI_Score"].mean(),1)
    td_  = dict(zip(ts_["Vitality Tier"].astype(str),ts_["Customers"]))
    tot_ = len(cust_df)
    v1,v2,v3,v4,v5,v6 = st.columns(6)
    with v1: kpi_card("","Avg RVI Score",f'{avg_}<span class="kpi-unit">/100</span>',"Customer health index","b-purple","All customers scored")
    with v2: kpi_card("t-ok","Champion",str(td_.get("Champion",0)),f"{round(td_.get('Champion',0)/tot_*100,1) if tot_ else 0}% of base","b-ok","High value · protect")
    with v3: kpi_card("","Loyal",str(td_.get("Loyal",0)),f"{round(td_.get('Loyal',0)/tot_*100,1) if tot_ else 0}% of base","b-purple","Stable · upsell")
    with v4: kpi_card("t-warn","Developing",str(td_.get("Developing",0)),f"{round(td_.get('Developing',0)/tot_*100,1) if tot_ else 0}% of base","b-warn","Monitor · nudge")
    with v5: kpi_card("t-danger","Dormant",str(td_.get("Dormant",0)),f"{round(td_.get('Dormant',0)/tot_*100,1) if tot_ else 0}% of base","b-danger","⚠ Re-engage now")
    with v6: kpi_card("t-teal","Total Customers",str(tot_),"Unique customer IDs","b-teal","All scored")
    divider()
    c1,c2 = st.columns(2)
    with c1:
        fv = px.pie(ts_,names="Vitality Tier",values="Customers",title="Customer Vitality Distribution",
            color="Vitality Tier",color_discrete_map={"Champion":"#10B981","Loyal":"#7C3AED","Developing":"#F59E0B","Dormant":"#F43F5E"},hole=0.52)
        fv.update_traces(textposition="outside",textinfo="percent+label",textfont_color=T["ct"])
        st.plotly_chart(sf(fv),use_container_width=True)
    with c2:
        sk = col_map.get("customer_segment")
        sf_ = sk if sk and sk in cust_df.columns else None
        if sf_:
            sr = get_avg_rvi_by_segment(cust_df,sf_)
            if sr is not None:
                fs = px.bar(sr,x=sf_,y="Avg RVI",title="Avg RVI by Segment",color="Avg RVI",color_continuous_scale=TS,text="Avg RVI")
                fs.update_traces(texttemplate="%{text:.1f}",textposition="outside")
                st.plotly_chart(sf(fs),use_container_width=True)
    divider()
    c1,c2 = st.columns(2)
    with c1:
        section_lbl("TOP CHAMPION CUSTOMERS")
        champs = get_champion_customers(cust_df,n=10)
        if champs is not None and len(champs)>0:
            w = [col_map.get("customer_id"),col_map.get("customer_segment"),"RVI_Score","Vitality_Tier"]
            st.dataframe(champs[[c for c in w if c and c in champs.columns]],use_container_width=True,hide_index=True)
    with c2:
        section_lbl("DORMANT — HIGHEST CHURN RISK")
        dorms = get_dormant_customers(cust_df,n=10)
        if dorms is not None and len(dorms)>0:
            w = [col_map.get("customer_id"),col_map.get("customer_segment"),"RVI_Score","Vitality_Tier"]
            st.dataframe(dorms[[c for c in w if c and c in dorms.columns]],use_container_width=True,hide_index=True)
    divider(); section_lbl("INTERVENTIONS BY VITALITY TIER")
    for tier in ["Champion","Loyal","Developing","Dormant"]:
        with st.expander(tier):
            for action in get_vitality_intervention(tier): st.markdown(f"→ {action}")

# ════════════════════════════════════════════════════════════════════════════
# PAGE 3 — DEEP ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
elif page == "🔬 Deep Analysis":
    page_header("Revenue Intelligence","Deep Analysis","Cross-dimensional drill-down — segment, channel, product, and risk breakdowns.")
    dims = {}
    for label,key in {"Sales Channel":"channel","Product Category":"product_category","Customer Segment":"customer_segment","Region":"region","City":"city","Acquisition Source":"acq_source","Payment Method":"payment"}.items():
        if col_map.get(key) and col_map[key] in df.columns: dims[label] = key
    if dims:
        sel = st.selectbox("Analyse revenue by:", list(dims.keys()))
        dd  = get_revenue_by_column(df,col_map,dims[sel])
        if dd is not None:
            c1,c2 = st.columns([2,1])
            with c1:
                f = px.bar(dd,x=dd.columns[0],y="Total Revenue",title=f"Revenue by {sel}",color="Total Revenue",color_continuous_scale=PS,text="Total Revenue")
                f.update_traces(texttemplate="₦%{text:,.0f}",textposition="outside")
                st.plotly_chart(sf(f,420),use_container_width=True)
            with c2: st.dataframe(dd,use_container_width=True,hide_index=True)
    divider(); section_lbl("DISCOUNT IMPACT ON PROFIT")
    di = get_discount_impact(df,col_map)
    if di is not None:
        c1,c2 = st.columns([2,1])
        with c1:
            f7 = px.bar(di,x="Discount Band",y="Avg Profit (NGN)",title="Avg Profit by Discount Band",color="Avg Profit (NGN)",color_continuous_scale=RS,text="Avg Profit (NGN)")
            f7.update_traces(texttemplate="₦%{text:,.0f}",textposition="outside")
            st.plotly_chart(sf(f7),use_container_width=True)
        with c2: st.dataframe(di,use_container_width=True,hide_index=True)
    divider(); section_lbl("TOP 20 HIGHEST-RISK ORDERS")
    st.caption("Ranked by Revenue Risk Index — built from return status, discount, profit, delivery delay, and rating.")
    tr = get_top_risk_orders(df,col_map,n=20)
    if tr is not None and len(tr)>0:
        def ct(v):
            return {"Profit Drain":"background-color:#2D1B1B;color:#F43F5E","At Risk":"background-color:#2D2410;color:#F59E0B","Stable":"background-color:#1B1F2D;color:#A78BFA","High Value":"background-color:#0F261E;color:#10B981"}.get(str(v),"")
        if "Risk_Tier" in tr.columns: st.dataframe(tr.style.map(ct,subset=["Risk_Tier"]),use_container_width=True,hide_index=True)
        else: st.dataframe(tr,use_container_width=True,hide_index=True)
    divider(); section_lbl("INTERVENTIONS BY RISK TIER")
    for tier in ["Profit Drain","At Risk","Stable","High Value"]:
        with st.expander(tier):
            for i,a in enumerate(get_intervention_recommendation(tier),1): st.markdown(f"{i}. {a}")
    divider(); section_lbl("DATA TRUST REPORT")
    if trust_report:
        ts = trust_report.get("trust_score",0)
        tl,_ = get_trust_label(ts) if isinstance(ts,(int,float)) else ("N/A","")
        c1,c2 = st.columns(2)
        with c1:
            st.markdown(f"**Score:** {ts}/100 — **{tl}**")
            st.markdown(f"**Original rows:** {trust_report.get('original_rows')}")
            st.markdown(f"**After cleaning:** {trust_report.get('final_rows')}")
            st.markdown(f"**Rows removed:** {trust_report.get('rows_removed')}")
        with c2:
            if trust_report.get("issues_found"):
                st.markdown("**Issues found:**")
                for iss in trust_report["issues_found"]: st.markdown(f"- {iss}")
        if trust_report.get("imputation_log"):
            with st.expander("Imputation decisions"):
                for lg in trust_report["imputation_log"]: st.markdown(f"- {lg}")

# ════════════════════════════════════════════════════════════════════════════
# PAGE 4 — ASK NEXUS RETAIL
# ════════════════════════════════════════════════════════════════════════════
elif page == "💬 Ask NEXUS Retail":
    page_header("AI Intelligence","Ask NEXUS Retail",
                "Ask any revenue question in plain English — Mistral AI answers from your live data.")

    if not st.session_state.mistral_api_key:
        st.warning("Add your Mistral API key in the sidebar to use the AI Analyst.", icon="🔑")
        st.stop()

    def _render_ai(text: str) -> str:
        import re as _re
        text = _re.sub(r'(?m)^-{3,}\s*$', '', text)
        text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = _re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
        def _heading(m):
            size = {1:"1.0rem", 2:"0.95rem", 3:"0.9rem"}.get(len(m.group(1)), "0.9rem")
            return (
                f'<div style="font-family:\'Space Grotesk\',sans-serif;font-weight:700;'
                f'font-size:{size};color:{T["primary_soft"]};margin:12px 0 4px;">'
                f'{m.group(2).strip()}</div>'
            )
        text = _re.sub(r'^(#{1,3})\s+(.+)$', _heading, text, flags=_re.MULTILINE)
        text = _re.sub(
            r'(?m)^\d+\.\s+(.+)$',
            lambda m: (
                f'<div style="display:flex;gap:8px;margin:4px 0 4px 12px;">'
                f'<span style="color:{T["primary_soft"]};font-weight:700;flex-shrink:0;">•</span>'
                f'<span style="line-height:1.6;">{m.group(1)}</span></div>'
            ), text,
        )
        text = _re.sub(
            r'(?m)^[-•]\s+(.+)$',
            lambda m: (
                f'<div style="display:flex;gap:8px;margin:4px 0 4px 12px;">'
                f'<span style="color:{T["primary_soft"]};font-weight:700;flex-shrink:0;">•</span>'
                f'<span style="line-height:1.6;">{m.group(1)}</span></div>'
            ), text,
        )
        lines_out = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                lines_out.append('<div style="height:4px;"></div>')
            elif stripped.startswith("<"):
                lines_out.append(stripped)
            else:
                lines_out.append(f'<p style="margin:0 0 7px 0;line-height:1.7;">{stripped}</p>')
        return "\n".join(lines_out)

    suggestions = [
        "Which channel should I invest in most?",
        "What is causing our high return rate?",
        "Which categories are destroying profit?",
        "What 3 actions improve margin this quarter?",
        "Which customer segment is most valuable?",
        "Is our discounting strategy working?",
    ]

    section_lbl("SUGGESTED QUESTIONS")
    sc = st.columns(3)
    clicked_q = None
    for i, s in enumerate(suggestions):
        with sc[i % 3]:
            if st.button(s, key=f"sug_{i}", use_container_width=True):
                clicked_q = s

    divider()

    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="chat-user"><strong>👤 You</strong><br>{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="chat-ai"><strong>🛒 NEXUS Retail</strong><br>'
                f'{_render_ai(msg["content"])}</div>',
                unsafe_allow_html=True,
            )

    # No key= on the text input — avoids all "cannot modify after instantiation" errors.
    # Prefill via value= works correctly when there is no key binding.
    q = st.text_input(
        "Ask anything about your revenue data:",
        value=clicked_q or "",
        placeholder="e.g. Which channel should I scale first?",
        label_visibility="collapsed",
    )

    bc1, bc2 = st.columns([1, 6])
    with bc1:
        send = st.button("Send →", type="primary", key="analyst_send")
    with bc2:
        if st.session_state.chat_history and st.button("Clear", key="analyst_clear"):
            st.session_state.chat_history = []
            st.rerun()

    # Fire on Send button OR when a suggestion was clicked (clicked_q acts as auto-send)
    question_to_send = q if send else (clicked_q if clicked_q else None)

    if question_to_send:
        os.environ["MISTRAL_API_KEY"] = st.session_state.mistral_api_key
        with st.spinner("Analysing…"):
            try:
                ans, upd = ask_analyst(
                    question_to_send, df, col_map,
                    analytics_summary=st.session_state.analytics_summary,
                    chat_history=st.session_state.chat_history.copy(),
                )
                st.session_state.chat_history = upd
                st.rerun()
            except Exception as e:
                st.error(str(e))
                
# ════════════════════════════════════════════════════════════════════════════
# PAGE 5 — EXECUTIVE BRIEF
# ════════════════════════════════════════════════════════════════════════════
elif page == "📋 Executive Brief":
    page_header("AI Intelligence","Executive Brief","Structured 5-section AI brief — summary, insights, conclusion, recommendations, and next steps.")
    if not st.session_state.mistral_api_key:
        st.warning("Add your Mistral API key in the sidebar.", icon="🔑"); st.stop()
    st.markdown(f"""<div class="report-card"><div style="font-weight:700;font-size:0.86rem;color:{T['primary_soft']};margin-bottom:10px;">📄 Report structure — 5 sections</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:0.8rem;color:{T['text2']};"><div>01 · Executive Summary</div><div>02 · In-Depth Insights</div><div>03 · Conclusion</div><div>04 · Recommendations</div><div style="grid-column:1/-1;">05 · Next Steps & Action Plan</div></div></div>""", unsafe_allow_html=True)
    if st.button("Generate Executive Brief", type="primary"):
        os.environ["MISTRAL_API_KEY"] = st.session_state.mistral_api_key
        with st.spinner("Writing your brief…"):
            try:
                summary_ = get_revenue_summary(df, col_map)
                alerts_  = get_proactive_alerts(df, col_map)
                cust_df_ = st.session_state.get("cust_df")
                rvi_avg_ = round(cust_df_["RVI_Score"].mean(), 1) if (cust_df_ is not None and "RVI_Score" in cust_df_.columns) else "N/A"
                today_str = datetime.now().strftime("%B %d, %Y")
                prompt = f"""You are a senior retail revenue analyst.
Generate a professional executive brief for a Nigerian retail business.
Today's date is {today_str}. Do NOT include a title, date line, or "Prepared by" line — start directly with the first section header below.
METRICS:
Net Revenue: \u20a6{summary_.get('total_net_revenue', 0):,.0f}
Gross Revenue: \u20a6{summary_.get('total_gross_revenue', 0):,.0f}
Total Orders: {summary_.get('total_orders', 0)}
Profit Margin: {summary_.get('profit_margin_pct', 'N/A')}%
Return Rate: {summary_.get('return_rate_pct', 'N/A')}%
Avg Order Value: \u20a6{summary_.get('avg_order_value', 0):,.0f}
Avg RVI Score: {rvi_avg_}
ALERTS: {len(alerts_)} active
{chr(10).join([f"- [{a['level'].upper()}] {a['title']}: {a['message']}" for a in alerts_]) if alerts_ else "None"}
Write using EXACTLY these headers on their own line (include the == delimiters):
== EXECUTIVE SUMMARY ==
== IN-DEPTH INSIGHTS ==
== CONCLUSION ==
== RECOMMENDATIONS ==
== NEXT STEPS & ACTION PLAN ==
STRICT RULES:
- Each section must contain at least 3 full sentences of substantive content.
- Do NOT use markdown asterisks ** or * for bold or italic — plain text only.
- Do NOT use backticks or any other markdown symbols.
- Use numbered lists (1. 2. 3.) for recommendations and next steps.
- Reference actual numbers from the metrics above.
- Write in professional English. Total length: 550-700 words."""
                brief = generate_executive_brief(df, col_map, prompt)
                first_marker_pos = brief.find("== EXECUTIVE SUMMARY ==")
                if first_marker_pos > 0: brief = brief[first_marker_pos:]
                brief = re.sub(r'\*{1,3}', '', brief)
                brief = re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', brief)
                brief = brief.replace('`', '')
                for placeholder in ["[Today's Date]", "[TODAY'S DATE]", "[DATE]", "[Date]"]:
                    brief = brief.replace(placeholder, today_str)
                st.session_state.executive_brief = brief
                st.session_state.executive_brief_date = today_str
            except Exception as e:
                st.error(str(e))

    if st.session_state.executive_brief:
        divider()
        brief_text = st.session_state.executive_brief
        brief_date = st.session_state.get("executive_brief_date") or datetime.now().strftime("%B %d, %Y")
        st.markdown(f"""<div class="report-card" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;"><div><div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1.1rem;color:{T['text']};">NEXUS Retail Executive Brief</div><div style="font-size:0.78rem;color:{T['text2']};margin-top:2px;">Prepared by NEXUS Retail Intelligence System</div></div><div style="font-size:0.8rem;color:{T['primary_soft']};font-weight:600;">📅 {brief_date}</div></div>""", unsafe_allow_html=True)

        def _md_to_html(text: str) -> str:
            import re as _re
            text = _re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text, flags=_re.DOTALL)
            text = _re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', text, flags=_re.DOTALL)
            text = text.replace('`', '')
            lines = text.split("\n"); html_parts = []; in_ul = False
            def close_lists():
                nonlocal in_ul
                if in_ul: html_parts.append("</ul>"); in_ul = False
            for raw_line in lines:
                line = raw_line.strip()
                if not line: close_lists(); html_parts.append('<div style="height:6px;"></div>'); continue
                m_num = _re.match(r'^\d+[.)]\s+(.*)', line)
                if m_num:
                    if not in_ul: html_parts.append('<ul style="padding-left:22px;margin:8px 0;color:inherit;">'); in_ul = True
                    html_parts.append(f'<li style="margin-bottom:7px;line-height:1.7;">{m_num.group(1)}</li>'); continue
                m_bul = _re.match(r'^[-•*◦○]\s+(.*)', line)
                if m_bul:
                    if not in_ul: html_parts.append('<ul style="padding-left:22px;margin:8px 0;color:inherit;">'); in_ul = True
                    html_parts.append(f'<li style="margin-bottom:7px;line-height:1.7;">{m_bul.group(1)}</li>'); continue
                is_subheading = (len(line)<=90 and not line.endswith((".",",",":")) and (_re.match(r'^[A-Z][^a-z]{3,}',line) or _re.match(r'^(\d+\.\s+)?[A-Z][A-Za-z ,:\-&/()\d]+$',line)))
                if is_subheading:
                    close_lists()
                    html_parts.append(f'<div style="font-family:\'Space Grotesk\',sans-serif;font-weight:700;font-size:0.88rem;color:{T["primary_soft"]};margin:14px 0 6px;">{line}</div>'); continue
                close_lists()
                html_parts.append(f'<p style="margin:0 0 10px 0;line-height:1.8;color:{T["text"]};">{line}</p>')
            close_lists()
            return "".join(html_parts)

        markers = [
            ("== EXECUTIVE SUMMARY ==","📊 Executive Summary"),
            ("== IN-DEPTH INSIGHTS ==","🔬 In-Depth Insights"),
            ("== CONCLUSION ==","🎯 Conclusion"),
            ("== RECOMMENDATIONS ==","💡 Recommendations"),
            ("== NEXT STEPS & ACTION PLAN ==","🗓 Next Steps & Action Plan"),
        ]
        all_markers = [m for m, _ in markers]; rendered = 0
        for marker, display in markers:
            if marker not in brief_text: continue
            start = brief_text.index(marker) + len(marker); end = len(brief_text)
            for om in all_markers:
                if om != marker and om in brief_text:
                    pos = brief_text.index(om)
                    if start < pos < end: end = pos
            content = brief_text[start:end].strip()
            if not content: continue
            st.markdown(f"""<div class="report-card"><div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1rem;color:{T['primary_soft']};margin-bottom:12px;">{display}</div><div style="font-size:0.88rem;line-height:1.8;color:{T['text']};">{_md_to_html(content)}</div></div>""", unsafe_allow_html=True)
            rendered += 1
        if rendered == 0:
            st.markdown(f'<div class="report-card" style="font-size:0.88rem;line-height:1.8;">{_md_to_html(brief_text)}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button("📥 Download Brief as Text", data=brief_text,
            file_name=f"NEXUS_Brief_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain", type="primary")

# ════════════════════════════════════════════════════════════════════════════
# PAGE 6 — EMAIL INTELLIGENCE
# ════════════════════════════════════════════════════════════════════════════
elif page == "📧 Email Intelligence":
    page_header("Automated Delivery","Email Intelligence","Monday 8AM stakeholder briefings and instant anomaly alerts.")
    section_lbl("EMAIL CONFIGURATION")
    st.caption("Enter your credentials below — stored in session state only, never saved to disk.")
    cfg_c1, cfg_c2 = st.columns(2)
    with cfg_c1:
        new_sender   = st.text_input("📤 Sender Email (Gmail recommended)", value=st.session_state.email_sender, placeholder="your_email@gmail.com", key="ei_sender_input")
        new_password = st.text_input("🔑 App Password", value=st.session_state.email_password, type="password", placeholder="16-char Gmail App Password", key="ei_password_input", help="Gmail → Google Account → Security → App Passwords. NOT your login password.")
    with cfg_c2:
        new_recipients = st.text_area("📬 Recipients (one per line or comma-separated)", value=st.session_state.email_recipients, placeholder="ceo@company.com\nops@company.com", height=120, key="ei_recipients_input")
    if st.button("💾 Save Email Config", type="primary", key="ei_save"):
        st.session_state.email_sender     = new_sender.strip()
        st.session_state.email_password   = new_password.strip()
        st.session_state.email_recipients = new_recipients.strip()
        os.environ["EMAIL_SENDER"]   = st.session_state.email_sender
        os.environ["EMAIL_PASSWORD"] = st.session_state.email_password
        _recs_save = [r.strip() for r in st.session_state.email_recipients.replace("\n",",").split(",") if r.strip()]
        os.environ["EMAIL_RECIPIENTS"] = ",".join(_recs_save)
        st.success(f"✅ Config saved — {len(_recs_save)} recipient(s) configured.", icon="✅"); st.rerun()
    divider()
    _sender_ok   = bool(st.session_state.email_sender)
    _password_ok = bool(st.session_state.email_password)
    _recs_live   = [r.strip() for r in st.session_state.email_recipients.replace("\n",",").split(",") if r.strip()]
    _recs_ok     = len(_recs_live) > 0
    sc1,sc2,sc3  = st.columns(3)
    for col,(label,ok,detail) in zip([sc1,sc2,sc3],[("Sender email",_sender_ok,st.session_state.email_sender or "Not configured"),("App password",_password_ok,"Configured ✓" if _password_ok else "Not configured"),("Recipients",_recs_ok,f"{len(_recs_live)} address(es) configured" if _recs_ok else "Not configured")]):
        bc = T["teal"] if ok else T["danger"]
        col.markdown(f"""<div style="background:{T['surface']};border:1px solid {bc};border-left:4px solid {bc};border-radius:10px;padding:14px 16px;"><div style="font-weight:700;font-size:0.82rem;color:{bc};">{'✓' if ok else '✗'} {label}</div><div style="font-size:0.74rem;color:{T['text2']};margin-top:3px;">{detail}</div></div>""", unsafe_allow_html=True)
    if _recs_live: st.markdown(f'<div style="font-size:0.78rem;color:{T["text2"]};margin-top:8px;">Recipients: {" · ".join(_recs_live)}</div>', unsafe_allow_html=True)
    divider()
    st.info("**Monday briefings:** Every Monday 8:00 AM Africa/Lagos — fires automatically while the app runs.\n\n**Anomaly alerts:** Return rate > 10%, any category margin < 5%, or Profit Drain > 15% of orders.")
    divider(); section_lbl("SEND TEST BRIEF")
    st.caption("Verify your email setup and preview what stakeholders receive every Monday.")
    _all_configured = _sender_ok and _password_ok and _recs_ok
    if not _all_configured: st.warning("Fill in and save the email configuration above before sending.", icon="⚠️")
    if st.button("Send Intelligence Email Now", type="primary", disabled=not _all_configured, key="ei_send"):
        ksum = st.session_state.get("kpi_summary", {}); alts = st.session_state.get("alerts", [])
        brf  = st.session_state.get("executive_brief") or ""
        exc  = (brf[:300]+"...") if len(brf)>300 else brf or "NEXUS Retail weekly scan complete."
        sents = [s.strip() for s in brf.split(".") if len(s.strip())>20]
        rec   = sents[-1] if sents else "Review Profit Drain orders."
        if not ksum: st.warning("Upload and analyse a dataset first.")
        else:
            with st.spinner("Sending…"):
                result = send_intelligence_email(kpi_summary=ksum, alerts=alts, ai_brief_excerpt=exc, recommended_action=rec, is_anomaly=False)
            if result["success"]: st.success(f"✅ {result['message']}"); st.session_state.email_result = result
            else:
                st.error(f"❌ {result['message']}")
                with st.expander("Troubleshooting"):
                    st.markdown("- **Gmail:** App Password required — Google Account → Security → App Passwords\n- **Outlook:** set `SMTP_HOST=smtp.office365.com` and `SMTP_PORT=587`\n- Make sure you clicked **Save Email Config** above before sending")
    if st.session_state.get("email_result"):
        r = st.session_state.email_result
        st.markdown(f'<div style="font-size:0.78rem;color:{T["text2"]};margin-top:8px;">Last sent: {r.get("message","")} · {", ".join(r.get("recipients",[]))}</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# PAGE 7 — EXPORT REPORT
# ════════════════════════════════════════════════════════════════════════════
elif page == "📥 Export Report":
    page_header("Export","Export Report","Download the full intelligence report, cleaned CSV, and cleaned Excel.")
    st.markdown(f"""<div class="report-card"><div style="font-weight:700;font-size:0.88rem;color:{T['text']};margin-bottom:10px;">📄 PDF Report includes</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:0.8rem;color:{T['text2']};"><div>✓ Data Trust Report</div><div>✓ Intelligence Alerts</div><div>✓ Executive Summary</div><div>✓ In-Depth Insights</div><div>✓ Recommendations</div><div>✓ Next Steps & Action Plan</div></div></div>""", unsafe_allow_html=True)
    if st.button("Generate PDF", type="primary"):
        with st.spinner("Generating PDF…"):
            try:
                alts = get_proactive_alerts(df, col_map)
                brf  = st.session_state.executive_brief or "Generate the Executive Brief to include it here."
                pdf  = generate_pdf_report(df=df, col_map=col_map,
                    analytics_summary=st.session_state.analytics_summary,
                    executive_brief=brf, trust_report=trust_report, alerts=alts)
                st.session_state["pdf_bytes"]    = pdf
                st.session_state["pdf_filename"] = f"NEXUS_Retail_{datetime.now().strftime('%Y%m%d')}.pdf"
                st.success("PDF ready — click Download below.")
            except Exception as e:
                st.error(f"PDF generation failed: {e}")
    if st.session_state["pdf_bytes"]:
        st.download_button(label="📥 Download PDF", data=st.session_state["pdf_bytes"],
            file_name=st.session_state["pdf_filename"], mime="application/pdf", type="primary")
    divider(); section_lbl("CLEANED DATASET")
    if st.session_state.df_clean is not None:
        r = len(st.session_state.df_clean); cl = len(st.session_state.df_clean.columns)
        st.markdown(f'<div style="font-size:0.78rem;color:{T["text2"]};margin-bottom:12px;">{r:,} rows · {cl} columns · all issues resolved</div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            st.download_button("📥 Download CSV", data=st.session_state.df_clean.to_csv(index=False).encode("utf-8"),
                file_name=f"NEXUS_Cleaned_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
        with c2:
            st.download_button("📥 Download Excel", data=df_to_excel_bytes(st.session_state.df_clean),
                file_name=f"NEXUS_Cleaned_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")