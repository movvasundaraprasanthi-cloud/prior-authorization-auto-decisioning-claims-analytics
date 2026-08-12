from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "dashboards" / "screenshots" / "executive_dashboard_preview.png"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def main() -> None:
    score = pd.read_csv(BASE / "data" / "exports" / "executive_scorecard.csv").iloc[0]
    perf = pd.read_csv(BASE / "data" / "exports" / "powerbi_client_monthly_performance.csv")
    client_rank = (
        perf.groupby("client_name", as_index=False)
        .agg(
            auto_decision_rate=("auto_decision_rate", "mean"),
            denial_rate=("denial_rate", "mean"),
            client_value_opportunity=("client_value_opportunity", "sum"),
        )
        .sort_values("client_value_opportunity", ascending=False)
    )

    img = Image.new("RGB", (1600, 900), "#f8fafb")
    d = ImageDraw.Draw(img)
    navy = "#12343B"
    teal = "#2D6A6F"
    gold = "#F2C14E"
    ink = "#20272b"
    muted = "#5f6c72"

    d.rectangle([0, 0, 1600, 118], fill=navy)
    d.text((54, 28), "Prior Authorization Auto-Decisioning & Claims Value Analytics", fill="white", font=font(38, True))
    d.text((56, 78), "Cohere-style Healthcare Analyst II project | SQL | Power BI-ready KPIs | claims + authorization data", fill="#d9f0f2", font=font(20))

    cards = [
        ("Authorizations", f"{int(score.authorization_volume):,}"),
        ("Claims", f"{int(score.claim_volume):,}"),
        ("Auto-Decision Rate", f"{score.auto_decision_rate:.2f}%"),
        ("SLA Met Rate", f"{score.decision_sla_met_rate:.2f}%"),
        ("Denied Amount", f"${score.denied_amount/1_000_000:.2f}M"),
    ]
    x = 54
    for label, value in cards:
        d.rounded_rectangle([x, 148, x + 280, 268], radius=8, fill="white", outline="#dbe3e6", width=2)
        d.text((x + 22, 170), label, fill=muted, font=font(18))
        d.text((x + 22, 204), value, fill=navy, font=font(34, True))
        x += 300

    d.rounded_rectangle([54, 310, 760, 790], radius=8, fill="white", outline="#dbe3e6", width=2)
    d.text((84, 338), "Client Value Opportunity Ranking", fill=navy, font=font(26, True))
    max_val = client_rank["client_value_opportunity"].max()
    y = 392
    for r in client_rank.itertuples():
        bar_w = int(520 * r.client_value_opportunity / max_val)
        d.text((84, y), r.client_name, fill=ink, font=font(19, True))
        d.text((84, y + 28), f"Auto {r.auto_decision_rate:.1%} | Denial {r.denial_rate:.1%}", fill=muted, font=font(16))
        d.rounded_rectangle([84, y + 58, 84 + bar_w, y + 84], radius=5, fill=teal)
        d.text((620, y + 56), f"${r.client_value_opportunity:,.0f}", fill=ink, font=font(17, True))
        y += 96

    d.rounded_rectangle([820, 310, 1546, 790], radius=8, fill="white", outline="#dbe3e6", width=2)
    d.text((850, 338), "Optimization Recommendation", fill=navy, font=font(26, True))
    recommendation = [
        "Move clean, policy-matched requests",
        "from nurse review to auto-decision",
        "while preserving clinical safeguards.",
    ]
    y = 398
    for line in recommendation:
        d.text((850, y), line, fill=ink, font=font(28, True))
        y += 40
    d.rounded_rectangle([850, 540, 1508, 640], radius=8, fill="#fff7df", outline=gold, width=2)
    d.text((880, 560), "Avoidable manual reviews identified", fill=muted, font=font(20))
    d.text((880, 590), f"{int(score.avoidable_manual_reviews):,}", fill=navy, font=font(34, True))
    d.rounded_rectangle([850, 665, 1508, 740], radius=8, fill="#eaf4f4", outline=teal, width=2)
    d.text((880, 686), f"Estimated admin savings: ${score.estimated_auto_decision_admin_savings:,.0f}", fill=navy, font=font(24, True))

    d.text((54, 838), "Generated from synthetic data. No PHI, PII, patient, payer, or real provider data included.", fill=muted, font=font(16))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
