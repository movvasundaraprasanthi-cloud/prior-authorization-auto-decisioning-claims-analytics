-- Cohere-Style Healthcare Analyst II Portfolio Project
-- Prior authorization auto-decisioning, claims outcomes, cost/utilization, KPI reporting, and rule refinement.

-- 1. Client monthly performance scorecard
WITH auth_base AS (
    SELECT
        client_id,
        request_month,
        authorization_id,
        decision_source,
        decision_outcome,
        decision_hours,
        target_decision_sla_hours,
        clinical_policy_match_flag,
        documentation_complete_flag,
        member_eligibility_flag,
        client_request_cost,
        estimated_admin_cost,
        CASE WHEN decision_source = 'Auto Decision' THEN 1 ELSE 0 END AS auto_decision_flag,
        CASE WHEN decision_hours <= target_decision_sla_hours THEN 1 ELSE 0 END AS decision_sla_met_flag,
        CASE
            WHEN decision_source IN ('Nurse Review', 'Medical Director')
             AND clinical_policy_match_flag = 1
             AND documentation_complete_flag = 1
             AND member_eligibility_flag = 1
            THEN 1 ELSE 0
        END AS avoidable_manual_review_flag
    FROM authorization_detail_scored
),
claims_base AS (
    SELECT
        client_id,
        claim_month,
        claim_id,
        claim_status,
        allowed_amount,
        paid_amount,
        denied_amount,
        denial_reason
    FROM claims_detail_enriched
)
SELECT
    a.client_id,
    a.request_month,
    COUNT(DISTINCT a.authorization_id) AS authorization_volume,
    ROUND(100.0 * SUM(a.auto_decision_flag) / COUNT(*), 2) AS auto_decision_rate,
    ROUND(100.0 * SUM(a.decision_sla_met_flag) / COUNT(*), 2) AS decision_sla_met_rate,
    SUM(a.avoidable_manual_review_flag) AS avoidable_manual_reviews,
    ROUND(AVG(a.decision_hours), 2) AS avg_decision_hours,
    COUNT(DISTINCT c.claim_id) AS claim_volume,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) / NULLIF(COUNT(c.claim_id), 0), 2) AS denial_rate,
    SUM(c.denied_amount) AS denied_amount,
    SUM(a.auto_decision_flag) * (24.50 - 4.75) AS estimated_auto_decision_admin_savings
FROM auth_base a
LEFT JOIN claims_base c
    ON a.client_id = c.client_id
   AND a.request_month = c.claim_month
GROUP BY a.client_id, a.request_month
ORDER BY a.client_id, a.request_month;

-- 2. Rule refinement opportunity by service category
WITH service_performance AS (
    SELECT
        service_category,
        COUNT(*) AS authorization_volume,
        AVG(CASE WHEN decision_source = 'Auto Decision' THEN 1.0 ELSE 0.0 END) AS auto_decision_rate,
        AVG(CASE WHEN clinical_policy_match_flag = 1 THEN 1.0 ELSE 0.0 END) AS policy_match_rate,
        AVG(CASE WHEN documentation_complete_flag = 1 THEN 1.0 ELSE 0.0 END) AS documentation_complete_rate,
        AVG(decision_hours) AS avg_decision_hours,
        SUM(CASE
            WHEN decision_source IN ('Nurse Review', 'Medical Director')
             AND clinical_policy_match_flag = 1
             AND documentation_complete_flag = 1
             AND member_eligibility_flag = 1
            THEN 1 ELSE 0
        END) AS avoidable_manual_reviews
    FROM authorization_detail_scored
    GROUP BY service_category
)
SELECT
    service_category,
    authorization_volume,
    ROUND(auto_decision_rate * 100, 2) AS auto_decision_rate,
    ROUND(policy_match_rate * 100, 2) AS policy_match_rate,
    ROUND(documentation_complete_rate * 100, 2) AS documentation_complete_rate,
    ROUND(avg_decision_hours, 2) AS avg_decision_hours,
    avoidable_manual_reviews,
    CASE
        WHEN avoidable_manual_reviews >= 500 AND policy_match_rate >= 0.70 THEN 'Tune auto-decision threshold'
        WHEN documentation_complete_rate < 0.78 THEN 'Add documentation prompt'
        WHEN auto_decision_rate < 0.40 THEN 'Review clinical policy logic'
        ELSE 'Monitor'
    END AS recommended_action
FROM service_performance
ORDER BY avoidable_manual_reviews DESC;

-- 3. Claims outcome analysis by decision path
SELECT
    decision_source,
    service_category,
    COUNT(*) AS claim_volume,
    ROUND(100.0 * SUM(CASE WHEN claim_status = 'Denied' THEN 1 ELSE 0 END) / COUNT(*), 2) AS denial_rate,
    SUM(denied_amount) AS denied_amount,
    SUM(paid_amount) AS paid_amount,
    ROUND(SUM(paid_amount) / NULLIF(SUM(allowed_amount), 0), 4) AS paid_to_allowed_ratio
FROM claims_detail_enriched
GROUP BY decision_source, service_category
ORDER BY denied_amount DESC;

-- 4. Client-facing KPI exception list
SELECT
    client_id,
    request_month,
    authorization_volume,
    ROUND(auto_decision_rate * 100, 2) AS auto_decision_rate,
    ROUND(sla_met_rate * 100, 2) AS sla_met_rate,
    ROUND(denial_rate * 100, 2) AS denial_rate,
    client_value_opportunity,
    CASE
        WHEN auto_decision_rate < 0.45 THEN 'Below auto-decision target'
        WHEN sla_met_rate < 0.80 THEN 'SLA risk'
        WHEN denial_rate > 0.20 THEN 'Claims denial risk'
        ELSE 'On track'
    END AS executive_status
FROM powerbi_client_monthly_performance
WHERE auto_decision_rate < 0.45
   OR sla_met_rate < 0.80
   OR denial_rate > 0.20
ORDER BY client_value_opportunity DESC;
