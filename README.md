# 🛒 NEXUS Retail — Revenue Intelligence OS

**AI-powered revenue, risk, and customer intelligence platform for Nigerian retail businesses.**

NEXUS Retail ingests raw retail sales data (CSV/Excel), cleans and validates it, scores every order for revenue risk and every customer for vitality, and surfaces actionable, AI-generated insights — all through a single, themeable Streamlit dashboard.

🔗 **Live App:** [nexus-retail-oaregrfzrkfw5wrgy9hq8c.streamlit.app](https://nexus-retail-oaregrfzrkfw5wrgy9hq8c.streamlit.app/)
📦 **Repository:** [github.com/Kkhaymie/nexus-retail](https://github.com/Kkhaymie/nexus-retail)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Pages & Modules](#pages--modules)
- [Design System](#design-system)
- [Known Issues & Roadmap](#known-issues--roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

NEXUS Retail is a single-page-application-style Streamlit dashboard built for **Case Study A — Nigerian Retail Sales Analysis**. It transforms a raw transactional dataset into a full intelligence suite in seconds:

1. **Upload** any retail CSV or Excel file — any column naming convention.
2. **Auto-clean** the dataset, resolving duplicates, inconsistent labels, and missing values, and producing a transparent Data Trust Score.
3. **Score every order** with the proprietary **Revenue Risk Index (RRI)** across five signals (returns, discounts, profit, delivery delay, ratings).
4. **Score every customer** with the **Retail Vitality Index (RVI)**, segmenting the customer base into Champion, Loyal, Developing, and Dormant tiers.
5. **Ask questions in plain English** and get answers grounded in your live data via Mistral AI.
6. **Generate a structured Executive Brief** (5 sections, AI-written, auto-dated).
7. **Export** a polished PDF report, plus the cleaned dataset as CSV/Excel.
8. **Schedule weekly email briefings** and instant anomaly alerts.

---

## Features

| Capability | Description |
|---|---|
| 🔍 **AI Data Cleaning** | Detects and resolves duplicates, label inconsistencies, and missing values. Outputs a 0–100 Data Trust Score with a full imputation log. |
| 🎯 **Revenue Risk Index (RRI)** | Every order scored 0–100 across five risk signals. Orders are bucketed into `High Value → Stable → At Risk → Profit Drain`. |
| 🧬 **Retail Vitality Index (RVI)** | Every customer scored 0–100 for health/engagement. Segments: `Champion → Loyal → Developing → Dormant`. |
| 🔮 **Predictive Intelligence** | Auto-computed on upload: revenue forecast (linear regression), churn risk, champion share, repeat-revenue share, and best-margin channel. |
| 🧮 **Global Filters & Slicers** | Sidebar-wide filters for date range (timeline slider), sales channel, customer segment, region, product category, and risk tier — applied across all pages with an active-filter indicator bar. |
| 💬 **Conversational AI Analyst** | Ask free-form revenue questions; Mistral AI answers using your live, filtered dataset as context. Suggested-question quick-fill. |
| 📋 **Executive Brief Generator** | 5-section AI-written brief (Executive Summary, In-Depth Insights, Conclusion, Recommendations, Next Steps & Action Plan), auto-dated, markdown-cleaned, and downloadable. |
| 📧 **Email Intelligence** | Scheduled Monday 8 AM (Africa/Lagos) stakeholder briefings via APScheduler, plus instant anomaly alerts (high return rate, low category margin, excessive Profit Drain share). |
| 📥 **Export Report** | One-click PDF report (via ReportLab) bundling the Data Trust Report, alerts, and Executive Brief sections, plus cleaned CSV/Excel downloads. |
| 🌑☀️ **Dark / Light Theming** | Full token-based theme system with a cohesive purple/teal palette, applied consistently across charts, cards, sidebar, and widgets. |

---

## Architecture

```
                 ┌─────────────────────────┐
                 │   Streamlit Frontend     │
                 │        app.py            │
                 └────────────┬────────────┘
                              │
        ┌──────────────┬─────┴──────┬───────────────┬────────────────┐
        ▼              ▼            ▼               ▼                ▼
 utils/cleaner   utils/intelligence  utils/vitality  utils/analyst   utils/report
 (data cleaning) (RRI scoring,       (RVI scoring,   (Mistral AI     (PDF generation
                  alerts, summaries)  segments)       via httpx)       via ReportLab)
        │                                                 │
        └──────────────────────┬──────────────────────────┘
                                 ▼
                        utils/scheduler
                (APScheduler + email delivery,
                   anomaly detection, .env config)
```

**Data flow:**

1. User uploads a file → `load_dataset()` parses it (CSV/XLSX/XLS).
2. `clean_dataset()` returns a cleaned DataFrame + a trust report (issues found, imputation log, trust score).
3. `detect_columns()` builds a `col_map` — a flexible mapping from internal field names (e.g. `net_revenue`, `channel`, `order_date`) to the actual column names in the uploaded file, so the app works with **any** naming convention.
4. `compute_revenue_risk_index()` adds `RRI_Score` and `Risk_Tier` columns to every order.
5. `compute_retail_vitality_index()` builds a per-customer DataFrame with `RVI_Score` and `Vitality_Tier`.
6. All seven pages read from this shared, filtered state.

---

## Tech Stack

- **Frontend / App framework:** [Streamlit](https://streamlit.io/)
- **Data processing:** pandas, NumPy
- **Visualization:** Plotly Express & Graph Objects
- **Machine Learning:** scikit-learn (`LinearRegression` for revenue forecasting)
- **AI / LLM:** Mistral AI — called via raw `httpx` REST requests (no `mistralai` SDK dependency)
- **PDF Generation:** ReportLab
- **Scheduling & Email:** APScheduler + `smtplib`
- **Environment management:** `python-dotenv`
- **Language/runtime:** Python 3.14

---

## Project Structure

```
nexus_retail/
├── app.py                  # Main Streamlit application (multi-page dashboard)
├── .env                     # Environment variables (NOT committed — see Configuration)
├── requirements.txt         # Python dependencies
└── utils/
    ├── cleaner.py            # Data loading, cleaning, trust scoring, Excel export
    ├── intelligence.py        # Column detection, RRI scoring, revenue summaries,
    │                           #   alerts, risk-tier and discount-impact analytics
    ├── vitality.py            # RVI scoring, vitality tiers, champion/dormant logic
    ├── analyst.py             # Mistral AI integration: ask_analyst(),
    │                           #   generate_executive_brief()
    ├── report.py              # ReportLab-based PDF report generation
    └── scheduler.py            # APScheduler setup, email sending, anomaly
                                #   detection, get_email_config()
```

---

## Getting Started

### Prerequisites

- Python 3.10+ (developed and tested on Python 3.14)
- A free [Mistral AI](https://console.mistral.ai) API key (for AI Analyst & Executive Brief features)
- (Optional) A Gmail account with an **App Password** for Email Intelligence

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Kkhaymie/nexus-retail.git
cd nexus-retail

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Running the App

```bash
# Windows (matches deployed dev environment)
C:\Users\HP\Downloads\nexus_retail\nexus_retail\venv\Scripts\python.exe -m streamlit run app.py

# macOS / Linux / generic
streamlit run app.py
```

The app will open at `http://localhost:8501`.

### First Run

1. Open the **🔑 API Key** panel in the sidebar and paste your Mistral API key (or set `MISTRAL_API_KEY` in `.env` — see below).
2. Upload your retail dataset (`.csv`, `.xlsx`, or `.xls`) via the **Dataset** uploader.
3. Click **🚀 Run Full Analysis**.
4. Use the **Navigation** menu to explore Command Center, Customer Vitality, Deep Analysis, Ask NEXUS Retail, Executive Brief, Email Intelligence, and Export Report.
5. Use **🧮 Filters & Slicers** in the sidebar to drill into specific date ranges, channels, segments, regions, product categories, or risk tiers — filters apply globally across all pages.

---

## Configuration

NEXUS Retail is configured via a `.env` file in the project root (never committed to version control).

```ini
# ── Mistral AI ──────────────────────────────────────────────
MISTRAL_API_KEY=your_mistral_api_key_here

# ── Email Intelligence (Gmail recommended) ─────────────────
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_16_char_gmail_app_password
EMAIL_RECIPIENTS=ceo@company.com,ops@company.com,analyst@company.com

# ── Optional: alternate SMTP provider ──────────────────────
# SMTP_HOST=smtp.office365.com
# SMTP_PORT=587
```

> ⚠️ **Gmail App Passwords:** Standard Gmail login passwords will not work for SMTP. Generate an App Password under **Google Account → Security → App Passwords**, and use that 16-character value for `EMAIL_PASSWORD`.

### Deploying to Streamlit Community Cloud

When deploying, add the same variables under **App Settings → Secrets** in TOML format:

```toml
MISTRAL_API_KEY = "your_mistral_api_key_here"
EMAIL_SENDER = "your_email@gmail.com"
EMAIL_PASSWORD = "your_16_char_gmail_app_password"
EMAIL_RECIPIENTS = "ceo@company.com,ops@company.com"
```

---

## Pages & Modules

### 🏠 Command Center
The default landing page after analysis. Displays six headline KPI cards (Total Orders, Net Revenue, Profit Margin, Return Rate, Avg Risk Score, Data Trust Score), auto-generated intelligence alerts, five predictive insight tiles (revenue forecast, churn risk, champions, repeat revenue share, best-margin channel), and six core revenue analytics charts.

### 🧬 Customer Vitality
Surfaces the Retail Vitality Index across the customer base: tier-distribution KPI cards (Champion/Loyal/Developing/Dormant), average RVI by segment, top champion customers, highest-churn-risk dormant customers, and tier-specific intervention playbooks.

### 🔬 Deep Analysis
Cross-dimensional drill-down by sales channel, product category, customer segment, region, city, acquisition source, or payment method. Includes discount-impact-on-profit analysis, a ranked table of the top 20 highest-risk orders (color-coded by risk tier), risk-tier intervention playbooks, and the full Data Trust Report.

### 💬 Ask NEXUS Retail
A conversational interface to Mistral AI, grounded in the current (filtered) dataset and analytics summary. Includes six suggested-question quick-fill buttons, persistent chat history, and AI responses rendered with clean markdown-to-HTML formatting (headings, bold, numbered/bulleted lists).

### 📋 Executive Brief
On demand, generates a structured, professional brief with five sections — Executive Summary, In-Depth Insights, Conclusion, Recommendations, and Next Steps & Action Plan — using live KPI and alert data. The brief is automatically dated to the current date, stripped of stray markdown artifacts, rendered as styled report cards, and downloadable as plain text.

### 📧 Email Intelligence
Displays the current email configuration status (sender, app password, recipients) sourced from `.env`. Supports sending an on-demand test briefing and documents the automatic schedule: weekly Monday 8 AM (Africa/Lagos) briefings plus instant anomaly alerts (return rate > 10%, any category margin < 5%, or Profit Drain orders > 15% of total).

### 📥 Export Report
Generates a full PDF intelligence report (Data Trust Report, alerts, Executive Brief sections) via ReportLab, with the download button persisted in session state so it remains available after generation. Also provides one-click downloads of the cleaned dataset as CSV or Excel.

---

## Design System

NEXUS Retail uses a consistent, token-driven design system across both Dark and Light themes.

| Token | Dark | Light | Usage |
|---|---|---|---|
| Primary | `#7C3AED` | `#7C3AED` | Buttons, accents, gradients |
| Primary Soft | `#A78BFA` | `#7C3AED` | Secondary text, badges, chart accents |
| Surface | `#1E1B4B` | `#FFFFFF` | Cards, sidebar |
| Surface 2 | `#2D2A5E` | `#EDE9FE` | Secondary surfaces |
| Background | `#0F172A` | `#F1F5F9` | App background |
| Text | `#F1F5F9` | `#0F172A` | Primary text |
| Text Secondary | `#A78BFA` | `#334155` | Labels, captions |
| Teal | `#0F766E` | `#0F766E` | Secondary accent (vitality, repeat revenue) |
| Danger | `#F43F5E` | `#E11D48` | Risk alerts, dormant tier |
| Warning | `#F59E0B` | `#D97706` | Caution states |
| Success | `#10B981` | `#059669` | Healthy/positive states |

**Typography:** [Space Grotesk](https://fonts.google.com/specimen/Space+Grotesk) for headings and KPI values, [Inter](https://fonts.google.com/specimen/Inter) for body text.

**Components:** KPI cards with gradient top-borders, pill badges, alert cards with severity-coded left borders, feature cards, chat bubbles, and report cards — all theme-aware via CSS variables injected at runtime based on the active theme.

---

## Known Issues & Roadmap

The following items are tracked as open issues from the most recent development cycle:

- [ ] **Executive Brief completeness** — Despite prompt-engineering fixes (explicit section markers, markdown stripping, `max_tokens=2500`, auto-dating), the AI-generated brief can occasionally truncate or omit a section under certain data conditions. Further investigation into response length handling and retry/continuation logic is planned.
- [ ] **Email Intelligence UI** — The in-app sender/recipient configuration tabs were not rendering reliably; the project has reverted to a `.env`-driven configuration as the stable interim approach. A future iteration may reintroduce an in-app form with improved state handling.

**Planned enhancements:**

- Retry/continuation logic for long AI-generated content (Executive Brief)
- Optional in-app email configuration with validation
- Additional predictive signals (e.g., customer lifetime value forecasting)
- Multi-dataset comparison mode

---

## Contributing

1. Fork the repository and create a feature branch (`git checkout -b feature/your-feature`).
2. Make your changes, following the existing code style (theme tokens via `T[...]`, helper functions for repeated UI patterns).
3. Test locally with `streamlit run app.py` against a sample dataset.
4. Submit a pull request with a clear description of the change and any new configuration requirements.

---

## License

This project is part of **Case Study A** for Nigerian retail revenue intelligence. License terms to be determined by the repository owner — see [GitHub repository](https://github.com/Kkhaymie/nexus-retail) for the most current licensing information.

---

<p align="center">
  <sub>NEXUS Retail v2.0 · Powered by Mistral AI · RRI · RVI · Email Intelligence</sub>
</p>