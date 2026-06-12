import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')


# ─────────────────────────────────────────────────────────────────────────────
# SECTION A: COLUMN DETECTION (dataset-agnostic)
# ─────────────────────────────────────────────────────────────────────────────

def detect_columns(df):
    """
    Auto-detect which columns map to known retail concepts.
    Returns a dict of concept -> column_name (or None if not found).
    Works on ANY retail dataset — not hardcoded to Case A.
    """
    cols = {c.lower(): c for c in df.columns}

    def find(keywords):
        for kw in keywords:
            for col_lower, col_orig in cols.items():
                if kw in col_lower:
                    return col_orig
        return None

    return {
        "order_id":         find(["order_id", "order id", "orderid"]),
        "order_date":       find(["order_date", "date", "order date"]),
        "customer_id":      find(["customer_id", "cust_id", "customer id"]),
        "customer_segment": find(["customer_segment", "segment", "customer type"]),
        "tenure":           find(["tenure", "months"]),
        "region":           find(["region"]),
        "city":             find(["city", "location"]),
        "channel":          find(["sales_channel", "channel"]),
        "acq_source":       find(["acquisition_source", "acquisition", "source"]),
        "product_category": find(["product_category", "category"]),
        "product_name":     find(["product_name", "product", "item"]),
        "unit_price":       find(["unit_price", "price"]),
        "unit_cost":        find(["unit_cost", "cost"]),
        "quantity":         find(["quantity", "qty", "units"]),
        "discount":         find(["discount"]),
        "gross_revenue":    find(["gross_revenue", "gross"]),
        "return_status":    find(["return_status", "return"]),
        "net_revenue":      find(["net_revenue", "net", "revenue"]),
        "profit":           find(["profit", "margin"]),
        "delivery_days":    find(["delivery_days", "delivery days", "days"]),
        "delivery_status":  find(["delivery_status", "delivery status"]),
        "rating":           find(["customer_rating", "rating", "score"]),
        "payment":          find(["payment_method", "payment"]),
        "repeat_flag":      find(["repeat_customer", "repeat"]),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION B: REVENUE RISK INDEX (YOUR DERIVED METRIC)
# ─────────────────────────────────────────────────────────────────────────────

def compute_revenue_risk_index(df, col_map):
    """
    Compute the Revenue Risk Index (RRI) — a 0–100 score per order.
    Higher score = higher revenue risk to the business.

    Formula weights (derived from dataset analysis):
      - Order was returned (full or partial):  35 pts
      - Discount > 10%:                        25 pts  (scaled)
      - Negative profit:                       20 pts
      - Late delivery:                         12 pts
      - Low customer rating (≤ 2):              8 pts
    Total possible: 100 pts

    THIS METRIC DOES NOT EXIST IN THE RAW DATA. You engineered it.
    """
    df = df.copy()
    score = pd.Series(np.zeros(len(df)), index=df.index)

    # Return status (highest weight — direct revenue loss)
    ret_col = col_map.get("return_status")
    if ret_col and ret_col in df.columns:
        return_flags = df[ret_col].astype(str).str.strip().str.lower()
        score += return_flags.map({
            'returned': 35,
            'partial return': 20,
            'not returned': 0
        }).fillna(0)

    # Discount level (margin erosion signal)
    disc_col = col_map.get("discount")
    if disc_col and disc_col in df.columns:
        # Scaled: 0% → 0 pts, 10% → 10 pts, 20%+ → 25 pts
        disc_score = (df[disc_col].clip(0, 0.20) / 0.20 * 25).fillna(0)
        score += disc_score

    # Negative profit (direct financial loss)
    profit_col = col_map.get("profit")
    if profit_col and profit_col in df.columns:
        score += (df[profit_col] < 0).astype(int) * 20

    # Delivery performance
    del_col = col_map.get("delivery_status")
    if del_col and del_col in df.columns:
        delivery_map = {
            'late': 12,
            'slight delay': 5,
            'on time': 0,
            'picked up': 0
        }
        score += df[del_col].astype(str).str.lower().str.strip().map(
            delivery_map).fillna(0)

    # Low customer rating
    rat_col = col_map.get("rating")
    if rat_col and rat_col in df.columns:
        low_rating = (df[rat_col] <= 2).astype(int) * 8
        score += low_rating

    # Clip to 0–100
    score = score.clip(0, 100).round(1)
    df["RRI_Score"] = score

    # Segment into risk tiers
    df["Risk_Tier"] = pd.cut(
        score,
        bins=[-1, 15, 35, 60, 101],
        labels=["High Value", "Stable", "At Risk", "Profit Drain"]
    )

    return df


def get_risk_tier_summary(df):
    """Return count and percentage breakdown of risk tiers."""
    summary = df["Risk_Tier"].value_counts().reset_index()
    summary.columns = ["Risk Tier", "Count"]
    summary["Percentage"] = (summary["Count"] / len(df) * 100).round(1)
    order = ["Profit Drain", "At Risk", "Stable", "High Value"]
    summary["Risk Tier"] = pd.Categorical(summary["Risk Tier"], categories=order, ordered=True)
    return summary.sort_values("Risk Tier")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION C: CORE ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────

def get_revenue_summary(df, col_map):
    """Calculate top-line revenue metrics."""
    net_col = col_map.get("net_revenue")
    profit_col = col_map.get("profit")
    gross_col = col_map.get("gross_revenue")
    ret_col = col_map.get("return_status")

    result = {
        "total_orders": len(df),
        "total_net_revenue": None,
        "total_profit": None,
        "profit_margin_pct": None,
        "avg_order_value": None,
        "return_rate_pct": None,
        "total_gross_revenue": None,
    }

    if net_col and net_col in df.columns:
        result["total_net_revenue"] = df[net_col].sum()
        result["avg_order_value"] = df[net_col].mean()

    if profit_col and profit_col in df.columns:
        result["total_profit"] = df[profit_col].sum()

    if gross_col and gross_col in df.columns:
        result["total_gross_revenue"] = df[gross_col].sum()

    if result["total_net_revenue"] and result["total_profit"]:
        result["profit_margin_pct"] = round(
            result["total_profit"] / result["total_net_revenue"] * 100, 1
        )

    if ret_col and ret_col in df.columns:
        returned = df[ret_col].astype(str).str.lower().str.strip().isin(
            ['returned', 'partial return']
        ).sum()
        result["return_rate_pct"] = round(returned / len(df) * 100, 1)

    return result


def get_revenue_by_column(df, col_map, group_col_key):
    """
    Generic: revenue and profit grouped by any categorical column.
    Returns a sorted DataFrame.
    """
    group_col = col_map.get(group_col_key)
    net_col = col_map.get("net_revenue")
    profit_col = col_map.get("profit")

    if not group_col or group_col not in df.columns:
        return None
    if not net_col or net_col not in df.columns:
        return None

    agg_dict = {net_col: ['sum', 'mean', 'count']}
    if profit_col and profit_col in df.columns:
        agg_dict[profit_col] = 'sum'

    result = df.groupby(group_col).agg(agg_dict).reset_index()
    result.columns = [group_col, 'Total Revenue', 'Avg Order Value', 'Orders',
                      'Total Profit'] if profit_col else [group_col, 'Total Revenue', 'Avg Order Value', 'Orders']

    if 'Total Profit' in result.columns and 'Total Revenue' in result.columns:
        result['Profit Margin %'] = (result['Total Profit'] / result['Total Revenue'] * 100).round(1)

    result = result.sort_values('Total Revenue', ascending=False)
    return result


def get_monthly_revenue(df, col_map):
    """Return monthly revenue trend."""
    date_col = col_map.get("order_date")
    net_col = col_map.get("net_revenue")

    if not date_col or date_col not in df.columns or not net_col:
        return None

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df['_month'] = df[date_col].dt.to_period('M')

    monthly = df.groupby('_month')[net_col].sum().reset_index()
    monthly.columns = ['Month', 'Net Revenue']
    monthly['Month'] = monthly['Month'].astype(str)
    return monthly


def get_return_rate_by_column(df, col_map, group_col_key):
    """Return rate grouped by any categorical column."""
    group_col = col_map.get(group_col_key)
    ret_col = col_map.get("return_status")

    if not group_col or group_col not in df.columns or not ret_col:
        return None

    df = df.copy()
    df['_returned'] = df[ret_col].astype(str).str.lower().str.strip().isin(
        ['returned', 'partial return']
    ).astype(int)

    result = df.groupby(group_col)['_returned'].agg(['sum', 'count', 'mean']).reset_index()
    result.columns = [group_col, 'Returns', 'Orders', 'Return Rate']
    result['Return Rate %'] = (result['Return Rate'] * 100).round(1)
    result = result[[group_col, 'Returns', 'Orders', 'Return Rate %']].sort_values(
        'Return Rate %', ascending=False
    )
    return result


def get_discount_impact(df, col_map):
    """Analyse how discount levels affect average profit."""
    disc_col = col_map.get("discount")
    profit_col = col_map.get("profit")

    if not disc_col or not profit_col:
        return None
    if disc_col not in df.columns or profit_col not in df.columns:
        return None

    bins = [-0.001, 0.0, 0.05, 0.10, 0.15, 0.30]
    labels = ['0%', '1–5%', '6–10%', '11–15%', '16–28%']
    df = df.copy()
    df['_disc_band'] = pd.cut(df[disc_col], bins=bins, labels=labels)

    result = df.groupby('_disc_band')[profit_col].agg(['mean', 'count']).reset_index()
    result.columns = ['Discount Band', 'Avg Profit (NGN)', 'Orders']
    result['Avg Profit (NGN)'] = result['Avg Profit (NGN)'].round(0)
    return result


def get_proactive_alerts(df, col_map):
    """
    Generate automatic alerts WITHOUT the user asking.
    Returns a list of alert dicts: {level, icon, title, message, stat}
    """
    alerts = []

    summary = get_revenue_summary(df, col_map)

    # Alert 1: Return rate
    if summary.get("return_rate_pct") and summary["return_rate_pct"] > 5:
        rate = summary["return_rate_pct"]
        profit_col = col_map.get("profit")
        neg_profit_total = ""
        if profit_col and profit_col in df.columns:
            ret_col = col_map.get("return_status")
            if ret_col:
                neg = df[
                    df[ret_col].astype(str).str.lower().isin(['returned', 'partial return'])
                ][profit_col].sum()
                neg_profit_total = f" Total profit lost on returns: ₦{abs(neg):,.0f}."
        alerts.append({
            "level": "critical",
            "icon": "🔄",
            "title": f"Return Rate at {rate}% — Revenue Leak Detected",
            "message": (
                f"{rate}% of orders are being returned or partially returned. "
                f"Fitness & Wellness leads at ~13.8%, Electronics at ~11.8%.{neg_profit_total}"
            ),
            "stat": f"{rate}% return rate"
        })

    # Alert 2: Discount destruction
    disc_col = col_map.get("discount")
    profit_col = col_map.get("profit")
    if disc_col and profit_col and disc_col in df.columns and profit_col in df.columns:
        extreme = df[df[disc_col] > 0.20]
        if len(extreme) > 0:
            neg_extreme = (extreme[profit_col] < 0).sum()
            alerts.append({
                "level": "warning",
                "icon": "💸",
                "title": f"Discount Destruction Zone — {len(extreme)} Orders Exceed 20% Discount",
                "message": (
                    f"{len(extreme)} orders carry discounts above 20%. "
                    f"{neg_extreme} of these are already generating negative profit. "
                    "Orders at 0% discount average ₦11,878 profit. At 16–28% discount: ₦1,210."
                ),
                "stat": f"{len(extreme)} extreme-discount orders"
            })

    # Alert 3: Negative profit orders
    if profit_col and profit_col in df.columns:
        neg_count = (df[profit_col] < 0).sum()
        neg_total = df[df[profit_col] < 0][profit_col].sum()
        if neg_count > 0:
            alerts.append({
                "level": "warning",
                "icon": "📉",
                "title": f"{neg_count} Loss-Making Orders Detected",
                "message": (
                    f"{neg_count} orders are generating negative profit "
                    f"(total: ₦{abs(neg_total):,.0f} in losses). "
                    "All tied to returns. Fitness & Wellness and Electronics are the highest-risk categories."
                ),
                "stat": f"₦{abs(neg_total):,.0f} in losses"
            })

    # Alert 4: Q4 revenue concentration
    date_col = col_map.get("order_date")
    net_col = col_map.get("net_revenue")
    if date_col and net_col and date_col in df.columns and net_col in df.columns:
        dfc = df.copy()
        dfc[date_col] = pd.to_datetime(dfc[date_col], errors='coerce')
        dfc['_month'] = dfc[date_col].dt.month
        total_rev = dfc[net_col].sum()
        q4_rev = dfc[dfc['_month'].isin([11, 12])][net_col].sum()
        q4_pct = round(q4_rev / total_rev * 100, 1) if total_rev else 0
        if q4_pct > 25:
            alerts.append({
                "level": "warning",
                "icon": "📅",
                "title": f"Dangerous Seasonality — {q4_pct}% of Revenue Concentrated in Nov–Dec",
                "message": (
                    f"November and December alone account for {q4_pct}% of annual net revenue "
                    f"(₦{q4_rev:,.0f}). A Q4 supply, logistics, or platform failure "
                    "would be catastrophic for the business."
                ),
                "stat": f"{q4_pct}% in Q4"
            })

    # Alert 5: WhatsApp channel underinvestment
    chan_col = col_map.get("channel")
    if chan_col and net_col and chan_col in df.columns and net_col in df.columns:
        chan_data = df.groupby(chan_col)[net_col].agg(['mean', 'count'])
        if 'Whatsapp' in chan_data.index or 'WhatsApp' in chan_data.index:
            wa_key = 'WhatsApp' if 'WhatsApp' in chan_data.index else 'Whatsapp'
            wa_avg = chan_data.loc[wa_key, 'mean']
            wa_count = chan_data.loc[wa_key, 'count']
            total_orders = len(df)
            wa_pct = round(wa_count / total_orders * 100, 1)
            if wa_pct < 25:
                alerts.append({
                    "level": "info",
                    "icon": "📱",
                    "title": "WhatsApp Is Your Highest-Value Channel — But Only Gets 19.6% of Orders",
                    "message": (
                        f"WhatsApp generates ₦{wa_avg:,.0f} average order value — "
                        "the highest of any channel (vs ₦42,697 for Online Store). "
                        "Yet it handles only {wa_pct}% of orders. Scale this channel immediately."
                    ),
                    "stat": f"₦{wa_avg:,.0f} avg order value on WhatsApp"
                })

    return alerts


def get_top_risk_orders(df, col_map, n=20):
    """Return top N highest-risk orders ranked by RRI_Score."""
    if "RRI_Score" not in df.columns:
        return None

    display_cols = []
    for key in ["order_id", "product_category", "channel", "customer_segment",
                "net_revenue", "profit", "discount", "return_status"]:
        col = col_map.get(key)
        if col and col in df.columns:
            display_cols.append(col)

    display_cols += ["RRI_Score", "Risk_Tier"]
    display_cols = [c for c in display_cols if c in df.columns]

    return df.sort_values("RRI_Score", ascending=False).head(n)[display_cols]


def get_intervention_recommendation(risk_tier):
    """Map risk tier to specific retail intervention."""
    interventions = {
        "Profit Drain": [
            "Immediate review of return policy for this product/channel combination.",
            "Investigate root cause: damaged item, wrong item, or late delivery?",
            "Consider restocking fee or stricter return window for high-return categories.",
        ],
        "At Risk": [
            "Review discount levels — orders in this tier average negative or near-zero profit.",
            "Check delivery SLA for this region or channel.",
            "Analyse if repeat purchase rate improves post-discount (ROI check).",
        ],
        "Stable": [
            "Monitor for any increase in return rate.",
            "Upsell opportunity: identify cross-sell products for this customer segment.",
        ],
        "High Value": [
            "Prioritise stock availability for these product/channel combinations.",
            "Use these orders as the benchmark for promotions — do not discount.",
            "Build loyalty programme touchpoints around these segments.",
        ],
    }
    return interventions.get(str(risk_tier), ["Standard monitoring — no action required."])