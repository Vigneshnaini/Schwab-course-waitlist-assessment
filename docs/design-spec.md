# Design Specification

## Scope

This project implements enrollment, dropping, and FIFO waitlist promotion for one
course offering. It is an in-memory service. It does not include a frontend,
database, authentication, payments, a course catalog, or multi-course registration.

## Service Boundary and API

The FastAPI application exposes three endpoints:

- `POST /enroll` accepts a learner ID and prerequisite status.
- `POST /drop` removes an enrolled learner and may promote a waitlisted learner.
- `GET /status` returns the capacity, enrolled learners, and waitlist (a snapshot).

All business rules live in `CourseRegistrationService` (`app/service.py`), which has
no dependency on FastAPI and can be tested directly. `app/main.py` only translates
HTTP requests and service results.

Service results carry a `status` field. The API maps it to an HTTP code:

| Service status | HTTP code |
|----------------|-----------|
| `enrolled`, `waitlisted`, `dropped` | 200 |
| `invalid_request` | 400 |
| `not_enrolled` | 404 |
| `already_enrolled`, `already_waitlisted` | 409 |
| `prerequisite_not_met` | 422 |

Malformed bodies (missing fields, wrong types) are rejected by FastAPI/Pydantic
with 422 before reaching the service.

## Data Model

A learner has `learner_id` and `prerequisite_completed`. The course state has a
fixed capacity, enrolled learners stored in an insertion-ordered dict keyed by
learner ID, and a FIFO waitlist stored as a `deque`. Learner IDs are trimmed and
treated as case-sensitive.

## Assumptions

- **Prerequisite rule:** `prerequisite_completed` is a boolean asserted by the
  caller. There is no transcript or identity integration (out of scope).
- **Ineligible learners are rejected at request time.** They are never enrolled
  and never join the waitlist.
- **Capacity must be greater than zero.**
- **Waitlist exit:** dropping a learner who is only waitlisted returns
  `not_enrolled`. There is no leave-waitlist operation.

## Enrollment and Capacity Invariants

- Enrolled count never exceeds capacity.
- A learner appears at most once across the enrolled set and the waitlist combined.
- An ineligible learner is never enrolled or added to the waitlist.
- Waitlist order is arrival order; promotion never reorders learners it does not promote.
- One drop promotes at most one learner.
- Invalid requests, duplicate requests, and drops of non-enrolled learners do not
  change state. Validation completes before any mutation.

## Waitlist Promotion Rule

When an enrolled learner drops, one seat opens. The service scans the waitlist
from the front and promotes the first learner whose prerequisite is satisfied.

**Policy for an ineligible learner at the front: skip and retain position.** An
ineligible learner is skipped, stays on the waitlist in their original position,
and is re-evaluated on later drops. Only the promoted learner is removed, so the
relative order of everyone else is unchanged. If no waitlisted learner is
eligible, the seat stays open and nobody is promoted.

An earlier approach (requeue the skipped learner at the back) was rejected because
it moves a skipped learner behind later arrivals and breaks FIFO fairness.

**Reachability note:** because ineligible learners are rejected at request time and
eligibility does not change afterward, this skip path cannot currently be reached
through the API. Promotion re-checks eligibility defensively in case that changes
(for example, if eligibility were later looked up from a data source). The path is
covered by unit tests that place an ineligible learner directly on the waitlist.

## Concurrency

FastAPI runs synchronous endpoints in a thread pool, so requests can overlap. The
service holds one `threading.Lock` around the public state-changing and reading
methods (`enroll`, `drop`, `get_status`), making each check-then-act sequence
atomic. Input validation runs outside the lock because it touches no shared state.
Private helpers never acquire the lock, since it is non-reentrant and `drop` calls
the promotion helper while holding it.

Three barrier-synchronized thread tests (concurrent enrollments, duplicate
requests, repeated drops of one learner) guard this behavior. They are regression
guards, not proof of safety: CPython's GIL can hide the race without the lock.

This protects a single process only. Multiple workers or processes would each hold
separate state and locks. A database-backed version would need a transaction or
row-level lock.

## Key Trade-offs

- In-memory state keeps the rules clear and testable, at the cost of persistence.
- One coarse lock is simple and correct for one course; it does not scale to many
  offerings or processes.
- Skip-and-retain adds a small amount of defensive logic that is not reachable via
  the API today, in exchange for a promotion rule that stays correct if eligibility
  becomes dynamic.