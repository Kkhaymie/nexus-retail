# NEXUS Retail — Revenue Intelligence Operating System
### Version 2.0 | Case Study A: Nigerian Retail Sales & Customer Revenue Intelligence

---

> **North Star:**
> *"This retail business generated ₦68.5M in revenue across 1,506 orders — but 174 orders are
> losing money, 7.4% of products are being returned, and your highest-value customers are drifting
> toward churn undetected. NEXUS Retail scores every order for risk, scores every customer for
> health, predicts what happens next month, and emails your stakeholders every Monday morning
> before they've had their coffee."*

---

## What Is NEXUS Retail?

NEXUS Retail is a **dataset-agnostic**, AI-powered Retail Intelligence Operating System built
in Streamlit. Unlike dashboards that show you what happened, NEXUS Retail:

- **Proactively alerts you** to revenue risks without you asking
- **Engineers two new metrics** — Revenue Risk Index and Retail Vitality Index — that do not
  exist in the raw data
- **Predicts next month's revenue** using linear regression on your historical trend
- **Answers questions in plain English** via Mistral AI
- **Emails stakeholders automatically** every Monday at 8AM (Africa/Lagos timezone)
- **Works on any retail dataset** — column detection is heuristic, not hardcoded

---

## The 7 Layers

| # | Layer | File | What It Does |
|---|-------|------|-------------|
| 1 | Ingest & Clean | `utils/cleaner.py` | Auto-cleans any retail CSV/Excel. Fixes casing, duplicates, missing values, label variants. Returns a Data Trust Report. |
| 2 | Revenue Risk Index | `utils/intelligence.py` | Scores every **order** 0–100 for financial risk. Segments: High Value, Stable, At Risk, Profit Drain. |
| 2B | Retail Vitality Index | `utils/vitality.py` | Scores every **customer** 0–100 for health and churn risk. Segments: Champion, Loyal, Developing, Dormant. |
| 3 | Command Center | `app.py` | Live dashboard: KPI tiles, proactive alerts, 5 predictive insights, 6 revenue charts. All fire automatically on upload. |
| 4 | Conversational Analyst | `utils/analyst.py` | Ask any revenue question in plain English. Mistral AI answers using your live dataset as context. |
| 5 | Export Engine | `utils/report.py` | Downloadable PDF report + cleaned CSV + cleaned Excel. |
| 6 | Email Intelligence | `utils/scheduler.py` | Monday 8AM automated HTML briefing to stakeholders. Instant anomaly alerts when thresholds are breached. |

---

## The Two Derived Metrics

### Revenue Risk Index (RRI) — per order, 0–100

Higher score = higher financial risk to the business.

| Signal | Weight | Logic |
|--------|--------|-------|
| Order returned (full) | 35 pts | Direct revenue loss |
| Discount level | 25 pts | Scaled: 0% → 0 pts, 20%+ → 25 pts |
| Negative profit | 20 pts | Order cost exceeds revenue |
| Late delivery | 12 pts | Delivery status = "Late" |
| Low customer rating (≤ 2) | 8 pts | Satisfaction signal |

**This metric does not exist in the raw data. It was engineered for this system.**

### Retail Vitality Index (RVI) — per customer, 0–100

Higher score = healthier, more valuable customer relationship.

| Signal | Weight | Logic |
|--------|--------|-------|
| Repeat purchase behaviour | 30 pts | `Repeat_Customer_Flag = Yes` or order count > 1 |
| AOV vs segment median | 25 pts | Customer AOV ÷ segment median, capped at 2× |
| Customer tenure | 20 pts | Tenure months ÷ max tenure |
| Return rate (this customer) | 15 pts | 0% returns = 15 pts; 100% returns = 0 pts |
| Acquisition source quality | 10 pts | Referral/Google = 10; WhatsApp/Direct = 8; Social/Email = 6; Paid = 4 |

**This metric does not exist in the raw data. It was engineered for this system.**

---

## Project Structure

```
nexus_retail/
├── app.py                  ← Main Streamlit app (7 pages)
├── utils/
│   ├── __init__.py         ← Empty package marker
│   ├── cleaner.py          ← Layer 1: Data cleaning engine
│   ├── intelligence.py     ← Layer 2: RRI + order analytics
│   ├── vitality.py         ← Layer 2B: RVI customer health scores
│   ├── analyst.py          ← Layer 4: Mistral conversational AI
│   ├── report.py           ← Layer 5: PDF + Excel export
│   └── scheduler.py        ← Layer 6: Email intelligence engine
├── requirements.txt
├── .env                    ← API keys and email config (never commit this)
├── .gitignore
└── README.md
```

---

## Setup

### 1. Navigate to your project folder

```powershell
cd C:\Users\HP\Downloads\nexus_retail
```

### 2. Activate virtual environment

```powershell
# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

Your prompt should show `(venv)` at the start.

### 3. Install all dependencies

```powershell
pip install -r requirements.txt
```

If `apscheduler` or `scikit-learn` are missing, install them separately:

```powershell
pip install apscheduler scikit-learn
```

### 4. Configure your `.env` file

Open `.env` in VS Code or Notepad and fill in:

```
MISTRAL_API_KEY=your_mistral_key_here

EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_16_char_gmail_app_password
EMAIL_RECIPIENTS=recipient1@email.com,recipient2@email.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
APP_URL=http://localhost:8501
```

**Getting your Mistral API key:** https://console.mistral.ai

**Getting a Gmail App Password (required — your main password will not work):**
1. Go to https://myaccount.google.com
2. Security → 2-Step Verification (must be ON)
3. Search "App passwords" → Create new → Name it "NEXUS Retail"
4. Copy the 16-character code → paste as `EMAIL_PASSWORD`

**Note:** Email variables are optional. If left blank, the app runs fully — the Email Intelligence
page will show ❌ configuration status but no crashes will occur.

### 5. Run the app

```powershell
streamlit run app.py
```

Your app opens at: **http://localhost:8501**

---

## Usage

1. Upload any retail dataset (CSV or Excel) using the sidebar
2. Click **🚀 Run Full Analysis**
3. Navigate through the 7 pages:

| Page | What to do |
|------|-----------|
| 🏠 Command Center | KPIs, alerts, 5 predictive insights, and 6 revenue charts appear automatically |
| 🧬 Customer Vitality | Browse Champion and Dormant customers; see RVI by segment |
| 🔬 Deep Analysis | Drill into revenue by any dimension; view top 20 risk orders |
| 💬 Ask NEXUS Retail | Type any revenue question; get a Mistral AI answer |
| 📋 Executive Brief | Generate the AI one-page brief for stakeholders |
| 📧 Email Intelligence | Verify email config; send a test brief; view anomaly alert logic |
| 📥 Export Report | Download PDF report, cleaned CSV, and cleaned Excel |

---

## Dataset Compatibility

NEXUS Retail uses heuristic column detection. It works on any retail dataset containing
order-level records, regardless of column names. Detection patterns include:

- Any column with `order_id`, `order id` → order identifier
- Any column with `net_revenue`, `revenue`, `net` → revenue signal
- Any column with `return_status`, `return` → return signal
- Any column with `customer_id`, `cust_id` → customer grouping
- Any column with `product_category`, `category` → category grouping
- Any column with `sales_channel`, `channel` → channel grouping
- Any column with `customer_segment`, `segment` → segment grouping
- And so on for all 24 detected concepts

---

## The 5 Predictive Intelligence Insights (Command Center)

These five tiles compute automatically after upload — no button clicks:

1. **Revenue Forecast** — Linear regression on monthly trend, projects next month's revenue
2. **Churn Risk** — Count of Dormant-tier customers as a % of total customer base
3. **Champion Customers** — Count of top-tier customers and their % of the base
4. **Repeat Revenue Share** — % of total net revenue coming from repeat customers
5. **Best Margin Channel** — The sales channel with the highest profit margin %

---

## Automated Email Intelligence

### Monday 8AM Briefing
Every Monday at 8AM (Africa/Lagos timezone), NEXUS Retail sends a formatted HTML email
to all configured recipients. The email includes:
- Full KPI summary table (revenue, profit, margin, return rate, RVI)
- Up to 3 intelligence alerts (colour-coded by severity)
- AI-generated brief excerpt (first 300 characters of the Executive Brief)
- One priority recommended action
- Direct link to the live app

### Instant Anomaly Alerts
Three conditions trigger an immediate email regardless of day or time:
1. Return rate exceeds **10%** (absolute threshold)
2. Return rate increases by more than **2 percentage points** week-over-week
3. Any product category margin drops below **5%**
4. Profit Drain orders exceed **15%** of all orders

### Deployment Note
APScheduler runs as a background thread within the Streamlit process.
On Streamlit Community Cloud, apps go to sleep after ~20 minutes of inactivity,
which stops the scheduler. Solutions:
- Use [UptimeRobot](https://uptimerobot.com) (free) to ping your app URL every 10 minutes
- Use the **"Send Intelligence Email Now"** button on the Email Intelligence page for
  controlled delivery during the hackathon demo

---

## Deployment (Live URL for Judges)

```bash
git init
git add .
git commit -m "NEXUS Retail v2.0: Revenue Intelligence Operating System"
git remote add origin https://github.com/YOUR_USERNAME/nexus-retail.git
git push -u origin main
```

**Critical:** Ensure `.env` is in `.gitignore` — never push your API key.

Then:
1. Go to **share.streamlit.io**
2. Sign in with GitHub → click "New app"
3. Select your `nexus-retail` repo → main file: `app.py`
4. Click **Advanced → Secrets** → add all variables from your `.env`
5. Click **Deploy**

Your live URL: `https://nexus-retail-yourusername.streamlit.app`

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: mistralai` | Run `pip install -r requirements.txt` with venv active |
| `ModuleNotFoundError: apscheduler` | Run `pip install apscheduler` with venv active |
| `ModuleNotFoundError: sklearn` | Run `pip install scikit-learn` with venv active |
| `MISTRAL_API_KEY not found` | Check `.env` exists in same folder as `app.py`; format: `MISTRAL_API_KEY=sk-...` (no quotes, no spaces around `=`) |
| `SMTP Authentication Error` | Use Gmail **App Password**, not your main Gmail password |
| Email sends but arrives in spam | Add your sender address to recipients' contacts |
| `RVI returns None` | Dataset must have a `customer_id` column — check col_map output in terminal |
| Vitality page shows "RVI not computed" | Click "Run Full Analysis" again after upload |
| Streamlit Cloud deploy fails | Check `requirements.txt` is in root folder; check all Secrets are set |
| Charts not rendering on some pages | Verify `plotly` is installed: `pip show plotly` |
| Pylance shows red import warnings in VS Code | Press `Ctrl+Shift+P` → "Python: Select Interpreter" → choose the `venv` interpreter |

---

## Tech Stack

| Purpose | Tool |
|---------|------|
| Frontend/App | Streamlit |
| AI/LLM | Mistral AI (mistral-large-latest) |
| Predictive Model | scikit-learn LinearRegression |
| Visualisation | Plotly |
| PDF generation | fpdf2 |
| Excel export | openpyxl |
| Email scheduling | APScheduler |
| Data processing | pandas, numpy |
| Environment | Python 3.10+, virtualenv |

---

## Presentation Narrative

**Slide 1 — The Hook:**
*"Every Monday morning, the operations team opens a spreadsheet with 1,506 rows and asks:
'Are we making money?' After two hours, they still don't know. NEXUS Retail answers that in
4 seconds — and sends the answer to their inbox before they even open the laptop."*

**Slide 2 — The Problem (with numbers):**
₦68.5M net revenue. ₦13.5M profit. 19.6% margin. But 174 orders are generating negative
profit. 7.4% return rate. Q4 is 30.6% of annual revenue and nobody is watching.

**Slide 3 — The Two Derived Metrics:**
*"RRI tells you which orders are destroying profit right now. RVI tells you which customers
are about to walk away next month. Neither metric exists in the raw data. I engineered both.
Together they give you the complete picture: past performance and future risk — from a single
uploaded file."*

**Slide 4 — Live Demo:**
Upload the dataset → show alerts firing → drill into Customer Vitality → ask one question
via the Analyst → generate Executive Brief → show email configuration.

**Slide 5 — The Automated Layer:**
*"Every other submission waits for a manager to log in and check a dashboard on Monday
morning. NEXUS Retail does not wait. At 8AM every Monday, it emails every stakeholder a
formatted intelligence brief — KPIs, alerts, AI insights, and one recommended action —
before their first meeting starts. If an anomaly is detected mid-week, the email fires
immediately. The system is always watching."*

**Closing:**
*"Every other solution here shows you a chart of what happened last month. NEXUS Retail
tells you what is happening right now, which orders are destroying profit, which customers
are about to churn, and what to do before the next order comes in."*

---

*Built for 10Alytics Hack-AI-Thon 2.0 | Case A: Retail Sales & Customer Revenue Intelligence*
*#10ABHackAIThon*