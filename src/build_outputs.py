from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
except Exception:  # Dashboard exports are helpful, but data outputs are the core artifact.
    plt = None


BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PROCESSED = BASE / "data" / "processed"
EXPORTS = BASE / "data" / "exports"
REPORTS = BASE / "reports"
SCREENSHOTS = BASE / "dashboards" / "screenshots"
RUN_DATE = pd.Timestamp("2026-08-01")


def ensure_dirs() -> None:
    for path in [RAW, PROCESSED, EXPORTS, REPORTS, SCREENSHOTS]:
        path.mkdir(parents=True, exist_ok=True)


def build_clients(rng: np.random.Generator) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "client_id": ["CHP_TX", "CHP_FL", "CHP_GA", "CHP_AZ"],
            "client_name": [
                "Central Health Plan Texas",
                "Atlantic Care Advantage",
                "Peach State Health",
                "Desert Valley Health",
            ],
            "line_of_business": ["Medicare Advantage", "Commercial", "Medicaid", "Exchange"],
            "implementation_wave": [1, 1, 2, 2],
            "target_auto_decision_rate": [58, 52, 49, 46],
            "target_decision_sla_hours": [24, 24, 36, 36],
        }
    )


def build_providers(rng: np.random.Generator, n: int = 720) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "provider_id": [f"PRV{100000 + i}" for i in range(n)],
            "specialty": rng.choice(
                ["Orthopedics", "Cardiology", "Radiology", "Physical Therapy", "Gastroenterology", "Sleep Medicine"],
                size=n,
                p=[0.2, 0.18, 0.22, 0.18, 0.12, 0.10],
            ),
            "state": rng.choice(["TX", "FL", "GA", "AZ", "NC", "OH"], size=n),
            "network_status": rng.choice(["In Network", "Out of Network", "Pending"], size=n, p=[0.78, 0.12, 0.10]),
            "credentialing_status": rng.choice(["Approved", "Pending", "Expired"], size=n, p=[0.74, 0.19, 0.07]),
            "risk_tier": rng.choice(["Low", "Medium", "High"], size=n, p=[0.54, 0.32, 0.14]),
        }
    )


def build_authorizations(rng: np.random.Generator, clients: pd.DataFrame, providers: pd.DataFrame, n: int = 18500) -> pd.DataFrame:
    auth = pd.DataFrame(
        {
            "authorization_id": [f"AUTH{200000 + i}" for i in range(n)],
            "client_id": rng.choice(clients["client_id"], size=n, p=[0.32, 0.26, 0.24, 0.18]),
            "provider_id": rng.choice(providers["provider_id"], size=n),
            "request_month": rng.choice(pd.period_range("2026-01", "2026-07", freq="M").astype(str), size=n),
            "service_category": rng.choice(
                ["MSK", "Cardiology", "Radiology", "Physical Therapy", "GI", "Sleep"],
                size=n,
                p=[0.22, 0.18, 0.24, 0.16, 0.11, 0.09],
            ),
            "request_channel": rng.choice(["Portal", "Fax", "API", "Phone"], size=n, p=[0.42, 0.25, 0.24, 0.09]),
            "decision_source": rng.choice(["Auto Decision", "Nurse Review", "Medical Director", "Pended"], size=n, p=[0.46, 0.29, 0.13, 0.12]),
            "clinical_policy_match_flag": rng.choice([0, 1], size=n, p=[0.28, 0.72]),
            "documentation_complete_flag": rng.choice([0, 1], size=n, p=[0.18, 0.82]),
            "member_eligibility_flag": rng.choice([0, 1], size=n, p=[0.07, 0.93]),
            "requested_units": rng.integers(1, 13, size=n),
        }
    )
    base_hours = rng.gamma(shape=2.1, scale=8.5, size=n)
    auth["decision_hours"] = np.where(auth["decision_source"].eq("Auto Decision"), base_hours * 0.28, base_hours * 1.35).round(1)
    auth["decision_outcome"] = np.select(
        [
            auth["decision_source"].eq("Pended"),
            auth["clinical_policy_match_flag"].eq(1) & auth["documentation_complete_flag"].eq(1),
            auth["clinical_policy_match_flag"].eq(0),
        ],
        ["Pending", "Approved", "Denied"],
        default="Partial Approval",
    )
    auth["client_request_cost"] = (
        rng.normal(940, 360, size=n).clip(120, 4200)
        * np.where(auth["service_category"].isin(["Cardiology", "Radiology"]), 1.35, 1.0)
    ).round(2)
    auth["estimated_admin_cost"] = np.where(auth["decision_source"].eq("Auto Decision"), 4.75, 24.5).round(2)
    return auth


def build_claims(rng: np.random.Generator, auth: pd.DataFrame, n: int = 28500) -> pd.DataFrame:
    sample = auth.sample(n=n, replace=True, random_state=2603).reset_index(drop=True)
    claims = pd.DataFrame(
        {
            "claim_id": [f"CLM{300000 + i}" for i in range(n)],
            "authorization_id": sample["authorization_id"],
            "client_id": sample["client_id"],
            "provider_id": sample["provider_id"],
            "service_category": sample["service_category"],
            "claim_month": sample["request_month"],
            "allowed_amount": (sample["client_request_cost"] * np.random.default_rng(77).uniform(0.62, 1.18, size=n)).round(2),
        }
    )
    auth_quality = sample["clinical_policy_match_flag"].eq(1) & sample["documentation_complete_flag"].eq(1)
    claims["claim_status"] = np.where(
        auth_quality,
        rng.choice(["Paid", "Denied", "Adjusted"], size=n, p=[0.82, 0.10, 0.08]),
        rng.choice(["Paid", "Denied", "Adjusted"], size=n, p=[0.55, 0.34, 0.11]),
    )
    claims["denial_reason"] = np.where(
        claims["claim_status"].eq("Denied"),
        rng.choice(
            ["Missing Documentation", "Medical Necessity", "Authorization Mismatch", "Eligibility", "Provider Credentialing"],
            size=n,
            p=[0.25, 0.27, 0.20, 0.15, 0.13],
        ),
        "None",
    )
    claims["paid_amount"] = np.where(claims["claim_status"].eq("Paid"), claims["allowed_amount"] * rng.uniform(0.74, 1.0, size=n), 0).round(2)
    claims["denied_amount"] = np.where(claims["claim_status"].eq("Denied"), claims["allowed_amount"], 0).round(2)
    return claims


def build_program_rules(rng: np.random.Generator) -> pd.DataFrame:
    rules = []
    for service in ["MSK", "Cardiology", "Radiology", "Physical Therapy", "GI", "Sleep"]:
        for rule_type in ["Policy Match", "Documentation", "Eligibility", "Site of Care", "Unit Limit"]:
            rules.append(
                {
                    "rule_id": f"{service[:3].upper()}_{rule_type.replace(' ', '_').upper()}",
                    "service_category": service,
                    "rule_type": rule_type,
                    "current_threshold": round(rng.uniform(0.62, 0.92), 2),
                    "rule_precision": round(rng.uniform(0.76, 0.95), 2),
                    "monthly_review_volume": int(rng.integers(180, 980)),
                    "recommended_action": rng.choice(["Tune threshold", "Keep", "Retire duplicate", "Add documentation prompt"], p=[0.38, 0.34, 0.08, 0.20]),
                }
            )
    return pd.DataFrame(rules)


def transform(auth: pd.DataFrame, claims: pd.DataFrame, clients: pd.DataFrame, providers: pd.DataFrame, rules: pd.DataFrame) -> dict[str, pd.DataFrame]:
    auth_enriched = auth.merge(clients, on="client_id", how="left").merge(providers, on="provider_id", how="left")
    auth_enriched["decision_sla_met_flag"] = (auth_enriched["decision_hours"] <= auth_enriched["target_decision_sla_hours"]).astype(int)
    auth_enriched["auto_decision_flag"] = auth_enriched["decision_source"].eq("Auto Decision").astype(int)
    auth_enriched["manual_review_flag"] = auth_enriched["decision_source"].isin(["Nurse Review", "Medical Director"]).astype(int)
    auth_enriched["avoidable_manual_review_flag"] = (
        auth_enriched["manual_review_flag"].eq(1)
        & auth_enriched["clinical_policy_match_flag"].eq(1)
        & auth_enriched["documentation_complete_flag"].eq(1)
        & auth_enriched["member_eligibility_flag"].eq(1)
    ).astype(int)

    claims_enriched = claims.merge(auth_enriched[["authorization_id", "decision_source", "auto_decision_flag", "clinical_policy_match_flag", "documentation_complete_flag"]], on="authorization_id", how="left")

    client_month = (
        auth_enriched.groupby(["client_id", "client_name", "line_of_business", "request_month"], as_index=False)
        .agg(
            authorization_volume=("authorization_id", "count"),
            auto_decisions=("auto_decision_flag", "sum"),
            avg_decision_hours=("decision_hours", "mean"),
            sla_met_rate=("decision_sla_met_flag", "mean"),
            avoidable_manual_reviews=("avoidable_manual_review_flag", "sum"),
            admin_cost=("estimated_admin_cost", "sum"),
            requested_cost=("client_request_cost", "sum"),
        )
    )
    client_month["auto_decision_rate"] = client_month["auto_decisions"] / client_month["authorization_volume"]
    client_month["avoidable_manual_review_rate"] = client_month["avoidable_manual_reviews"] / client_month["authorization_volume"]

    claims_month = (
        claims_enriched.groupby(["client_id", "claim_month"], as_index=False)
        .agg(
            claim_volume=("claim_id", "count"),
            denied_claims=("claim_status", lambda s: s.eq("Denied").sum()),
            denied_amount=("denied_amount", "sum"),
            allowed_amount=("allowed_amount", "sum"),
            paid_amount=("paid_amount", "sum"),
        )
    )
    claims_month["denial_rate"] = claims_month["denied_claims"] / claims_month["claim_volume"]

    program_performance = client_month.merge(
        claims_month,
        left_on=["client_id", "request_month"],
        right_on=["client_id", "claim_month"],
        how="left",
    )
    program_performance["estimated_auto_decision_admin_savings"] = (
        program_performance["auto_decisions"] * (24.5 - 4.75)
    ).round(2)
    program_performance["client_value_opportunity"] = (
        program_performance["avoidable_manual_reviews"] * 19.75
        + program_performance["denied_amount"].fillna(0) * 0.035
    ).round(2)

    rule_refinement = (
        auth_enriched.groupby(["service_category", "decision_source"], as_index=False)
        .agg(
            auth_volume=("authorization_id", "count"),
            policy_match_rate=("clinical_policy_match_flag", "mean"),
            documentation_complete_rate=("documentation_complete_flag", "mean"),
            avg_decision_hours=("decision_hours", "mean"),
            auto_decision_rate=("auto_decision_flag", "mean"),
            avoidable_manual_review_rate=("avoidable_manual_review_flag", "mean"),
        )
        .merge(rules.groupby("service_category", as_index=False).agg(review_volume=("monthly_review_volume", "sum")), on="service_category", how="left")
    )

    executive = pd.DataFrame(
        [
            {
                "authorization_volume": len(auth_enriched),
                "claim_volume": len(claims_enriched),
                "auto_decision_rate": round(auth_enriched["auto_decision_flag"].mean() * 100, 2),
                "decision_sla_met_rate": round(auth_enriched["decision_sla_met_flag"].mean() * 100, 2),
                "avoidable_manual_reviews": int(auth_enriched["avoidable_manual_review_flag"].sum()),
                "claims_denial_rate": round(claims_enriched["claim_status"].eq("Denied").mean() * 100, 2),
                "denied_amount": round(float(claims_enriched["denied_amount"].sum()), 2),
                "estimated_auto_decision_admin_savings": round(float(auth_enriched["auto_decision_flag"].sum() * (24.5 - 4.75)), 2),
                "client_value_opportunity": round(float(program_performance["client_value_opportunity"].sum()), 2),
                "top_optimization_theme": "Move clean, policy-matched requests from nurse review to auto-decision queue",
            }
        ]
    )

    return {
        "authorization_detail": auth_enriched,
        "claims_detail": claims_enriched,
        "client_monthly_performance": program_performance,
        "rule_refinement": rule_refinement,
        "executive_scorecard": executive,
    }


def write_reports(outputs: dict[str, pd.DataFrame]) -> None:
    score = outputs["executive_scorecard"].iloc[0].to_dict()
    top_clients = outputs["client_monthly_performance"].groupby("client_name", as_index=False).agg(
        auto_decision_rate=("auto_decision_rate", "mean"),
        denial_rate=("denial_rate", "mean"),
        client_value_opportunity=("client_value_opportunity", "sum"),
    ).sort_values("client_value_opportunity", ascending=False)
    top_client_md = "\n".join(
        f"- {r.client_name}: {r.auto_decision_rate:.1%} auto-decision rate, {r.denial_rate:.1%} denial rate, ${r.client_value_opportunity:,.0f} value opportunity"
        for r in top_clients.itertuples()
    )
    report = f"""# Executive Findings

## Six-Second Recruiter Summary

Built a Cohere-style healthcare analytics project analyzing prior authorization auto-decisioning, claims outcomes, clinical policy matching, cost/utilization trends, KPI performance, and rule-refinement opportunities across synthetic payer clients.

## Executive KPIs

- Authorization volume analyzed: {score['authorization_volume']:,}
- Claims volume analyzed: {score['claim_volume']:,}
- Auto-decision rate: {score['auto_decision_rate']}%
- Decision SLA met rate: {score['decision_sla_met_rate']}%
- Avoidable manual reviews identified: {score['avoidable_manual_reviews']:,}
- Claims denial rate: {score['claims_denial_rate']}%
- Denied amount reviewed: ${score['denied_amount']:,.2f}
- Estimated auto-decision admin savings: ${score['estimated_auto_decision_admin_savings']:,.2f}
- Client value opportunity: ${score['client_value_opportunity']:,.2f}

## Client Opportunity Ranking

{top_client_md}

## Recommendation

The strongest optimization opportunity is to shift clean, policy-matched, documentation-complete requests from manual nurse review into the auto-decision path while preserving clinical and compliance safeguards. This reduces administrative cost, improves turnaround time, and gives clients clearer performance reporting.
"""
    (REPORTS / "executive_findings.md").write_text(report)


def write_dashboard_screenshot(outputs: dict[str, pd.DataFrame]) -> None:
    if plt is None:
        return
    perf = outputs["client_monthly_performance"].copy()
    trend = perf.groupby("request_month", as_index=False).agg(
        auto_decision_rate=("auto_decision_rate", "mean"),
        denial_rate=("denial_rate", "mean"),
        value_opportunity=("client_value_opportunity", "sum"),
    )
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    fig.patch.set_facecolor("#f8fafb")
    axes[0].plot(trend["request_month"], trend["auto_decision_rate"] * 100, marker="o", color="#12343B", linewidth=2.5)
    axes[0].set_title("Auto-Decision Rate", fontweight="bold")
    axes[0].set_ylabel("%")
    axes[0].tick_params(axis="x", rotation=35)
    axes[1].bar(trend["request_month"], trend["denial_rate"] * 100, color="#2D6A6F")
    axes[1].set_title("Claims Denial Rate", fontweight="bold")
    axes[1].set_ylabel("%")
    axes[1].tick_params(axis="x", rotation=35)
    axes[2].bar(trend["request_month"], trend["value_opportunity"], color="#F2C14E")
    axes[2].set_title("Client Value Opportunity", fontweight="bold")
    axes[2].set_ylabel("$")
    axes[2].tick_params(axis="x", rotation=35)
    for ax in axes:
        ax.grid(axis="y", alpha=0.2)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Cohere-Style Prior Authorization Analytics Monitor", fontsize=16, fontweight="bold", color="#12343B")
    fig.tight_layout()
    fig.savefig(SCREENSHOTS / "executive_dashboard_preview.png", dpi=160)
    plt.close(fig)


def main() -> None:
    ensure_dirs()
    rng = np.random.default_rng(2603)
    clients = build_clients(rng)
    providers = build_providers(rng)
    auth = build_authorizations(rng, clients, providers)
    claims = build_claims(rng, auth)
    rules = build_program_rules(rng)

    for name, df in [
        ("clients", clients),
        ("providers", providers),
        ("authorization_requests", auth),
        ("claims", claims),
        ("clinical_decision_rules", rules),
    ]:
        df.to_csv(RAW / f"{name}.csv", index=False)

    outputs = transform(auth, claims, clients, providers, rules)
    outputs["authorization_detail"].to_csv(PROCESSED / "authorization_detail_scored.csv", index=False)
    outputs["claims_detail"].to_csv(PROCESSED / "claims_detail_enriched.csv", index=False)
    outputs["client_monthly_performance"].to_csv(EXPORTS / "powerbi_client_monthly_performance.csv", index=False)
    outputs["rule_refinement"].to_csv(EXPORTS / "powerbi_rule_refinement_tracker.csv", index=False)
    outputs["executive_scorecard"].to_csv(EXPORTS / "executive_scorecard.csv", index=False)

    write_reports(outputs)
    write_dashboard_screenshot(outputs)
    print(outputs["executive_scorecard"].to_string(index=False))


if __name__ == "__main__":
    main()
