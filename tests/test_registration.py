import threading

import pytest
from fastapi.testclient import TestClient

from app import main
from app.models import Learner
from app.service import CourseRegistrationService


# ---------------------------------------------------------------------------
# Enrollment and capacity
# ---------------------------------------------------------------------------

def test_enrolls_learner_when_capacity_is_available():
    service = CourseRegistrationService(capacity=2)

    result = service.enroll("learner-1", True)

    assert result["status"] == "enrolled"
    assert service.get_status()["enrolled"] == ["learner-1"]


def test_eligible_learner_is_waitlisted_when_course_is_full():
    service = CourseRegistrationService(capacity=1)
    service.enroll("learner-1", True)

    result = service.enroll("learner-2", True)

    assert result["status"] == "waitlisted"
    assert service.get_status()["waitlist"] == ["learner-2"]


# ---------------------------------------------------------------------------
# Duplicate requests
# ---------------------------------------------------------------------------

def test_duplicate_enrollment_does_not_create_duplicate_record():
    service = CourseRegistrationService(capacity=2)
    service.enroll("learner-1", True)

    result = service.enroll("learner-1", True)

    assert result["status"] == "already_enrolled"
    assert service.get_status()["enrolled"] == ["learner-1"]


def test_duplicate_waitlist_request_does_not_create_duplicate_record():
    service = CourseRegistrationService(capacity=1)
    service.enroll("learner-1", True)
    service.enroll("learner-2", True)

    result = service.enroll("learner-2", True)

    assert result["status"] == "already_waitlisted"
    assert service.get_status()["waitlist"] == ["learner-2"]


# ---------------------------------------------------------------------------
# Prerequisite failures
# ---------------------------------------------------------------------------

def test_learner_who_does_not_meet_prerequisite_is_not_enrolled():
    service = CourseRegistrationService(capacity=2)

    result = service.enroll("learner-1", False)

    assert result["status"] == "prerequisite_not_met"
    assert service.get_status()["enrolled"] == []


def test_ineligible_learner_is_not_waitlisted_when_course_is_full():
    service = CourseRegistrationService(capacity=1)
    service.enroll("learner-1", True)

    result = service.enroll("learner-2", False)

    assert result["status"] == "prerequisite_not_met"
    assert service.get_status()["enrolled"] == ["learner-1"]
    assert service.get_status()["waitlist"] == []


# ---------------------------------------------------------------------------
# Drop and FIFO promotion
# ---------------------------------------------------------------------------

def test_drop_promotes_first_waitlisted_learner_in_fifo_order():
    service = CourseRegistrationService(capacity=1)
    service.enroll("learner-1", True)
    service.enroll("learner-2", True)
    service.enroll("learner-3", True)

    result = service.drop("learner-1")

    assert result["status"] == "dropped"
    assert result["promoted_learner_id"] == "learner-2"
    assert service.get_status()["enrolled"] == ["learner-2"]
    assert service.get_status()["waitlist"] == ["learner-3"]


def test_fifo_order_is_preserved_across_multiple_drops():
    service = CourseRegistrationService(capacity=2)
    service.enroll("learner-1", True)
    service.enroll("learner-2", True)
    service.enroll("learner-3", True)
    service.enroll("learner-4", True)

    first_drop = service.drop("learner-1")
    second_drop = service.drop("learner-2")

    assert first_drop["promoted_learner_id"] == "learner-3"
    assert second_drop["promoted_learner_id"] == "learner-4"
    assert service.get_status()["enrolled"] == ["learner-3", "learner-4"]
    assert service.get_status()["waitlist"] == []


# ---------------------------------------------------------------------------
# Ineligible learner on the waitlist (skip but keep position)
# These tests insert directly into service state because the public API
# rejects ineligible learners before they can join the waitlist.
# ---------------------------------------------------------------------------

def test_ineligible_waitlisted_learner_is_skipped_during_promotion():
    service = CourseRegistrationService(capacity=1)
    service.enroll("learner-1", True)
    service.course.waitlist.append(Learner("learner-2", False))
    service.course.waitlist.append(Learner("learner-3", True))

    result = service.drop("learner-1")

    assert result["promoted_learner_id"] == "learner-3"
    assert service.get_status()["enrolled"] == ["learner-3"]
    assert service.get_status()["waitlist"] == ["learner-2"]


def test_skipped_learner_keeps_position_ahead_of_later_learners():
    service = CourseRegistrationService(capacity=1)
    service.enroll("learner-1", True)
    service.course.waitlist.append(Learner("learner-2", False))
    service.course.waitlist.append(Learner("learner-3", True))
    service.course.waitlist.append(Learner("learner-4", True))

    result = service.drop("learner-1")

    assert result["promoted_learner_id"] == "learner-3"
    assert service.get_status()["waitlist"] == ["learner-2", "learner-4"]


def test_no_promotion_when_all_waitlisted_learners_are_ineligible():
    service = CourseRegistrationService(capacity=1)
    service.enroll("learner-1", True)
    service.course.waitlist.append(Learner("learner-2", False))

    result = service.drop("learner-1")

    assert result["status"] == "dropped"
    assert "promoted_learner_id" not in result
    assert service.get_status()["enrolled"] == []
    assert service.get_status()["waitlist"] == ["learner-2"]


# ---------------------------------------------------------------------------
# Invalid and repeated requests
# ---------------------------------------------------------------------------

def test_invalid_and_repeated_drops_do_not_change_course_state():
    service = CourseRegistrationService(capacity=1)
    service.enroll("learner-1", True)

    invalid_result = service.drop("")
    first_drop = service.drop("learner-1")
    repeated_drop = service.drop("learner-1")

    assert invalid_result["status"] == "invalid_request"
    assert first_drop["status"] == "dropped"
    assert repeated_drop["status"] == "not_enrolled"
    assert service.get_status()["enrolled"] == []


def test_invalid_enrollment_requests_do_not_change_course_state():
    service = CourseRegistrationService(capacity=1)
    service.enroll("learner-1", True)

    empty_id_result = service.enroll("", True)
    invalid_prerequisite_result = service.enroll("learner-2", "true")

    assert empty_id_result["status"] == "invalid_request"
    assert invalid_prerequisite_result["status"] == "invalid_request"
    assert service.get_status()["enrolled"] == ["learner-1"]
    assert service.get_status()["waitlist"] == []


def test_repeated_drop_after_promotion_does_not_change_state():
    service = CourseRegistrationService(capacity=1)
    service.enroll("learner-1", True)
    service.enroll("learner-2", True)
    service.enroll("learner-3", True)

    first_drop = service.drop("learner-1")
    repeated_drop = service.drop("learner-1")

    assert first_drop["promoted_learner_id"] == "learner-2"
    assert repeated_drop["status"] == "not_enrolled"
    assert service.get_status()["enrolled"] == ["learner-2"]
    assert service.get_status()["waitlist"] == ["learner-3"]


# ---------------------------------------------------------------------------
# Concurrency (regression guards; see DESIGN.md for the caveat about the GIL)
# ---------------------------------------------------------------------------

def _run_threads(target, count, args_for=None):
    threads = [
        threading.Thread(
            target=target,
            args=args_for(i) if args_for else (),
        )
        for i in range(count)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def test_concurrent_enrollments_never_exceed_capacity():
    capacity, total = 5, 50
    service = CourseRegistrationService(capacity=capacity)
    barrier = threading.Barrier(total)

    def worker(i):
        barrier.wait()
        service.enroll(f"learner-{i}", True)

    _run_threads(worker, total, args_for=lambda i: (i,))

    status = service.get_status()
    assert len(status["enrolled"]) == capacity
    assert len(status["waitlist"]) == total - capacity
    assert len(set(status["enrolled"]) | set(status["waitlist"])) == total


def test_concurrent_duplicate_requests_create_one_record():
    service = CourseRegistrationService(capacity=5)
    barrier = threading.Barrier(20)

    def worker():
        barrier.wait()
        service.enroll("learner-1", True)

    _run_threads(worker, 20)

    status = service.get_status()
    assert status["enrolled"] == ["learner-1"]
    assert status["waitlist"] == []


def test_concurrent_drops_of_same_learner_promote_only_once():
    service = CourseRegistrationService(capacity=1)
    service.enroll("learner-1", True)
    service.enroll("learner-2", True)
    service.enroll("learner-3", True)
    barrier = threading.Barrier(10)
    results = []

    def worker():
        barrier.wait()
        results.append(service.drop("learner-1")["status"])

    _run_threads(worker, 10)

    assert results.count("dropped") == 1
    assert results.count("not_enrolled") == 9
    assert service.get_status()["enrolled"] == ["learner-2"]
    assert service.get_status()["waitlist"] == ["learner-3"]


# ---------------------------------------------------------------------------
# HTTP API (status-code mapping)
# ---------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    # Fresh service per test so global state never leaks between tests.
    monkeypatch.setattr(main, "service", CourseRegistrationService(capacity=1))
    return TestClient(main.app)


def api_enroll(client, learner_id, prereq=True):
    return client.post(
        "/enroll",
        json={"learner_id": learner_id, "prerequisite_completed": prereq},
    )


def test_api_enroll_then_waitlist_return_200(client):
    assert api_enroll(client, "a").json()["status"] == "enrolled"

    second = api_enroll(client, "b")

    assert second.status_code == 200
    assert second.json()["status"] == "waitlisted"


def test_api_duplicate_enroll_returns_409(client):
    api_enroll(client, "a")

    response = api_enroll(client, "a")

    assert response.status_code == 409
    assert response.json()["status"] == "already_enrolled"


def test_api_prerequisite_not_met_returns_422(client):
    response = api_enroll(client, "a", prereq=False)

    assert response.status_code == 422
    assert client.get("/status").json()["enrolled"] == []


def test_api_empty_learner_id_returns_400(client):
    response = api_enroll(client, "")

    assert response.status_code == 400
    assert response.json()["status"] == "invalid_request"


def test_api_missing_field_is_rejected_by_validation(client):
    response = client.post("/enroll", json={"learner_id": "a"})

    assert response.status_code == 422


def test_api_drop_promotes_next_learner(client):
    api_enroll(client, "a")
    api_enroll(client, "b")

    response = client.post("/drop", json={"learner_id": "a"})

    assert response.status_code == 200
    assert response.json()["promoted_learner_id"] == "b"
    status = client.get("/status").json()
    assert status["enrolled"] == ["b"]
    assert status["waitlist"] == []


def test_api_repeated_drop_returns_404_and_keeps_state(client):
    api_enroll(client, "a")
    client.post("/drop", json={"learner_id": "a"})

    response = client.post("/drop", json={"learner_id": "a"})

    assert response.status_code == 404
    assert response.json()["status"] == "not_enrolled"
    assert client.get("/status").json()["enrolled"] == []