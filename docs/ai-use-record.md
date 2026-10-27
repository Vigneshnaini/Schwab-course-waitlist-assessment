# AI-Assisted Engineering Record

## Purpose

This record describes how AI was used as an engineering assistant during a time-boxed assessment for a single-course enrollment, drop, and FIFO waitlist-promotion service.

## AI Tool

OpenAI Codex / ChatGPT

## Initial Scope Consultation

### Request Summary

I sought guidance on interpreting the assessment when no starter project, dataset, or existing code was supplied.

### AI Contribution

AI identified the permitted minimal fallback: a small Python service using in-memory state, focused on one course offering. It also clarified that the scope did not require a frontend, database, authentication, deployment, course catalog, payment integration, or multi-term registration.

### Decision and Files Informed

Accepted. I implemented a Python/FastAPI service with pytest tests and supporting Markdown documentation.

Files informed:

- `app/models.py`
- `app/service.py`
- `app/main.py`
- `tests/test_registration.py`
- `docs/`
- `README.md`

### Verification

The implementation was kept intentionally limited to one course offering and in-memory state.

---

## Structured Engineering Consultations

### 1. Delivery Planning

#### Prompt

> I’m completing a time-boxed engineering assessment for a single-course registration service with enrollment, dropping, prerequisite validation, and FIFO waitlist promotion. No starter project was supplied, so I will use a Python service with an in-memory store.
>
> Create an ordered delivery plan covering assumptions, design, implementation, tests, documentation, and verification. Give each stage a clear definition of done. Identify scope boundaries I should avoid expanding.

#### Relevant AI Response Summary

AI proposed an ordered plan covering assumptions and invariants, service design, core implementation, focused tests, independent verification, documentation, and final GitHub submission checks. It specifically identified database, frontend, authentication, payments, multi-course support, and configurable policy engines as out of scope.

#### Decision

Accepted. The project was structured around a small service, focused tests, and the required documents.

#### Verification

The resulting repository contains application code, tests, design documentation, limitations, and AI-use evidence without unrelated infrastructure.

---

### 2. Policy and Invariant Design

#### Prompt

> Help me define the minimum design decisions and invariants for an in-memory, single-course enrollment service.
>
> The service must preserve capacity, prevent duplicate enrollment and waitlist records, validate prerequisites, support dropping, and promote the earliest eligible waitlisted learner. Identify ambiguities around learner identity, prerequisite status, and ineligible learners at promotion time. Recommend one simple, consistent policy without proposing a configurable policy engine.

#### Relevant AI Response Summary

AI recommended these core invariants:

- Enrolled count must never exceed capacity.
- A learner may not appear more than once in enrolled or waitlisted state.
- Invalid, duplicate, and repeated requests must not mutate state.
- Only eligible learners may enroll or initially join the waitlist.
- A valid drop can promote at most one learner.

It also recommended trimming learner IDs, treating them as case-sensitive, and rechecking eligibility during promotion. If an ineligible learner is found during promotion, the selected policy is to retain and requeue that learner at the back while continuing to search for the earliest eligible learner.

#### Decision

Accepted. The policy was documented and implemented consistently.

#### Files and Decisions Informed

- `docs/design-spec.md`
- `app/service.py`
- `tests/test_registration.py`

#### Verification

The implementation contains capacity checks, duplicate checks, prerequisite validation, bounded promotion logic, and tests for these behaviors.

---

### 3. Core Algorithm Design

#### Prompt

> Based on the agreed policy, provide concise pseudocode and recommended Python data structures for `enroll`, `drop`, `get_status`, and FIFO waitlist promotion.
>
> The design must ensure that invalid or duplicate requests do not mutate state, enrolled count never exceeds capacity, and a drop promotes at most one eligible learner. Explain the state transitions and boundary cases before showing implementation code.

#### Relevant AI Response Summary

AI recommended:

- A dictionary keyed by learner ID for enrolled learners.
- A FIFO queue for waitlisted learners.
- Validation before every state mutation.
- A bounded promotion loop that examines no more than the original waitlist length, avoiding an infinite loop when no waitlisted learner is eligible.

#### Decision

Accepted. The implementation uses a dictionary for enrolled learners and `collections.deque` for the FIFO waitlist.

#### Files and Decisions Informed

- `app/models.py`
- `app/service.py`

#### Verification

The promotion implementation stops after examining the original queue length and returns without promotion when no eligible learner exists.

---

### 4. Core Service Implementation

#### Prompt

> Help me implement the core Python service methods for a one-course, in-memory registration feature.
>
> Constraints:
> - fixed course capacity
> - eligible learners enroll when seats exist
> - eligible learners waitlist when full
> - duplicate enrollment and waitlist entries are rejected
> - invalid requests do not mutate state
> - a valid drop triggers FIFO promotion
> - an ineligible learner found during promotion is retained and requeued at the back while the next eligible learner is considered
>
> Provide compact, readable code with clear result statuses. Briefly explain any non-obvious state transitions so I can independently review the implementation.

#### Relevant AI Response Summary

AI provided a compact implementation approach for enrollment, dropping, duplicate prevention, status retrieval, and waitlist promotion. It used explicit result statuses such as `enrolled`, `waitlisted`, `already_enrolled`, `already_waitlisted`, `prerequisite_not_met`, `dropped`, `not_enrolled`, and `invalid_request`.

#### Decision

Accepted as the implementation baseline. I reviewed the service behavior against the stated invariants and validated it using automated tests and manual API requests.

#### Files and Decisions Informed

- `app/service.py`
- `app/models.py`
- `app/main.py`

#### Verification

The service was exercised manually through the FastAPI Swagger interface for enrollment, full-capacity waitlisting, dropping, automatic promotion, prerequisite rejection, repeated drops, and status retrieval.

---

### 5. Focused Test Implementation

#### Prompt

> Help me draft focused pytest tests for the service implementation.
>
> Cover available capacity, full capacity and waitlisting, duplicate enrollment, duplicate waitlist requests, prerequisite rejection, invalid enrollment and drop requests, FIFO promotion across multiple drops, repeated drops, and state integrity after rejected requests. Use readable arrange-act-assert style and keep the tests limited to the assessment scope.

#### Relevant AI Response Summary

AI proposed focused unit tests for core enrollment behavior, duplicate protection, prerequisite failure, invalid requests, FIFO promotion, multiple drops, repeated drops, and state integrity. It also recommended a defensive test that simulates an eligibility change after a learner has joined the waitlist.

#### Decision

Accepted. I added focused pytest coverage without adding database, frontend, or unrelated integration tests.

#### Files and Decisions Informed

- `tests/test_registration.py`

#### Verification Evidence

Command executed in the active virtual environment:

```text
python -m pytest