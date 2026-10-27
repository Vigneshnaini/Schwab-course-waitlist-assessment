# Course Waitlist Assessment

A focused, AI-assisted engineering assessment implementing enrollment, dropping, and FIFO waitlist promotion for one course offering.

## Overview

This project provides a small in-memory course-registration service. It supports:

- Enrolling eligible learners while seats are available
- Adding eligible learners to a FIFO waitlist when the course is full
- Preventing duplicate enrollment and duplicate waitlist entries
- Dropping enrolled learners
- Automatically promoting the earliest eligible learner from the waitlist when a seat opens
- Returning clear outcomes for invalid and repeated requests

The project intentionally does not include a frontend, database, authentication, payments, deployment, course catalog, multi-term registration, or configurable policy engine.

## Technology

- Python 3.10+
- FastAPI
- Uvicorn
- pytest

## Project Structure

```
app/
  __init__.py
  models.py                 Learner and course-state data structures
  service.py                Enrollment, drop, and waitlist business logic
  main.py                   FastAPI endpoints

tests/
  test_registration.py      Automated tests

docs/
  design-spec.md            Design decisions and assumptions
  ai-use-record.md          AI-assisted engineering record
  limitations.md            Limitations and follow-up risks

README.md
requirements.txt
.gitignore
```

## Setup

### 1. Clone the repository

```powershell
git clone https://github.com/Vigneshnaini/Schwab-course-waitlist-assessment.git
cd Schwab-course-waitlist-assessment
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## Run Automated Tests

```powershell
python -m pytest
```

Expected result:

```text
12 passed
```

The tests cover available capacity, full-capacity waitlisting, duplicate enrollment and waitlist requests, prerequisite rejection, invalid enrollment and drop requests, FIFO promotion, multiple drops, repeated drops, and state integrity.

## Run the API

```powershell
python -m uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`.

Open Swagger UI for interactive testing:

```text
http://127.0.0.1:8000/docs
```

Stop the application with `Ctrl + C`.

## API Endpoints

### Enroll a learner

`POST /enroll`

```json
{
  "learner_id": "learner-1",
  "prerequisite_completed": true
}
```

Possible outcomes:

```text
enrolled
waitlisted
already_enrolled
already_waitlisted
prerequisite_not_met
invalid_request
```

### Drop a learner

`POST /drop`

```json
{
  "learner_id": "learner-1"
}
```

A successful drop automatically promotes the earliest eligible learner from the waitlist when one exists.

### View course status

`GET /status`

The response includes course capacity, enrolled learner IDs, and waitlisted learner IDs in FIFO order.

## Assumptions

- The service manages one course offering only.
- The API demonstration uses a capacity of two learners.
- A learner must meet the prerequisite to enroll or initially join the waitlist.
- Learner IDs are trimmed before processing and treated as case-sensitive.
- Eligibility is checked on enrollment and rechecked during promotion.
- If an ineligible learner is encountered during promotion, they remain waitlisted and are requeued at the back while the service looks for the next eligible learner.
- The application stores data in memory, so restarting it clears course state.

## Supporting Documentation

The `docs/` folder contains:

- `design-spec.md` - service design, assumptions, invariants, and trade-offs
- `ai-use-record.md` - AI-assisted engineering prompts, decisions, and verification
- `limitations.md` - current limitations and production follow-up risks