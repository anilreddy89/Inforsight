"""Visualization and charting utilities for the conservation dashboard."""

from __future__ import annotations

from typing import Any, Mapping, Sequence
import matplotlib.pyplot as plt
import pandas as pd

from dashboard.config import ACTION_METADATA, RISK_TIERS


def plot_shap_waterfall(
    root_attributions: Mapping[str, float],
    base_value_logit: float,
    calibrated_logit: float,
    max_features: int = 8,
) -> plt.Figure:
    """Renders a clean horizontal waterfall attribution chart matching Phase 2.09."""
    sorted_features = sorted(root_attributions.items(), key=lambda x: abs(x[1]), reverse=True)
    top_features = sorted_features[:max_features]

    # Calculate "other" features sum if truncated
    other_sum = sum(val for _, val in sorted_features[max_features:])
    items_to_plot = list(reversed(top_features))
    if abs(other_sum) > 1e-4:
        items_to_plot.insert(0, ("other_features_combined", other_sum))

    names = [k.replace("_", " ").title() for k, _ in items_to_plot]
    values = [v for _, v in items_to_plot]
    colors = ["#EF4444" if v > 0 else "#10B981" for v in values]

    fig, ax = plt.subplots(figsize=(8, max(4.0, len(names) * 0.45)), dpi=150)
    bars = ax.barh(names, values, color=colors, height=0.6, alpha=0.9, edgecolor="none")

    ax.axvline(0, color="#64748B", linestyle="--", linewidth=1.0, alpha=0.7)
    ax.set_xlabel("Impact on Log-Odds of Lapse (Δ logit)", fontsize=10, fontweight="normal", color="#334155")
    ax.set_title(
        f"Feature Attributions (Base Logit: {base_value_logit:.2f} → Score: {calibrated_logit:.2f})",
        fontsize=11,
        fontweight="bold",
        color="#1E293B",
        pad=12,
    )

    # Label bars with numerical values
    for bar, val in zip(bars, values):
        x_pos = val + (0.015 if val >= 0 else -0.015)
        ha = "left" if val >= 0 else "right"
        ax.text(
            x_pos,
            bar.get_y() + bar.get_height() / 2,
            f"{val:+.3f}",
            va="center",
            ha=ha,
            fontsize=8.5,
            fontweight="bold",
            color="#334155",
        )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E1")
    ax.spines["bottom"].set_color("#CBD5E1")
    ax.tick_params(colors="#475569", labelsize=9)
    fig.tight_layout()
    return fig


def plot_risk_distribution(tier_counts: Mapping[str, int]) -> plt.Figure:
    """Renders a donut chart illustrating portfolio risk distribution across tiers."""
    labels = []
    sizes = []
    colors = []

    for tier_key, meta in RISK_TIERS.items():
        count = tier_counts.get(tier_key, 0)
        labels.append(f"{meta.short_label}\n({count:,})")
        sizes.append(count)
        colors.append(meta.color_hex)

    fig, ax = plt.subplots(figsize=(5, 5), dpi=150)
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        pctdistance=0.75,
        startangle=140,
        colors=colors,
        wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2),
    )
    plt.setp(texts, size=8.5, color="#1E293B", weight="normal")
    plt.setp(autotexts, size=8.5, weight="bold", color="white")
    ax.set_title("Portfolio Risk Tiers", fontsize=11, fontweight="bold", color="#1E293B", pad=10)
    fig.tight_layout()
    return fig


def plot_intervention_mix(action_counts: Mapping[str, int]) -> plt.Figure:
    """Renders a horizontal bar chart displaying the optimal intervention distribution."""
    action_items = []
    for action_key, count in action_counts.items():
        meta = ACTION_METADATA.get(action_key, {"title": action_key.replace("_", " ").title(), "icon": "•"})
        action_items.append((meta['title'], count))

    # Sort descending
    action_items.sort(key=lambda x: x[1])
    titles = [x[0] for x in action_items]
    counts = [x[1] for x in action_items]

    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=150)
    palette = ["#94A3B8", "#38BDF8", "#818CF8", "#A78BFA", "#34D399"]
    bars = ax.barh(titles, counts, color=palette[:len(counts)], height=0.55, edgecolor="none")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E1")
    ax.spines["bottom"].set_color("#CBD5E1")
    ax.tick_params(colors="#475569", labelsize=8.5)
    ax.set_xlabel("Policy Count", fontsize=9, fontweight="normal", color="#334155")
    ax.set_title("Optimal Intervention Mix", fontsize=11, fontweight="bold", color="#1E293B", pad=10)

    for bar, val in zip(bars, counts):
        ax.text(
            val + (max(counts) * 0.02 if counts else 1),
            bar.get_y() + bar.get_height() / 2,
            f"{val:,}",
            va="center",
            ha="left",
            fontsize=8.5,
            fontweight="bold",
            color="#334155",
        )

    fig.tight_layout()
    return fig
