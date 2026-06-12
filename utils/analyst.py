import os
import httpx
from dotenv import load_dotenv
import pandas as pd

load_dotenv()


def _call_mistral(messages, max_tokens=800, temperature=0.3):
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY not found. Check your .env file.")
    response = httpx.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "mistral-large-latest",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        timeout=90,          # raised from 60 — large briefs take longer
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def build_dataset_context(df, col_map, analytics_summary):
    parts = []
    parts.append(f"DATASET: {len(df)} orders, {list(df.columns)}")

    net_col    = col_map.get("net_revenue")
    profit_col = col_map.get("profit")

    if net_col and net_col in df.columns:
        total_rev = df[net_col].sum()
        avg_order = df[net_col].mean()
        parts.append(
            f"REVENUE: Total net revenue = NGN {total_rev:,.0f} | "
            f"Avg order = NGN {avg_order:,.0f}"
        )

    if profit_col and profit_col in df.columns:
        total_profit = df[profit_col].sum()
        margin = (
            total_profit / df[net_col].sum() * 100
            if net_col and net_col in df.columns and df[net_col].sum() > 0
            else None
        )
        parts.append(
            f"PROFIT: Total = NGN {total_profit:,.0f} | Margin = {margin:.1f}%"
            if margin is not None
            else f"PROFIT: NGN {total_profit:,.0f}"
        )

    ret_col = col_map.get("return_status")
    if ret_col and ret_col in df.columns:
        ret_rate = (
            df[ret_col].astype(str).str.lower()
            .isin(["returned", "partial return"])
            .mean() * 100
        )
        parts.append(f"RETURN RATE: {ret_rate:.1f}%")

    chan_col = col_map.get("channel")
    if chan_col and chan_col in df.columns and net_col and net_col in df.columns:
        top_chan = (
            df.groupby(chan_col)[net_col]
            .mean()
            .sort_values(ascending=False)
        )
        parts.append(f"CHANNEL AVG ORDER VALUE: {dict(top_chan.round(0))}")

    if "RRI_Score" in df.columns and "Risk_Tier" in df.columns:
        tier_counts = df["Risk_Tier"].value_counts().to_dict()
        avg_rri = round(df["RRI_Score"].mean(), 1)
        parts.append(
            f"REVENUE RISK INDEX: Average RRI = {avg_rri}/100 | "
            f"Tier distribution: {tier_counts}"
        )

    seg_col = col_map.get("customer_segment")
    if seg_col and seg_col in df.columns and net_col and net_col in df.columns:
        seg_rev = (
            df.groupby(seg_col)[net_col]
            .agg(["sum", "mean", "count"])
            .sort_values("sum", ascending=False)
        )
        parts.append(f"SEGMENT REVENUE: {seg_rev.to_dict()}")

    if analytics_summary:
        parts.append(f"ADDITIONAL ANALYTICS: {analytics_summary}")

    return "\n".join(parts)


def ask_analyst(question, df, col_map, analytics_summary="", chat_history=None):
    """
    Send a question to Mistral with full dataset context.
    Returns: (answer_text, updated_chat_history)
    """
    dataset_context = build_dataset_context(df, col_map, analytics_summary)

    system_prompt = f"""You are NEXUS Retail Analyst — an expert retail intelligence assistant.

You have been given a live retail dataset with the following profile:
{dataset_context}

Your role:
- Answer questions about THIS specific dataset and retail business
- Give actionable, specific recommendations tied to the numbers above
- Think like a senior retail consultant for a growing Nigerian business
- Reference the NGN figures, channel names, product categories from the data
- Be concise but substantive — 2-4 paragraphs maximum
- Always end with ONE specific recommended action

NEVER say "I don't have access to the data" — the full data profile is above.
NEVER give generic advice — tie everything to the specific numbers you have been given.
"""

    if chat_history is None:
        chat_history = []

    messages = [{"role": "system", "content": system_prompt}]
    messages += chat_history
    messages.append({"role": "user", "content": question})

    answer = _call_mistral(messages, max_tokens=800, temperature=0.3)

    chat_history.append({"role": "user",      "content": question})
    chat_history.append({"role": "assistant", "content": answer})
    return answer, chat_history


def generate_executive_brief(df, col_map, prompt):
    """
    Generate executive brief from a fully-formed prompt passed by app.py.
    max_tokens raised to 2500 so all 5 sections render completely.
    """
    return _call_mistral(
        [{"role": "user", "content": prompt}],
        max_tokens=2500,     # was 700 / 1000 — needs room for 550-700 word brief
        temperature=0.2,
    )