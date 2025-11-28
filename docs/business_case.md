# RoleFit Analyzer — Business Case

Executive Summary
-----------------
RoleFit Analyzer automates and standardizes CV screening while producing evidence-based, auditable decisions recruiters can rely on — decreasing time-to-hire, reducing bias, and improving candidate-job fit.

Problem
-------
- Manual screening is time-consuming and inconsistent.
- Existing AI tools often lack an audit trail or evidence for claims.
- Scalability during hiring spikes is expensive.

Opportunity
-----------
- Save recruiter time, improve quality of hire, and provide explainable outputs.

Solution
--------
RoleFit Analyzer extracts resume and JD text, stores them in session memory, and uses evidence-only `search_memory` to return structured JSON screening and matching decisions with exact supporting snippets.

Key Benefits
------------
- Faster initial screening (automation of triage)
- Evidence-backed decisions to reduce legal/explainability risk
- Seamless ATS integration (JSON outputs)

KPIs
----
- Time-saved per CV
- Reduction in Time-to-Fill
- Accuracy vs manual decisions
- % of claims with evidence

Pilot Plan (6-8 weeks)
----------------------
- Weeks 1–2: Pilot Setup
- Weeks 3–5: Controlled trial
- Weeks 6–8: Integration & Governance

Readiness
---------
- Sample `adk web` environment available
- Scripts for validation: `scripts/validate_results.py` and `scripts/run_test.py`

Next steps
----------
- Run pilot for a single job family
- Integrate `talent_matching_result` outputs into ATS workflow
- Set up audit logs and governance for production rollout

Contact
-------
For a pilot or integration support, reach out to the engineering team.
