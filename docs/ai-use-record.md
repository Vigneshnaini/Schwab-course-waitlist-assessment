# AI-Assisted Engineering Record

## Purpose
This record documents how AI was used as an engineering assistant while building
enrollment, drop, and FIFO waitlist promotion for a single course offering
(Python, FastAPI, in-memory store). No credentials, secrets, or personal data were
included in any prompt. Prompts are lightly edited for readability.

## Workflow and Tools
| Phase | Tool | Role |
|-------|------|------|
| Approach selection and task decomposition | Claude | Delivery approach, scope boundaries, design decisions to settle first |
| Implementation (models, service, API) | OpenAI Codex / ChatGPT | Baseline implementation |
| Implementation (tests) | OpenAI Codex / ChatGPT | Baseline test suite |
| Independent review | Claude | Adversarial code review, concurrency review |
| Applying review findings | Claude + my edits | Fixes, API tests, dependency resolution |
| Documentation | OpenAI Codex / ChatGPT | Design spec, README, limitations drafts |

The deliberate split was one tool to build and a second, independent tool to
review, so the reviewer had not authored the code under review.

## Summary of Decisions
| # | Activity | Tool | Decision |
|---|----------|------|----------|
| 1 | Approach and task decomposition | Claude | Accepted |
| 2 | Policy, invariants, and service build | Codex/ChatGPT | Invariants accepted; requeue-at-back policy later rejected |
| 3 | Test suite | Codex/ChatGPT | Accepted as baseline, then extended |
| 4 | Adversarial code review | Claude | Accepted; promotion logic changed |
| 5 | Concurrency review | Claude | Accepted; lock and tests added |
| 6 | HTTP status mapping and API tests | Claude | Accepted |
| 7 | Dependency incompatibility | Claude | Corrected after a real error |
| 8 | Documentation drafts | Codex/ChatGPT | Accepted after verification against code |

---

## 1. Approach and Task Decomposition (Claude)
- **Prompt:** I shared the assessment brief and asked for the best approach to
  deliver it within the timebox: how to decompose the work, which design decisions
  to settle before coding (prerequisite rule, ineligible-learner policy), and which
  scope boundaries to hold.
- **AI response:** Deliver one small service with an in-memory store, settle the
  eligibility policy and invariants first, then implement, test, and document.
  Keep scope to a single offering; exclude a frontend, catalog, payments, auth,
  and a policy engine.
- **Decision:** Accepted. I chose a Python/FastAPI service with pytest.
- **Files informed:** overall layout (`app/`, `tests/`, `docs/`)
- **Verification:** Checked the approach against the Scope Boundaries in the
  assignment.

## 2. Policy, Invariants, and Service Build (Codex/ChatGPT)
- **Prompt 2a (design):** Define the minimum design decisions and invariants for a
  single-course enrollment service, covering learner identity, prerequisite status,
  and ineligible learners at promotion time, without a configurable policy engine.
- **Response 2a:** Invariants: enrolled count never exceeds capacity; a learner
  appears at most once across enrolled and waitlist; invalid, duplicate, and
  repeated requests do not mutate state; only eligible learners enroll or join the
  waitlist; one drop promotes at most one learner. For an ineligible learner found
  during promotion it proposed **retain and requeue at the back**.
- **Prompt 2b (build):** Implement the one-course service with a fixed capacity,
  explicit statuses (`enrolled`, `waitlisted`, `already_enrolled`,
  `already_waitlisted`, `prerequisite_not_met`, `dropped`, `not_enrolled`,
  `invalid_request`), validation before mutation, and FIFO promotion on drop.
- **Response 2b:** `models.py` (dataclasses, a dict for enrolled learners, a `deque`
  waitlist), `service.py` (enroll, drop, status, bounded pop-and-requeue
  promotion), and `main.py` (FastAPI endpoints).
- **Decision:** Accepted as the baseline. The requeue-at-back policy was **rejected
  after independent review** (entry 4).
- **Files informed:** `app/models.py`, `app/service.py`, `app/main.py`
- **Verification:** Reviewed the code against the invariants and exercised it
  through Swagger: enrollment, waitlist overflow, drop with promotion,
  prerequisite rejection, and repeated drops.

## 3. Test Suite (Codex/ChatGPT)
- **Prompt:** Draft focused pytest tests in arrange-act-assert style covering
  capacity, full-course waitlisting, duplicates, prerequisite failure, invalid and
  repeated requests, FIFO across multiple drops, and state integrity.
- **AI response:** 12 unit tests, including a defensive test that places an
  ineligible learner directly on the waitlist.
- **Decision:** Accepted as the baseline, then extended in entries 4 to 6.
- **Files informed:** `tests/test_registration.py`
- **Verification:** Ran `python -m pytest`; all tests passed. The passing suite
  did not expose the ordering defect found in entry 4, because no test placed an
  eligible learner behind a skipped one. This is the gap the review closed.

## 4. Adversarial Code Review (Claude)
- **Prompt:** I submitted `service.py`, `models.py`, `main.py`, and the tests for an
  independent review of correctness, ordering, and concurrency.
- **AI response:**
  1. *Queue-ordering defect.* Promotion pops each ineligible learner and appends
     them to the back, so a skipped learner ends up behind later arrivals
     (waitlist `[2 (ineligible), 3, 4]` becomes `[4, 2]` after promoting 3). This
     contradicted the intent to retain waitlisted learners.
  2. *Unreachable path.* Through the API, ineligible learners are rejected before
     joining the waitlist, so the skip path is reachable only by inserting into
     service state directly.
- **Decision:**
  - Issue 1: **Accepted and implemented.** Promotion now scans by index and removes
    only the promoted learner, so everyone else keeps their position. This
    replaces the requeue-at-back policy from entry 2.
  - Issue 2: **Accepted as documentation** (no code change).
- **Files changed:** `app/service.py`, `tests/test_registration.py`
- **Verification:** Added `test_skipped_learner_keeps_position_ahead_of_later_learners`
  and `test_no_promotion_when_all_waitlisted_learners_are_ineligible`. Against the
  original pop-and-append code the first test failed:
  ```text
  ► PASTE real failing output (run: pytest -k skipped_learner_keeps_position -v)
  ```
  After the fix it passes.

## 5. Concurrency Review (Claude)
- **Prompt:** Part of the same review: is the service safe under simultaneous
  requests?
- **AI response:** FastAPI runs synchronous endpoints in a thread pool, so
  `len(enrolled) < capacity` followed by the insert is a check-then-act race. Use
  one `threading.Lock` around the public state-changing methods, and never acquire
  it in private helpers because it is non-reentrant.
- **Decision:** Accepted. Added `self._lock` to `enroll`, `drop`, and `get_status`.
  Validation stays outside the lock because it touches no shared state.
- **Files changed:** `app/service.py`, `tests/test_registration.py`
- **Verification:** Added three barrier-synchronized thread tests (50 concurrent
  enrollments into capacity 5; 20 duplicate requests; 10 concurrent drops of the
  same learner). These are **regression guards, not proof of safety**: CPython's GIL
  can hide the race without the lock. A database-backed version would need a
  transaction or row lock.

## 6. HTTP Status Mapping and API Tests (Claude)
- **Prompt:** Requested corrected code files and the tests consolidated into one file.
- **AI response:** Return HTTP codes that reflect outcomes (`invalid_request` 400,
  `not_enrolled` 404, `already_*` 409, `prerequisite_not_met` 422) instead of 200
  for everything, and add `TestClient` API tests.
- **Decision:** Accepted and implemented. Added `STATUS_CODES` and `_respond` in
  `main.py`, plus 7 API tests with a fixture giving each test a fresh service.
- **Files changed:** `app/main.py`, `tests/test_registration.py`
- **Verification:** API tests pass, and Swagger confirmed 200 for
  enrolled/waitlisted/dropped, 409 for duplicates, 422 for prerequisite failure,
  400 for an empty ID, and 404 for a repeated drop.

## 7. Dependency Incompatibility (Claude, corrected by me)
- **What happened:** Claude advised `httpx` for `TestClient`. In my environment
  (Python 3.13) test collection failed with "requires the httpx2 package".
- **Decision:** Corrected. I diagnosed the failure from the error output, installed
  `httpx2`, and updated `requirements.txt`.
- **Verification:** `pytest` collected and ran after the change.

## 8. Documentation Drafts (Codex/ChatGPT)
- **Prompt:** Requested the design specification, README, and limitations summary
  for the finished implementation.
- **AI response:** Drafts of those documents.
- **Decision:** Accepted after verifying them against the final code, including the
  skip-and-keep-position policy, the locking approach, and the status-code mapping.
- **Files informed:** `docs/design-spec.md`, `README.md`, `LIMITATIONS.md`
- **Verification:** ► Describe what you checked or corrected (e.g. updated policy
  text from requeue-at-back to keep-position; confirmed run commands from a fresh
  clone).

---

## Suggestions Rejected
- **Requeue skipped learners at the back** (Codex/ChatGPT): rejected because it
  breaks FIFO fairness. Replaced with skip-and-keep-position.
- **`leave_waitlist` operation:** rejected as out of scope. Dropping a waitlisted
  learner returns `not_enrolled`, documented as an assumption.
- **Configurable eligibility policy:** rejected; the assignment excludes a policy engine.

## Verification Evidence
**Automated tests** (`pytest -v`, Python 3.13, 24 tests):
```text
► PASTE the full pytest -v output showing 24 passed
```

**Manual API checks** (Swagger at `/docs`, capacity 2): enrolled up to capacity,
waitlist overflow in order, duplicate enroll (409), prerequisite failure (422),
empty ID (400), drop with FIFO promotion, repeated and unknown drops (404), and
`/status` unchanged after each rejected request.

## Contribution Summary
Codex/ChatGPT produced the baseline implementation, tests, and documentation
drafts. Claude served as an independent reviewer, identifying a queue-ordering
defect and a missing lock. I decided which suggestions to adopt, rejected the
requeue-at-back policy, resolved the dependency error, and verified the final
behavior with the automated suite and manual API runs.