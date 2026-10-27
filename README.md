# Course Waitlist Assessment

An in-memory service that handles enrollment, dropping, and FIFO waitlist promotion
for a single course offering. Built with Python and FastAPI, with automated tests
and design documentation.

## Features

- Enrolls eligible learners while seats are available
- Adds eligible learners to a FIFO waitlist when the course is full
- Rejects duplicate enrollment and duplicate waitlist requests
- Rejects learners who do not meet the prerequisite (they never join the waitlist)
- Drops enrolled learners and promotes the earliest eligible waitlisted learner
- Returns clear results for invalid and repeated requests without changing state
- Serializes state changes with a lock so simultaneous requests cannot exceed capacity

Out of scope by design: frontend, database, authentication, payments, deployment,
course catalog, multi-term registration, and a configurable policy engine.

## Requirements

- Python 3.10 or newer (tested on 3.13)
- Dependencies in `requirements.txt`: FastAPI, Uvicorn, pytest, httpx2
  (`httpx2` is required by FastAPI's `TestClient`)

## Project Structure

```text
app/
  __init__.py
  models.py              Learner and course-state data structures
  service.py             Enrollment, drop, and waitlist business logic
  main.py                FastAPI endpoints and HTTP status mapping

tests/
  test_registration.py   Service, concurrency, and API tests (24 tests)

docs/
  design-spec.md         Design, invariants, assumptions, trade-offs
  ai-use-record.md       AI-assisted engineering record
  limitations.md         Limitations and follow-up risks

README.md
requirements.txt
.gitignore
```

## Setup

**1. Clone the repository**

```bash
git clone https://github.com/Vigneshnaini/Schwab-course-waitlist-assessment.git
cd Schwab-course-waitlist-assessment
```

**2. Create and activate a virtual environment**

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**

```bash
python -m pip install -r requirements.txt
```

## Run the Tests

From the project root:

```bash
python -m pytest -v
```

Expected result: `24 passed`.

The tests cover:

- available capacity and full-capacity waitlisting
- duplicate enrollment and duplicate waitlist requests
- prerequisite rejection
- invalid enrollment and drop requests
- FIFO promotion across multiple drops
- skip-and-keep-position for ineligible waitlisted learners
- repeated and invalid drops leaving state unchanged
- concurrent enroll and drop requests (barrier-synchronized threads)
- HTTP status-code mapping through the API

## Run the API

```bash
python -m uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`. Interactive Swagger UI is at
`http://127.0.0.1:8000/docs`. Stop the server with `Ctrl + C`.

The demo service starts with a capacity of 2. State is held in memory, so
restarting the server (including an automatic `--reload` restart after a file
change) clears all enrollments.

## API Reference

### `POST /enroll`

```json
{ "learner_id": "learner-1", "prerequisite_completed": true }
```

### `POST /drop`

```json
{ "learner_id": "learner-1" }
```

A successful drop promotes the earliest eligible waitlisted learner, if any, and
returns their ID as `promoted_learner_id`.

### `GET /status`

Returns the capacity, the enrolled learner IDs, and the waitlisted learner IDs in
FIFO order.

### Result statuses and HTTP codes

| Service status | HTTP code | Endpoint |
|----------------|-----------|----------|
| `enrolled`, `waitlisted`, `dropped` | 200 | enroll / drop |
| `invalid_request` | 400 | enroll / drop |
| `not_enrolled` | 404 | drop |
| `already_enrolled`, `already_waitlisted` | 409 | enroll |
| `prerequisite_not_met` | 422 | enroll |

Malformed request bodies (missing fields, wrong types) are rejected by FastAPI
with 422 before reaching the service.

## Assumptions and Policies

- The service manages one course offering only.
- `prerequisite_completed` is a boolean asserted by the caller. There is no
  transcript or identity integration.
- A learner who does not meet the prerequisite is rejected at request time and
  never enrolls or joins the waitlist.
- Learner IDs are trimmed before processing and treated as case-sensitive.
- Eligibility is rechecked during promotion. An ineligible learner found there is
  **skipped and keeps their original waitlist position**; the earliest eligible
  learner behind them is promoted, and the skipped learner is re-evaluated on later
  drops. Through the API this path is not currently reachable, so it is covered by
  unit tests that place an ineligible learner directly on the waitlist.
- Dropping a learner who is only waitlisted returns `not_enrolled`. There is no
  leave-waitlist operation.
- A single `threading.Lock` makes enroll, drop, and status calls atomic within one
  process. Multiple workers or processes would need a database transaction or row
  lock.
- Data is stored in memory only.

## Documentation

- [`docs/design-spec.md`](docs/design-spec.md): service boundary, data model,
  invariants, promotion rule, concurrency approach, trade-offs
- [`docs/ai-use-record.md`](docs/ai-use-record.md): AI prompts, decisions, and
  verification evidence
- [`docs/limitations.md`](docs/limitations.md): limitations and follow-up risks