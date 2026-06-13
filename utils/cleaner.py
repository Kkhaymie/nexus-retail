import pandas as pd
import numpy as np
from io import BytesIO


def load_dataset(uploaded_file):
    filename = uploaded_file.name.lower()

    if filename.endswith('.csv'):
        return pd.read_csv(uploaded_file)

    elif filename.endswith(('.xlsx', '.xls')):
        engine = 'xlrd' if filename.endswith('.xls') else 'openpyxl'
        xl = pd.ExcelFile(uploaded_file, engine=engine)
        dfs = {}
        for sheet in xl.sheet_names:
            try:
                temp = xl.parse(sheet, header=0)
                if len(temp) > 10 and len(temp.columns) > 3:
                    dfs[sheet] = temp
            except Exception:
                continue
        if not dfs:
            raise ValueError("No usable data sheet found in the Excel file.")
        return max(dfs.values(), key=lambda x: len(x))

    else:
        raise ValueError("Unsupported file type. Please upload CSV or Excel.")


def clean_dataset(df):
    report = {
        "original_rows":       len(df),
        "original_cols":       len(df.columns),
        "issues_found":        [],
        "fixes_applied":       [],
        "rows_removed":        0,
        "columns_with_nulls":  [],
        "imputation_log":      [],
        "flag_columns_added":  [],
        "trust_score":         100,
        # detailed breakdown for transparency
        "_score_log":          [],
    }

    df = df.copy()

    def _deduct(pts, reason):
        report["trust_score"]  -= pts
        report["_score_log"].append(f"-{pts}  {reason}")

    def _recover(pts, reason):
        report["trust_score"]  += pts
        report["_score_log"].append(f"+{pts}  {reason}")

    # ── 1. Strip whitespace ──────────────────────────────────────────────
    str_cols = df.select_dtypes(include=['object', 'str']).columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace('nan', np.nan)
    report["fixes_applied"].append(
        f"Stripped whitespace from {len(str_cols)} string columns.")

    # ── 2. Duplicates ────────────────────────────────────────────────────
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    report["rows_removed"] += removed
    if removed > 0:
        # Penalise once for having duplicates, not per-row
        # Scale: 1-5 rows = -2, 6-20 = -5, 21+ = -10
        penalty = 2 if removed <= 5 else 5 if removed <= 20 else 10
        _deduct(penalty, f"{removed} duplicate rows found and removed")
        report["issues_found"].append(
            f"{removed} exact duplicate rows found (same Order_ID, same data).")
        report["fixes_applied"].append(f"Removed {removed} exact duplicate rows.")

    # ── 3. Region labels ─────────────────────────────────────────────────
    region_col = _find_col(df, ['region'])
    if region_col:
        region_map = {
            'south west':    'South-West',  'south-west':    'South-West',
            'north central': 'North-Central','north-central': 'North-Central',
            'south-south':   'South-South',  'south-east':    'South-East',
            'north-west':    'North-West',   'south east':    'South-East',
            'north west':    'North-West',
        }
        original_unique = df[region_col].nunique()
        df[region_col] = df[region_col].str.strip().apply(
            lambda x: region_map.get(str(x).lower().strip(), x) if pd.notna(x) else x)
        new_unique = df[region_col].nunique()
        if new_unique < original_unique:
            diff = original_unique - new_unique
            # Deduct 3 for having the issue, then recover 2 because we fixed it
            _deduct(3, f"Region had {diff} label variants")
            _recover(2, "Region labels standardised automatically")
            report["issues_found"].append(
                f"Region column had {diff} label variants — standardised to canonical form.")
            report["fixes_applied"].append(
                f"Standardised Region: {original_unique} variants → {new_unique} values.")

    # ── 4. Product_Category labels ───────────────────────────────────────
    cat_col = _find_col(df, ['product_category', 'category'])
    if cat_col:
        cat_map = {
            'electronics ':            'Electronics',
            'electronic':              'Electronics',
            'home & living':           'Home & Living',
            'home and living':         'Home & Living',
            'home & living ':          'Home & Living',
            'beauty & personal care ': 'Beauty & Personal Care',
            'beauty & personal care':  'Beauty & Personal Care',
            'groceries':               'Groceries',
            'fashion':                 'Fashion',
            'office supplies':         'Office Supplies',
            'fitness & wellness':      'Fitness & Wellness',
        }
        original_unique = df[cat_col].nunique()
        df[cat_col] = df[cat_col].str.strip().apply(
            lambda x: cat_map.get(str(x).lower().strip(),
                      cat_map.get(str(x).strip(), x)) if pd.notna(x) else x)
        df[cat_col] = df[cat_col].str.strip()
        new_unique = df[cat_col].nunique()
        if new_unique < original_unique:
            diff = original_unique - new_unique
            _deduct(3, f"Product_Category had {diff} label inconsistencies")
            _recover(2, "Product_Category labels standardised automatically")
            report["issues_found"].append(
                f"Product_Category had {diff} label inconsistencies — standardised.")
            report["fixes_applied"].append(
                f"Standardised Product_Category: {original_unique} → {new_unique} values.")

    # ── 5. Normalise other categoricals (title case) ─────────────────────
    for col in str_cols:
        if col in [region_col, cat_col]:
            continue
        n_unique = df[col].nunique(dropna=True)
        if 2 <= n_unique <= 20:
            original = set(df[col].dropna().unique())
            df[col] = df[col].str.title()
            new_set = set(df[col].dropna().unique())
            if original != new_set and len(original) == len(new_set):
                report["fixes_applied"].append(
                    f"Normalised '{col}' to Title Case.")

    # ── 6. Missing values ────────────────────────────────────────────────
    null_counts = df.isnull().sum()
    null_cols   = null_counts[null_counts > 0].index.tolist()

    for col in null_cols:
        null_n = int(df[col].isnull().sum())
        pct    = round(null_n / len(df) * 100, 1)
        report["columns_with_nulls"].append(
            {"column": col, "missing": null_n, "pct": pct})

        # Return_Reason: expected nulls — no score penalty
        if 'return_reason' in col.lower() or 'reason' in col.lower():
            report["issues_found"].append(
                f"'{col}': {null_n} nulls ({pct}%) — expected for non-returned orders. Flagged, not imputed.")
            report["imputation_log"].append(
                f"'{col}': {null_n} nulls → NOT imputed (expected for non-returned orders).")
            continue  # no deduction

        # Penalise only significant gaps: <1% = 0pts, 1-5% = -1, 5-15% = -2, >15% = -3
        if pct < 1:
            penalty = 0
        elif pct < 5:
            penalty = 1
        elif pct < 15:
            penalty = 2
        else:
            penalty = 3

        if penalty > 0:
            _deduct(penalty, f"'{col}' had {null_n} missing values ({pct}%)")

        # Impute
        if df[col].dtype in ['float64', 'int64']:
            median_val = df[col].median()
            df[col]    = df[col].fillna(median_val)
            report["imputation_log"].append(
                f"'{col}': {null_n} nulls → imputed with median ({median_val:.1f}).")
        else:
            mode_val = df[col].mode()[0] if not df[col].mode().empty else "Unknown"
            df[col]  = df[col].fillna(mode_val)
            report["imputation_log"].append(
                f"'{col}': {null_n} nulls → imputed with mode ('{mode_val}').")

        # Partial recovery for successful imputation
        if penalty > 0:
            _recover(max(1, penalty - 1), f"'{col}' nulls successfully imputed")

        report["fixes_applied"].append(
            f"Imputed {null_n} missing values in '{col}'.")

    # ── 7. Flag extreme discounts (business signal, NOT a data quality issue)
    disc_col = _find_col(df, ['discount'])
    if disc_col:
        extreme_disc = (df[disc_col] > 0.20).sum()
        if extreme_disc > 0:
            df['Extreme_Discount_Flag'] = (df[disc_col] > 0.20).astype(int)
            # Noted as a business insight — zero score penalty
            report["issues_found"].append(
                f"{extreme_disc} orders have discounts > 20% — flagged for margin analysis.")
            report["fixes_applied"].append(
                f"Added 'Extreme_Discount_Flag': {extreme_disc} rows flagged.")
            report["flag_columns_added"].append("Extreme_Discount_Flag")

    # ── 8. Flag negative profit (business signal, NOT a data quality issue)
    profit_col = _find_col(df, ['profit'])
    if profit_col:
        neg_profit = (df[profit_col] < 0).sum()
        if neg_profit > 0:
            df['Negative_Profit_Flag'] = (df[profit_col] < 0).astype(int)
            # Noted as a business insight — zero score penalty
            report["issues_found"].append(
                f"{neg_profit} orders have negative profit (all tied to returns).")
            report["fixes_applied"].append(
                f"Added 'Negative_Profit_Flag': {neg_profit} rows flagged.")
            report["flag_columns_added"].append("Negative_Profit_Flag")

    # ── 9. Cap and finalise ───────────────────────────────────────────────
    report["trust_score"] = max(0, min(100, round(report["trust_score"])))
    report["final_rows"]  = len(df)
    report["final_cols"]  = len(df.columns)

    return df, report


def _find_col(df, keywords):
    for kw in keywords:
        for col in df.columns:
            if kw in col.lower():
                return col
    return None


def get_trust_label(score):
    if score >= 90: return "Excellent", "#27ae60"
    elif score >= 80: return "Good",    "#2980b9"
    elif score >= 70: return "Fair",    "#e67e22"
    else:             return "Poor",    "#c0392b"


def df_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Cleaned_Data')
    return output.getvalue()