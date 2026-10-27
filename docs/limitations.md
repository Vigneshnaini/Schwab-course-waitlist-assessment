# Limitations and Follow-up Risks

- The service stores all data in memory. Restarting the application clears enrollment and waitlist state.
- The implementation supports one course offering only, as required by the assessment scope.
- The service is designed for a single-process demonstration and does not provide transaction handling or locking for concurrent requests.
- Prerequisite eligibility is represented by a Boolean input. A production system would integrate with an authoritative academic-records source.
- The API has no authentication or authorization. A production system would verify the caller and enforce access controls.
- Learner IDs are treated as case-sensitive strings. A production system would use validated, canonical learner identifiers.
- The service has no audit log, persistence, observability, or administrative workflow.