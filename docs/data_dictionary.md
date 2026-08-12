# Data Dictionary

## authorization_requests.csv

| Field | Description |
|---|---|
| authorization_id | Synthetic prior authorization request identifier |
| client_id | Synthetic payer client |
| provider_id | Synthetic provider identifier |
| request_month | Month of authorization request |
| service_category | Clinical service category such as MSK, Radiology, Cardiology, GI, Sleep |
| request_channel | Intake path: Portal, Fax, API, Phone |
| decision_source | Auto Decision, Nurse Review, Medical Director, or Pended |
| decision_outcome | Approved, Denied, Partial Approval, or Pending |
| clinical_policy_match_flag | Whether request matched configured clinical policy logic |
| documentation_complete_flag | Whether required documentation was present |
| member_eligibility_flag | Whether member eligibility passed |
| decision_hours | Hours from request intake to decision |
| client_request_cost | Synthetic estimated cost associated with requested service |
| estimated_admin_cost | Synthetic administrative cost estimate for processing path |

## claims.csv

| Field | Description |
|---|---|
| claim_id | Synthetic claim identifier |
| authorization_id | Linked authorization request |
| claim_status | Paid, Denied, or Adjusted |
| denial_reason | Denial category when claim is denied |
| allowed_amount | Synthetic allowed claim amount |
| paid_amount | Synthetic paid claim amount |
| denied_amount | Synthetic denied claim amount |

## clinical_decision_rules.csv

| Field | Description |
|---|---|
| rule_id | Synthetic rule identifier |
| service_category | Clinical service category |
| rule_type | Policy Match, Documentation, Eligibility, Site of Care, Unit Limit |
| current_threshold | Current synthetic threshold setting |
| rule_precision | Synthetic precision proxy for rule performance |
| monthly_review_volume | Monthly volume affected by the rule |
| recommended_action | Tune threshold, keep, retire duplicate, or add documentation prompt |
