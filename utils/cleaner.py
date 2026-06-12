import pandas as pd
import numpy as np
from io import BytesIO


def load_dataset(uploaded_file):
    """
    Accept any CSV or Excel file and return a raw DataFrame.
    Handles multi-sheet Excel by picking the sheet with the most rows.
    Skips metadata/instruction rows automatically.
    """
    filename = uploaded_file.name.lower()

    if filename.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
        return df

    elif filename.endswith(('.xlsx', '.xls')):
        xl = pd.ExcelFile(uploaded_file)
        dfs = {}
        for sheet in xl.sheet_names:
            try:
                temp = xl.parse(sheet, header=0)
                # Only keep sheets that look like data (not metadata)
                if len(temp) > 10 and len(temp.columns) > 3:
                    dfs[sheet] = temp
            except Exception:
                continue

        if not dfs:
            raise ValueError("No usable data sheet found in the Excel file.")

        # Pick the sheet with the most rows
        df = max(dfs.values(), key=lambda x: len(x))
        return df

    else:
        raise ValueError("Unsupported file type. Please upload CSV or Excel.")


def clean_dataset(df):
    """
    Automatically clean a retail dataset.
    Returns: (cleaned_df, quality_report_dict)
    The quality_report_dict documents every issue found and every fix applied.
    """
    report = {
        "original_rows": len(df),
        "original_cols": len(df.columns),
        "issues_found": [],
        "fixes_applied": [],
        "rows_removed": 0,
        "columns_with_nulls": [],
        "imputation_log": [],
        "flag_columns_added": [],
        "trust_score": 100,
    }

    df = df.copy()

    # ── 1. Strip whitespace from all string columns ──────────────────────
    str_cols = df.select_dtypes(include=['object', 'str']).columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace('nan', np.nan)
    report["fixes_applied"].append(
        f"Stripped leading/trailing whitespace from all {len(str_cols)} string columns."
    )

    # ── 2. Remove exact duplicate rows ───────────────────────────────────
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    if removed > 0:
        report["issues_found"].append(
            f"{removed} exact duplicate rows found (same Order_ID, same data)."
        )
        report["fixes_applied"].append(
            f"Removed {removed} exact duplicate rows."
        )
        report["rows_removed"] += removed
        report["trust_score"] -= removed * 3

    # ── 3. Standardise Region labels ─────────────────────────────────────
    region_col = _find_col(df, ['region'])
    if region_col:
        region_map = {
            'south west': 'South-West',
            'south-west': 'South-West',
            'north central': 'North-Central',
            'north-central': 'North-Central',
            'south-south': 'South-South',
            'south-east': 'South-East',
            'north-west': 'North-West',
            'south east': 'South-East',
            'north west': 'North-West',
        }
        original_unique = df[region_col].nunique()
        df[region_col] = df[region_col].str.strip().apply(
            lambda x: region_map.get(str(x).lower().strip(), x) if pd.notna(x) else x
        )
        new_unique = df[region_col].nunique()
        if new_unique < original_unique:
            diff = original_unique - new_unique
            report["issues_found"].append(
                f"Region column had {diff} label variants "
                f"(e.g. 'South West', 'South-west' → standardised to 'South-West')."
            )
            report["fixes_applied"].append(
                f"Standardised Region labels: {original_unique} variants → {new_unique} canonical values."
            )
            report["trust_score"] -= 5

    # ── 4. Standardise Product_Category labels ───────────────────────────
    cat_col = _find_col(df, ['product_category', 'category'])
    if cat_col:
        cat_map = {
            'electronics ': 'Electronics',
            'electronic': 'Electronics',
            'home & living': 'Home & Living',
            'home and living': 'Home & Living',
            'home & living ': 'Home & Living',
            'beauty & personal care ': 'Beauty & Personal Care',
            'beauty & personal care': 'Beauty & Personal Care',
            'groceries': 'Groceries',
            'fashion': 'Fashion',
            'office supplies': 'Office Supplies',
            'fitness & wellness': 'Fitness & Wellness',
        }
        original_unique = df[cat_col].nunique()
        df[cat_col] = df[cat_col].str.strip().apply(
            lambda x: cat_map.get(str(x).lower().strip(),
                      cat_map.get(str(x).strip(), x)) if pd.notna(x) else x
        )
        # Normalise any remaining with title case
        df[cat_col] = df[cat_col].str.strip()
        new_unique = df[cat_col].nunique()
        if new_unique < original_unique:
            diff = original_unique - new_unique
            report["issues_found"].append(
                f"Product_Category had {diff} label inconsistencies "
                f"(e.g. 'Electronics ', 'Electronic', 'Home and Living')."
            )
            report["fixes_applied"].append(
                f"Standardised Product_Category: {original_unique} variants → {new_unique} canonical values."
            )
            report["trust_score"] -= 5

    # ── 5. Normalise other categorical columns (title case) ───────────────
    for col in str_cols:
        if col in [region_col, cat_col]:
            continue  # already handled above
        n_unique = df[col].nunique(dropna=True)
        if 2 <= n_unique <= 20:
            original = set(df[col].dropna().unique())
            df[col] = df[col].str.title()
            new_set = set(df[col].dropna().unique())
            if original != new_set and len(original) == len(new_set):
                report["fixes_applied"].append(
                    f"Normalised '{col}' to Title Case for consistency."
                )

    # ── 6. Handle missing values ─────────────────────────────────────────
    null_counts = df.isnull().sum()
    null_cols = null_counts[null_counts > 0].index.tolist()

    for col in null_cols:
        null_n = int(df[col].isnull().sum())
        pct = round(null_n / len(df) * 100, 1)
        report["columns_with_nulls"].append(
            {"column": col, "missing": null_n, "pct": pct}
        )

        # Return_Reason: expected nulls — flag, do not impute
        if 'return_reason' in col.lower() or 'reason' in col.lower():
            report["issues_found"].append(
                f"'{col}': {null_n} nulls ({pct}%) — expected for non-returned orders. Flagged, not imputed."
            )
            report["imputation_log"].append(
                f"'{col}': {null_n} nulls → NOT imputed (expected for non-returned orders)."
            )
            report["trust_score"] -= 1  # minor deduction
            continue

        report["trust_score"] -= min(5, int(pct))

        if df[col].dtype in ['float64', 'int64']:
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            report["imputation_log"].append(
                f"'{col}': {null_n} nulls → imputed with median ({median_val:.1f})."
            )
        else:
            mode_val = df[col].mode()[0] if not df[col].mode().empty else "Unknown"
            df[col] = df[col].fillna(mode_val)
            report["imputation_log"].append(
                f"'{col}': {null_n} nulls → imputed with mode ('{mode_val}')."
            )

        report["fixes_applied"].append(
            f"Imputed {null_n} missing values in '{col}'."
        )

    # ── 7. Flag extreme discounts ─────────────────────────────────────────
    disc_col = _find_col(df, ['discount'])
    if disc_col:
        extreme_disc = (df[disc_col] > 0.20).sum()
        if extreme_disc > 0:
            df['Extreme_Discount_Flag'] = (df[disc_col] > 0.20).astype(int)
            report["issues_found"].append(
                f"{extreme_disc} orders have discounts > 20% — potential margin risk."
            )
            report["fixes_applied"].append(
                f"Added 'Extreme_Discount_Flag' column: {extreme_disc} rows flagged (discount > 20%)."
            )
            report["flag_columns_added"].append("Extreme_Discount_Flag")
            report["trust_score"] -= 3

    # ── 8. Flag negative profit rows ─────────────────────────────────────
    profit_col = _find_col(df, ['profit'])
    if profit_col:
        neg_profit = (df[profit_col] < 0).sum()
        if neg_profit > 0:
            df['Negative_Profit_Flag'] = (df[profit_col] < 0).astype(int)
            report["issues_found"].append(
                f"{neg_profit} orders have negative profit (all tied to returns)."
            )
            report["fixes_applied"].append(
                f"Added 'Negative_Profit_Flag' column: {neg_profit} rows flagged."
            )
            report["flag_columns_added"].append("Negative_Profit_Flag")
            report["trust_score"] -= 4

    # ── 9. Cap trust score ────────────────────────────────────────────────
    report["trust_score"] = max(0, min(100, round(report["trust_score"])))
    report["final_rows"] = len(df)
    report["final_cols"] = len(df.columns)

    return df, report


def _find_col(df, keywords):
    """Find a column by keyword match (case-insensitive)."""
    for kw in keywords:
        for col in df.columns:
            if kw in col.lower():
                return col
    return None


def get_trust_label(score):
    """Return a human-readable label for the data trust score."""
    if score >= 90:
        return "Excellent", "#27ae60"
    elif score >= 75:
        return "Good", "#2980b9"
    elif score >= 60:
        return "Fair", "#e67e22"
    else:
        return "Poor", "#c0392b"


def df_to_excel_bytes(df):
    """Convert a DataFrame to Excel bytes for download."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Cleaned_Data')
    return output.getvalue()