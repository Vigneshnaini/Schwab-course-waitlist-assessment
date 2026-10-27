# Limitations and Follow-up Risks

## Concurrency
- A single `threading.Lock` makes `enroll`, `drop`, and `get_status` atomic within one
  process. It does not protect multiple workers or processes, which would each hold
  separate state and locks. A database-backed version would need a transaction or
  row-level lock.
- The concurrency tests are regression guards, not proof of safety. CPython's GIL can
  hide a race even when the lock is removed.
- One coarse lock is adequate for one course offering but would not scale to many
  offerings.

## Data and persistence
- All data is held in memory. Restarting the application clears enrollment and
  waitlist state.
- There is no audit log, persistence, observability, or administrative workflow.

## Eligibility and identity
- Prerequisite eligibility is a caller-supplied Boolean. A production system would
  read it from an authoritative academic-records source.
- Eligibility is evaluated when a learner requests enrollment and never refreshed.
  The promotion-time re-check (skip and keep position) is therefore not reachable
  through the API today. It is covered only by unit tests that place an ineligible
  learner directly on the waitlist.
- Learner IDs are trimmed and treated as case-sensitive strings. A production system
  would use validated, canonical identifiers.
- The API has no authentication or authorization. A production system would verify
  the caller and enforce access controls.

## Functional scope
- The service manages one course offering only, as required by the assessment scope.
  The demo capacity of 2 is hard-coded in `app/main.py`.
- There is no operation for a waitlisted learner to leave the waitlist. `POST /drop`
  for a learner who is not enrolled returns `not_enrolled`.
- Promotion is not notified to the promoted learner; the response to `/drop` is the
  only signal.