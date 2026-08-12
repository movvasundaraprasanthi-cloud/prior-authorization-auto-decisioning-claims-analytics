from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]


def test_executive_scorecard_has_required_kpis():
    scorecard = pd.read_csv(BASE / "data" / "exports" / "executive_scorecard.csv")
    required = {
        "authorization_volume",
        "claim_volume",
        "auto_decision_rate",
        "decision_sla_met_rate",
        "avoidable_manual_reviews",
        "claims_denial_rate",
        "denied_amount",
        "estimated_auto_decision_admin_savings",
        "client_value_opportunity",
    }
    assert required.issubset(scorecard.columns)


def test_powerbi_exports_are_not_empty():
    for file_name in ["powerbi_client_monthly_performance.csv", "powerbi_rule_refinement_tracker.csv"]:
        data = pd.read_csv(BASE / "data" / "exports" / file_name)
        assert len(data) > 0
