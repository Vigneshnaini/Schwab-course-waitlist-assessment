# Design Specification

## Scope

This project implements enrollment, dropping, and FIFO waitlist promotion for one course offering. It is an in-memory service and does not include a frontend, database, authentication, payments, or multi-course registration.

## Service Boundary and API

The FastAPI application exposes three endpoints:

- `POST /enroll` accepts a learner ID and prerequisite status.
- `POST /drop` removes an enrolled learner and may promote a waitlisted learner.
- `GET /status` returns the current capacity, enrolled learners, and waitlist.

The core business logic is isolated in `app/service.py` so it can be tested independently of the HTTP API.

## Data Model

A learner has:

- `learner_id`
- `prerequisite_completed`

The course state has:

- Fixed capacity
- Enrolled learners, stored by learner ID
- A FIFO waitlist, stored as a queue

Learner IDs are trimmed before processing and treated as case-sensitive identifiers.

## Enrollment and Capacity Invariants

- Enrolled learner count never exceeds course capacity.
- A learner cannot be enrolled more than once.
- A learner cannot appear on the waitlist more than once.
- A learner who does not meet the prerequisite is not enrolled or added to the waitlist.
- Invalid requests do not change the course state.
- Dropping a learner who is not enrolled does not change the course state.

## Waitlist Promotion Rule

When an enrolled learner drops, one seat becomes available. The service promotes the earliest eligible learner on the FIFO waitlist.

The service defensively rechecks prerequisite eligibility during promotion. If an ineligible learner is encountered, they are retained on the waitlist and requeued at the back while the service continues searching for the earliest eligible learner. This defensive behavior protects the promotion rule if eligibility changes after a learner joins the waitlist.

## Persistence and Concurrency

The implementation uses an in-memory store because the assessment permits a minimal service when no starter project or data model is supplied.

The current implementation is intended for a single-process demonstration. A production version would use database transactions or locking to prevent race conditions during simultaneous enrollment and drop requests.

## Key Trade-offs

The design prioritizes clear, testable business rules over persistent storage or additional infrastructure. It is intentionally limited to one course offering and a small API surface.