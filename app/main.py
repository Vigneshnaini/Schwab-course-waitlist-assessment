from fastapi import FastAPI, Response
from pydantic import BaseModel

from app.service import CourseRegistrationService


app = FastAPI(
    title="Course Waitlist Assessment",
    description="In-memory enrollment, drop, and FIFO waitlist service.",
)

service = CourseRegistrationService(capacity=2)

# Successful outcomes (enrolled, waitlisted, dropped) return 200.
STATUS_CODES = {
    "invalid_request": 400,
    "not_enrolled": 404,
    "already_enrolled": 409,
    "already_waitlisted": 409,
    "prerequisite_not_met": 422,
}


class EnrollmentRequest(BaseModel):
    learner_id: str
    prerequisite_completed: bool


class DropRequest(BaseModel):
    learner_id: str


def _respond(result: dict, response: Response) -> dict:
    response.status_code = STATUS_CODES.get(result["status"], 200)
    return result


@app.post("/enroll")
def enroll_learner(request: EnrollmentRequest, response: Response) -> dict:
    result = service.enroll(
        learner_id=request.learner_id,
        prerequisite_completed=request.prerequisite_completed,
    )
    return _respond(result, response)


@app.post("/drop")
def drop_learner(request: DropRequest, response: Response) -> dict:
    return _respond(service.drop(learner_id=request.learner_id), response)


@app.get("/status")
def get_course_status() -> dict:
    return service.get_status()