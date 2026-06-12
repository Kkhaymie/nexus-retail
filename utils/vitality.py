import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')


# ─────────────────────────────────────────────────────────────────────────────
# SECTION A: COLUMN DETECTION (re-uses intelligence.py detect_columns logic)
# ─────────────────────────────────────────────────────────────────────────────

def _find_col(df, keywords):
    """Find a column by keyword match (case-insensitive). Same helper as cleaner.py."""
    for kw in keywords:
        for col in df.columns:
            if kw in col.lower():
                return col
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SECTION B: ACQUISITION SOURCE QUALITY SCORER
# ─────────────────────────────────────────────────────────────────────────────

def _score_acquisition_source(source_str):
    """
    Map acquisition source to a quality score (0–10).
    Dataset-agnostic: uses keyword matching, not hardcoded values.
    """
    if pd.isna(source_str):
        return 2
    s = str(source_str).lower().strip()
    if any(k in s for k in ['referral', 'organic', 'google']):
        return 10
    if any(k in s for k in ['social', 'instagram', 'facebook', 'twitter', 'tiktok']):
        return 6
    if any(k in s for k in ['email', 'newsletter', 'campaign']):
        return 6
    if any(k in s for k in ['whatsapp', 'direct', 'chat']):
        return 8
    if any(k in s for k in ['paid', 'ad', 'ppc', 'cpc']):
        return 4
    return 2


# ─────────────────────────────────────────────────────────────────────────────
# SECTION C: COMPUTE THE RETAIL VITALITY INDEX (PER CUSTOMER)
# ─────────────────────────────────────────────────────────────────────────────

def compute_retail_vitality_index(df, col_map):
    """
    Compute the Retail Vitality Index (RVI) — a 0–100 score per CUSTOMER.
    Higher score = healthier, more valuable customer relationship.

    This metric does not exist in the raw data. It is engineered from 5 signals.

    Returns: DataFrame at customer level with RVI_Score and Vitality_Tier columns.
    Works on ANY retail dataset through col_map column detection.
    """
    cust_col   = col_map.get("customer_id")
    seg_col    = col_map.get("customer_segment")
    net_col    = col_map.get("net_revenue")
    ret_col    = col_map.get("return_status")
    rep_col    = col_map.get("repeat_flag")
    acq_col    = col_map.get("acq_source")
    tenure_col = col_map.get("tenure")

    if not cust_col or cust_col not in df.columns:
        return None

    df = df.copy()

    # ── Build customer-level aggregation ────────────────────────────────────
    agg_dict = {}

    if net_col and net_col in df.columns:
        agg_dict[net_col] = ['sum', 'mean', 'count']

    if ret_col and ret_col in df.columns:
        df['_returned'] = df[ret_col].astype(str).str.lower().str.strip().isin(
            ['returned', 'partial return']
        ).astype(int)
        agg_dict['_returned'] = 'sum'

    if rep_col and rep_col in df.columns:
        df['_repeat'] = df[rep_col].astype(str).str.lower().str.strip().isin(
            ['yes', 'true', '1', 'repeat']
        ).astype(int)
        agg_dict['_repeat'] = 'max'

    if acq_col and acq_col in df.columns:
        agg_dict[acq_col] = 'first'

    if tenure_col and tenure_col in df.columns:
        agg_dict[tenure_col] = 'first'

    if seg_col and seg_col in df.columns:
        agg_dict[seg_col] = 'first'

    if not agg_dict:
        return None

    cust_df = df.groupby(cust_col).agg(agg_dict).reset_index()

    # Flatten multi-level columns
    flat_cols = [cust_col]
    for col, func in agg_dict.items():
        if isinstance(func, list):
            for f in func:
                flat_cols.append(f"{col}_{f}")
        else:
            flat_cols.append(col)
    cust_df.columns = flat_cols

    # ── Signal 1: Repeat purchase behaviour (30 pts) ────────────────────────
    order_count_col = f"{net_col}_count" if net_col else None
    repeat_score = pd.Series(np.zeros(len(cust_df)), index=cust_df.index)

    if '_repeat' in cust_df.columns:
        repeat_score += cust_df['_repeat'] * 30
    elif order_count_col and order_count_col in cust_df.columns:
        # If no explicit repeat flag, use order count > 1 as proxy
        repeat_score += (cust_df[order_count_col] > 1).astype(int) * 30

    # ── Signal 2: AOV vs segment median (25 pts) ────────────────────────────
    aov_col = f"{net_col}_mean" if net_col else None
    aov_score = pd.Series(np.zeros(len(cust_df)), index=cust_df.index)

    if aov_col and aov_col in cust_df.columns:
        seg_col_flat = seg_col if seg_col in cust_df.columns else None
        if seg_col_flat:
            seg_medians = cust_df.groupby(seg_col_flat)[aov_col].transform('median')
            ratio = (cust_df[aov_col] / seg_medians.replace(0, np.nan)).fillna(1)
        else:
            overall_median = cust_df[aov_col].median()
            ratio = (cust_df[aov_col] / overall_median if overall_median > 0 else 1)
        # Cap at 2× median = full 25 pts
        aov_score = (ratio.clip(0, 2) / 2 * 25).fillna(0)

    # ── Signal 3: Customer tenure (20 pts) ──────────────────────────────────
    tenure_score = pd.Series(np.zeros(len(cust_df)), index=cust_df.index)
    tenure_col_flat = tenure_col if tenure_col in cust_df.columns else None

    if tenure_col_flat:
        max_tenure = cust_df[tenure_col_flat].max()
        if max_tenure and max_tenure > 0:
            tenure_score = (cust_df[tenure_col_flat] / max_tenure * 20).fillna(0)
    elif order_count_col and order_count_col in cust_df.columns:
        # Proxy: order count as tenure signal if no tenure column
        max_orders = cust_df[order_count_col].max()
        if max_orders > 0:
            tenure_score = (cust_df[order_count_col] / max_orders * 20).fillna(0)

    # ── Signal 4: Return rate for this customer (15 pts) ────────────────────
    return_score = pd.Series(np.full(len(cust_df), 15.0), index=cust_df.index)

    if '_returned' in cust_df.columns and order_count_col and order_count_col in cust_df.columns:
        cust_return_rate = (
            cust_df['_returned'] / cust_df[order_count_col].replace(0, np.nan)
        ).fillna(0)
        # 0% returns = 15 pts; 100% returns = 0 pts
        return_score = ((1 - cust_return_rate) * 15).clip(0, 15)

    # ── Signal 5: Acquisition source quality (10 pts) ───────────────────────
    acq_score = pd.Series(np.zeros(len(cust_df)), index=cust_df.index)
    acq_col_flat = acq_col if acq_col in cust_df.columns else None

    if acq_col_flat:
        acq_score = cust_df[acq_col_flat].apply(_score_acquisition_source)

    # ── Combine and clip ─────────────────────────────────────────────────────
    rvi = (repeat_score + aov_score + tenure_score + return_score + acq_score)
    rvi = rvi.clip(0, 100).round(1)
    cust_df['RVI_Score'] = rvi

    # ── Vitality segments ────────────────────────────────────────────────────
    cust_df['Vitality_Tier'] = pd.cut(
        rvi,
        bins=[-1, 24, 49, 74, 101],
        labels=['Dormant', 'Developing', 'Loyal', 'Champion']
    )

    return cust_df


# ─────────────────────────────────────────────────────────────────────────────
# SECTION D: VITALITY ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────

def get_vitality_tier_summary(cust_df):
    """Return count and percentage breakdown of vitality tiers."""
    summary = cust_df['Vitality_Tier'].value_counts().reset_index()
    summary.columns = ['Vitality Tier', 'Customers']
    summary['Percentage'] = (summary['Customers'] / len(cust_df) * 100).round(1)
    order = ['Champion', 'Loyal', 'Developing', 'Dormant']
    summary['Vitality Tier'] = pd.Categorical(
        summary['Vitality Tier'], categories=order
    )
    return summary.sort_values('Vitality Tier')


def get_champion_customers(cust_df, n=10):
    """Return top N Champion customers ranked by RVI_Score."""
    if 'RVI_Score' not in cust_df.columns:
        return None
    return cust_df[cust_df['Vitality_Tier'] == 'Champion'].sort_values(
        'RVI_Score', ascending=False
    ).head(n)


def get_dormant_customers(cust_df, n=10):
    """Return top N Dormant customers — highest churn risk."""
    if 'RVI_Score' not in cust_df.columns:
        return None
    return cust_df[cust_df['Vitality_Tier'] == 'Dormant'].sort_values(
        'RVI_Score', ascending=True
    ).head(n)


def get_avg_rvi_by_segment(cust_df, seg_col):
    """Return average RVI score broken down by customer segment."""
    if seg_col not in cust_df.columns or 'RVI_Score' not in cust_df.columns:
        return None
    result = cust_df.groupby(seg_col)['RVI_Score'].agg(
        ['mean', 'count', 'std']
    ).reset_index()
    result.columns = [seg_col, 'Avg RVI', 'Customers', 'RVI Std Dev']
    result['Avg RVI'] = result['Avg RVI'].round(1)
    return result.sort_values('Avg RVI', ascending=False)


def get_vitality_intervention(tier):
    """Map vitality tier to specific retention/growth intervention."""
    interventions = {
        'Champion': [
            "Protect: prioritise stock availability and delivery SLA for these customers.",
            "Reward: create an exclusive early-access or VIP programme for this tier.",
            "Leverage: these are your most credible referral sources — activate them.",
            "Do NOT discount: they are already paying full price willingly.",
        ],
        'Loyal': [
            "Upsell: identify the one product category they have not bought yet.",
            "Frequency nudge: if last order > 45 days ago, send a personalised restock prompt.",
            "Protect margin: offer loyalty points over discounts to maintain AOV.",
        ],
        'Developing': [
            "Second purchase trigger: the move from 1 to 2 orders is the most critical conversion.",
            "Category discovery: show them the category with the highest margin, not the most popular.",
            "Survey: find out what stopped them from reordering — one question, one channel.",
        ],
        'Dormant': [
            "Re-engagement campaign: time-limited offer tied to their first purchase category.",
            "Root cause check: were they a high-return customer? Address the product issue first.",
            "Accept some churn: not every Dormant customer is worth re-acquiring — segment by AOV.",
        ],
    }
    return interventions.get(str(tier), ["Standard monitoring."])