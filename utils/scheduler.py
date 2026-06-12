import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION A: EMAIL CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

def get_email_config():
    """Load email configuration from environment variables."""
    return {
        "sender":     os.getenv("EMAIL_SENDER", ""),
        "password":   os.getenv("EMAIL_PASSWORD", ""),
        "recipients": [
            r.strip()
            for r in os.getenv("EMAIL_RECIPIENTS", "").split(",")
            if r.strip()
        ],
        "smtp_host":  os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "smtp_port":  int(os.getenv("SMTP_PORT", 587)),
        "app_url":    os.getenv("APP_URL", "https://your-nexus-app.streamlit.app"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION B: HTML EMAIL TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

def build_html_email(
    kpi_summary: dict,
    alerts: list,
    ai_brief_excerpt: str,
    recommended_action: str,
    app_url: str,
    report_date: str,
    is_anomaly: bool = False,
) -> str:
    """
    Build a fully formatted HTML email for stakeholder delivery.
    Works with any dataset — all values passed in from the caller.

    Parameters
    ----------
    kpi_summary        : dict with keys like 'total_net_revenue', 'profit_margin_pct', etc.
    alerts             : list of alert dicts from get_proactive_alerts()
    ai_brief_excerpt   : first 300 chars of the Mistral executive brief
    recommended_action : single recommended action string
    app_url            : live Streamlit app URL
    report_date        : formatted date string e.g. "Monday, 16 June 2025"
    is_anomaly         : True if this is an immediate anomaly alert, not a Monday brief
    """
    subject_line = (
        "⚠️ NEXUS Retail — Anomaly Alert Detected"
        if is_anomaly
        else f"📊 NEXUS Retail Intelligence Brief — {report_date}"
    )

    banner_color = "#c0392b" if is_anomaly else "#1a5c1a"
    banner_label = "ANOMALY ALERT" if is_anomaly else "WEEKLY INTELLIGENCE BRIEF"

    # ── KPI table rows ────────────────────────────────────────────────────────
    kpi_rows = ""
    kpi_display = [
        ("Total Net Revenue",  kpi_summary.get("total_net_revenue"),    "₦{:,.0f}"),
        ("Total Profit",       kpi_summary.get("total_profit"),         "₦{:,.0f}"),
        ("Profit Margin",      kpi_summary.get("profit_margin_pct"),    "{:.1f}%"),
        ("Avg Order Value",    kpi_summary.get("avg_order_value"),      "₦{:,.0f}"),
        ("Return Rate",        kpi_summary.get("return_rate_pct"),      "{:.1f}%"),
        ("Total Orders",       kpi_summary.get("total_orders"),         "{:,}"),
        ("Avg RVI Score",      kpi_summary.get("avg_rvi"),              "{:.1f}/100"),
    ]
    for label, value, fmt in kpi_display:
        if value is not None:
            try:
                formatted = fmt.format(value)
            except Exception:
                formatted = str(value)

            # Colour-code the return rate cell if elevated
            cell_style = ""
            if label == "Return Rate" and isinstance(value, (int, float)) and value > 5:
                cell_style = "color:#c0392b;font-weight:bold;"

            kpi_rows += f"""
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;color:#555;
                           font-size:13px;">{label}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;
                           font-weight:600;font-size:13px;{cell_style}">{formatted}</td>
            </tr>"""

    # ── Alert rows ────────────────────────────────────────────────────────────
    alert_html = ""
    if alerts:
        for alert in alerts[:3]:  # cap at 3 in email
            level = alert.get("level", "info")
            border = (
                "#c0392b" if level == "critical"
                else "#e67e22" if level == "warning"
                else "#2980b9"
            )
            bg = (
                "#fff0f0" if level == "critical"
                else "#fffbf0" if level == "warning"
                else "#f0f8ff"
            )
            alert_html += f"""
            <div style="border-left:4px solid {border};background:{bg};
                        padding:10px 14px;margin:8px 0;border-radius:4px;">
                <strong style="font-size:13px;">{alert.get('icon','')}
                {alert.get('title','')}</strong><br>
                <span style="font-size:12px;color:#555;">{alert.get('message','')}</span>
            </div>"""
    else:
        alert_html = (
            '<p style="color:#27ae60;font-size:13px;">✅ '
            'No active alerts. All KPIs within normal range.</p>'
        )

    # ── Full HTML template ────────────────────────────────────────────────────
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1.0">
    </head>
    <body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f5f5f5;">
        <table width="100%" cellpadding="0" cellspacing="0"
               style="background:#f5f5f5;padding:24px 0;">
            <tr><td align="center">
                <table width="600" cellpadding="0" cellspacing="0"
                       style="background:#ffffff;border-radius:8px;
                              box-shadow:0 2px 12px rgba(0,0,0,0.08);
                              overflow:hidden;">

                    <!-- Header banner -->
                    <tr>
                        <td style="background:{banner_color};padding:20px 28px;">
                            <p style="margin:0;color:#ffffff;font-size:11px;
                                      letter-spacing:1.5px;font-weight:600;">
                                {banner_label}</p>
                            <h1 style="margin:4px 0 0;color:#ffffff;font-size:20px;
                                       font-weight:700;">🛒 NEXUS Retail</h1>
                            <p style="margin:4px 0 0;color:rgba(255,255,255,0.8);
                                      font-size:12px;">{report_date}</p>
                        </td>
                    </tr>

                    <!-- KPI Summary -->
                    <tr>
                        <td style="padding:24px 28px 8px;">
                            <h2 style="margin:0 0 12px;font-size:14px;color:#1a5c1a;
                                       text-transform:uppercase;letter-spacing:1px;">
                                Performance Summary</h2>
                            <table width="100%" cellpadding="0" cellspacing="0"
                                   style="border:1px solid #eee;border-radius:6px;
                                          overflow:hidden;">
                                {kpi_rows}
                            </table>
                        </td>
                    </tr>

                    <!-- Alerts -->
                    <tr>
                        <td style="padding:16px 28px 8px;">
                            <h2 style="margin:0 0 10px;font-size:14px;color:#1a5c1a;
                                       text-transform:uppercase;letter-spacing:1px;">
                                Intelligence Alerts</h2>
                            {alert_html}
                        </td>
                    </tr>

                    <!-- AI Brief excerpt -->
                    <tr>
                        <td style="padding:16px 28px 8px;">
                            <h2 style="margin:0 0 10px;font-size:14px;color:#1a5c1a;
                                       text-transform:uppercase;letter-spacing:1px;">
                                AI Brief Excerpt</h2>
                            <p style="font-size:13px;color:#444;line-height:1.6;
                                      background:#f9f9f9;padding:14px;border-radius:6px;
                                      margin:0;">{ai_brief_excerpt}</p>
                        </td>
                    </tr>

                    <!-- Recommended action -->
                    <tr>
                        <td style="padding:16px 28px 8px;">
                            <h2 style="margin:0 0 10px;font-size:14px;color:#1a5c1a;
                                       text-transform:uppercase;letter-spacing:1px;">
                                Priority Action This Week</h2>
                            <div style="background:#e8f5e9;border-left:4px solid #1a5c1a;
                                        padding:12px 16px;border-radius:4px;">
                                <p style="margin:0;font-size:13px;color:#2d6a2d;
                                          font-weight:600;">→ {recommended_action}</p>
                            </div>
                        </td>
                    </tr>

                    <!-- CTA button -->
                    <tr>
                        <td style="padding:24px 28px 28px;text-align:center;">
                            <a href="{app_url}"
                               style="display:inline-block;background:#1a5c1a;color:#ffffff;
                                      padding:12px 28px;border-radius:6px;font-size:14px;
                                      font-weight:600;text-decoration:none;">
                                Open Full Dashboard →
                            </a>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background:#f8f8f8;padding:14px 28px;
                                   border-top:1px solid #eee;">
                            <p style="margin:0;font-size:11px;color:#aaa;text-align:center;">
                                Generated by NEXUS Retail Intelligence System ·
                                <a href="{app_url}" style="color:#1a5c1a;">
                                    {app_url}</a><br>
                                To update recipients, edit EMAIL_RECIPIENTS in your .env file.
                            </p>
                        </td>
                    </tr>

                </table>
            </td></tr>
        </table>
    </body>
    </html>
    """
    return html, subject_line


# ─────────────────────────────────────────────────────────────────────────────
# SECTION C: SEND EMAIL
# ─────────────────────────────────────────────────────────────────────────────

def send_intelligence_email(
    kpi_summary: dict,
    alerts: list,
    ai_brief_excerpt: str,
    recommended_action: str,
    is_anomaly: bool = False,
) -> dict:
    """
    Build and send the HTML intelligence email to all configured recipients.

    Returns a result dict: {"success": bool, "message": str, "recipients": list}
    """
    config = get_email_config()

    if not config["sender"] or not config["password"]:
        return {
            "success": False,
            "message": "EMAIL_SENDER or EMAIL_PASSWORD not configured in .env",
            "recipients": []
        }

    if not config["recipients"]:
        return {
            "success": False,
            "message": "EMAIL_RECIPIENTS not configured in .env",
            "recipients": []
        }

    report_date = datetime.now().strftime("%A, %d %B %Y")

    html_body, subject = build_html_email(
        kpi_summary=kpi_summary,
        alerts=alerts,
        ai_brief_excerpt=ai_brief_excerpt,
        recommended_action=recommended_action,
        app_url=config["app_url"],
        report_date=report_date,
        is_anomaly=is_anomaly,
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"NEXUS Retail <{config['sender']}>"
    msg["To"]      = ", ".join(config["recipients"])
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["sender"], config["password"])
            server.sendmail(
                config["sender"],
                config["recipients"],
                msg.as_string()
            )
        logger.info(
            f"Intelligence email sent to {config['recipients']} at {datetime.now()}"
        )
        return {
            "success": True,
            "message": f"Email sent to {len(config['recipients'])} recipient(s)",
            "recipients": config["recipients"],
        }
    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": (
                "SMTP authentication failed. Check EMAIL_SENDER and EMAIL_PASSWORD. "
                "For Gmail, use an App Password (not your main password)."
            ),
            "recipients": []
        }
    except Exception as e:
        logger.error(f"Email send error: {e}")
        return {"success": False, "message": str(e), "recipients": []}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION D: ANOMALY DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

def detect_anomalies(df, col_map, prev_kpis: dict = None) -> list:
    """
    Detect anomaly conditions that warrant an immediate alert email.
    Works on any dataset through col_map.

    Conditions checked:
    1. Return rate > 10% (absolute threshold)
    2. Return rate increased > 2pp vs prev_kpis (if available)
    3. Any product category margin < 5%
    4. Profit Drain orders > 15% of total orders

    Returns list of triggered anomaly strings.
    """
    anomalies = []

    # Condition 1 & 2: Return rate
    ret_col = col_map.get("return_status")
    if ret_col and ret_col in df.columns:
        returned = df[ret_col].astype(str).str.lower().str.strip().isin(
            ['returned', 'partial return']
        ).sum()
        current_ret_rate = round(returned / len(df) * 100, 1)

        if current_ret_rate > 10:
            anomalies.append(
                f"CRITICAL: Return rate is {current_ret_rate}% — exceeds 10% threshold."
            )
        if prev_kpis and prev_kpis.get("return_rate_pct"):
            delta = current_ret_rate - prev_kpis["return_rate_pct"]
            if delta > 2:
                anomalies.append(
                    f"WARNING: Return rate increased by {delta:.1f}pp "
                    f"({prev_kpis['return_rate_pct']}% → {current_ret_rate}%)."
                )

    # Condition 3: Category margin < 5%
    cat_col    = col_map.get("product_category")
    net_col    = col_map.get("net_revenue")
    profit_col = col_map.get("profit")

    if cat_col and net_col and profit_col:
        if all(c in df.columns for c in [cat_col, net_col, profit_col]):
            cat_margins = df.groupby(cat_col).apply(
                lambda x: x[profit_col].sum() / x[net_col].sum() * 100
                if x[net_col].sum() > 0 else 0
            )
            low_margin = cat_margins[cat_margins < 5]
            for cat, margin in low_margin.items():
                anomalies.append(
                    f"WARNING: {cat} margin is {margin:.1f}% — below 5% floor."
                )

    # Condition 4: Profit Drain concentration
    if "Risk_Tier" in df.columns:
        drain_pct = (df["Risk_Tier"] == "Profit Drain").sum() / len(df) * 100
        if drain_pct > 15:
            anomalies.append(
                f"CRITICAL: {drain_pct:.1f}% of all orders are Profit Drain — "
                "exceeds 15% threshold."
            )

    return anomalies


# ─────────────────────────────────────────────────────────────────────────────
# SECTION E: APSCHEDULER SETUP (called once at app startup)
# ─────────────────────────────────────────────────────────────────────────────

def start_email_scheduler(get_current_state_fn):
    """
    Start the APScheduler background job for Monday 8AM emails.

    Parameters
    ----------
    get_current_state_fn : callable
        A zero-argument function that returns a dict with keys:
        {"df": DataFrame, "col_map": dict, "kpi_summary": dict,
         "alerts": list, "ai_brief": str}
        This is how the scheduler gets the latest app state at send time.

    Usage in app.py
    ---------------
        from utils.scheduler import start_email_scheduler

        def get_state():
            return {
                "df":          st.session_state.get("df_with_risk"),
                "col_map":     st.session_state.get("col_map"),
                "kpi_summary": st.session_state.get("kpi_summary", {}),
                "alerts":      st.session_state.get("alerts", []),
                "ai_brief":    st.session_state.get("executive_brief", ""),
            }

        if "scheduler_started" not in st.session_state:
            start_email_scheduler(get_state)
            st.session_state.scheduler_started = True
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("apscheduler not installed — email scheduling disabled.")
        return None

    def _send_monday_brief():
        state = get_current_state_fn()
        if state.get("df") is None:
            logger.info("Scheduler: no dataset loaded — skipping email.")
            return

        kpi_summary = state.get("kpi_summary", {})
        alerts      = state.get("alerts", [])
        ai_brief    = state.get("ai_brief", "")
        brief_excerpt = (ai_brief[:300] + "...") if len(ai_brief) > 300 else ai_brief

        # Extract recommended action from brief (last sentence heuristic)
        sentences = [s.strip() for s in ai_brief.split(".") if len(s.strip()) > 20]
        recommended = sentences[-1] if sentences else "Review top Profit Drain orders."

        result = send_intelligence_email(
            kpi_summary=kpi_summary,
            alerts=alerts,
            ai_brief_excerpt=brief_excerpt,
            recommended_action=recommended,
            is_anomaly=False,
        )
        logger.info(f"Monday brief result: {result['message']}")

    scheduler = BackgroundScheduler(timezone="Africa/Lagos")
    scheduler.add_job(
        _send_monday_brief,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="monday_brief",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("NEXUS Retail email scheduler started — Monday 8AM Africa/Lagos.")
    return scheduler