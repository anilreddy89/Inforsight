"""Configuration constants and paths for the Inforsight Conservation Intelligence Dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

# Base Paths
ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE_PATH = ROOT_DIR / "docs" / "experiments" / "phase-02-10-model-bundle.json"
DEFAULT_AUDIT_LOG_PATH = ROOT_DIR / "data" / "audit" / "conservation-audit-log.jsonl"
DEFAULT_MONITORING_SCHEMA = ROOT_DIR / "serving" / "monitoring" / "diagnostics-schema.json"

# Operational Capacity Defaults
DEFAULT_MAX_SPECIALIST_HOURS = 50.0
DEFAULT_BUDGET = 2500.00


class RiskTierDisplay(NamedTuple):
    label: str
    short_label: str
    color_hex: str
    bg_hex: str
    description: str


RISK_TIERS = {
    "Tier 4: Critical Risk": RiskTierDisplay(
        label="Tier 4: Critical Risk (Top 1%)",
        short_label="Tier 4 (Critical)",
        color_hex="#DC2626",
        bg_hex="#FEE2E2",
        description="Immediate specialist review required. Imminent combined termination risk.",
    ),
    "Tier 3: High Risk": RiskTierDisplay(
        label="Tier 3: High Risk (Top 5%)",
        short_label="Tier 3 (Elevated)",
        color_hex="#EA580C",
        bg_hex="#FFEDD5",
        description="Structured payment restructuring or dedicated outreach. Grace period critical.",
    ),
    "Tier 2: Moderate Risk": RiskTierDisplay(
        label="Tier 2: Moderate Risk (Top 20%)",
        short_label="Tier 2 (Moderate)",
        color_hex="#CA8A04",
        bg_hex="#FEF9C3",
        description="Digital self-service portal link and automated notification nudges.",
    ),
    "Tier 1: Low Risk": RiskTierDisplay(
        label="Tier 1: Low Risk (Baseline)",
        short_label="Tier 1 (Normal)",
        color_hex="#16A34A",
        bg_hex="#DCFCE7",
        description="Standard operational servicing. Proactive outreach not indicated.",
    ),
}

# Action Taxonomy Metadata
ACTION_METADATA = {
    "courtesy_reminder": {
        "title": "Courtesy Reminder",
        "icon": "📱",
        "channel": "SMS",
        "description": "Send a bounded courtesy reminder through the permitted channel.",
    },
    "grace_period_consultation": {
        "title": "Grace Period Consultation",
        "icon": "☎️",
        "channel": "PHONE",
        "description": "Provide a structured consultation while the policy is in grace.",
    },
    "specialist_phone_outreach": {
        "title": "Specialist Phone Consultation",
        "icon": "📞",
        "channel": "PHONE",
        "description": "High-touch empathetic phone consultation by a certified retention specialist.",
    },
    "payment_method_remediation": {
        "title": "Payment Method Remediation",
        "icon": "💳",
        "channel": "SMS",
        "description": "Offer a bounded payment-method correction path through the permitted channel.",
    },
    "abstain": {
        "title": "Abstain / No Intervention",
        "icon": "⏸️",
        "channel": "none",
        "description": "Decline active outreach to conserve resources and avoid customer fatigue.",
    },
}

# Standard Override Rationale Codes
OVERRIDE_RATIONALE_CODES = [
    ("OVERRIDE_SPECIALIST_DISCRETION_PREMIUM_DISPUTE", "Customer expressed active premium or billing dispute"),
    ("OVERRIDE_PREFERRED_CHANNEL_PHONE", "Customer historical preference indicates high responsiveness to phone"),
    ("OVERRIDE_PREFERRED_CHANNEL_DIGITAL", "Customer opted out of voice calls; digital self-service requested"),
    ("OVERRIDE_TEMPORARY_FINANCIAL_HARDSHIP", "Specialist verified documented short-term cash-flow hardship"),
    ("OVERRIDE_VIP_SERVICING_ESCALATION", "High cumulative face value / tenure policyholder requiring agent care"),
    ("OVERRIDE_OPERATIONAL_CAPACITY_CONSTRAINTS", "Specialist capacity allocated to higher immediate risk accounts"),
]

# Standard Rejection Rationale Codes
REJECT_RATIONALE_CODES = [
    ("REJECT_CUSTOMER_REQUESTED_NO_CONTACT", "Policyholder explicitly requested no proactive contact"),
    ("REJECT_POLICY_REPLACED_EXTERNALLY", "Confirmed policy replacement or external transfer"),
    ("REJECT_DECEASED_OR_INSOLVENT", "Notification of death or formal bankruptcy proceeding"),
    ("REJECT_DUPLICATE_OR_RECENT_CONTACT", "Successful contact completed within past 14 days"),
    ("REJECT_INSUFFICIENT_PRESERVED_UTILITY", "Specialist assessed cost exceeds realistic retained value"),
]
