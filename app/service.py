import threading

from app.models import CourseState, Learner


class CourseRegistrationService:
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("Course capacity must be greater than zero.")

        self.course = CourseState(capacity=capacity)
        # Non-reentrant lock: only public methods acquire it. Private helpers
        # (e.g. _promote_waitlisted_learner) must never acquire it, or drop()
        # would deadlock.
        self._lock = threading.Lock()

    def enroll(self, learner_id: str, prerequisite_completed: bool) -> dict:
        # Validation touches no shared state, so it runs outside the lock.
        if not isinstance(learner_id, str) or not learner_id.strip():
            return {
                "status": "invalid_request",
                "message": "learner_id must be a non-empty string.",
            }

        if not isinstance(prerequisite_completed, bool):
            return {
                "status": "invalid_request",
                "message": "prerequisite_completed must be true or false.",
            }

        learner_id = learner_id.strip()

        with self._lock:
            if learner_id in self.course.enrolled:
                return {
                    "status": "already_enrolled",
                    "message": "Learner is already enrolled.",
                }

            if self._is_waitlisted(learner_id):
                return {
                    "status": "already_waitlisted",
                    "message": "Learner is already on the waitlist.",
                }

            if not prerequisite_completed:
                return {
                    "status": "prerequisite_not_met",
                    "message": "Learner does not meet the prerequisite.",
                }

            learner = Learner(
                learner_id=learner_id,
                prerequisite_completed=prerequisite_completed,
            )

            if len(self.course.enrolled) < self.course.capacity:
                self.course.enrolled[learner_id] = learner
                return {
                    "status": "enrolled",
                    "message": "Learner enrolled successfully.",
                }

            self.course.waitlist.append(learner)
            return {
                "status": "waitlisted",
                "message": "Course is full; learner added to the waitlist.",
            }

    def drop(self, learner_id: str) -> dict:
        if not isinstance(learner_id, str) or not learner_id.strip():
            return {
                "status": "invalid_request",
                "message": "learner_id must be a non-empty string.",
            }

        learner_id = learner_id.strip()

        with self._lock:
            if learner_id not in self.course.enrolled:
                return {
                    "status": "not_enrolled",
                    "message": "Learner is not currently enrolled.",
                }

            del self.course.enrolled[learner_id]
            promoted_learner = self._promote_waitlisted_learner()

            result = {
                "status": "dropped",
                "message": "Learner dropped successfully.",
            }

            if promoted_learner:
                result["promoted_learner_id"] = promoted_learner.learner_id

            return result

    def get_status(self) -> dict:
        with self._lock:
            return {
                "capacity": self.course.capacity,
                "enrolled": list(self.course.enrolled.keys()),
                "waitlist": [
                    learner.learner_id for learner in self.course.waitlist
                ],
            }

    # ---- private helpers: callers must already hold self._lock ----

    def _is_waitlisted(self, learner_id: str) -> bool:
        return any(
            learner.learner_id == learner_id
            for learner in self.course.waitlist
        )

    def _promote_waitlisted_learner(self) -> Learner | None:
        # Policy: ineligible learners are skipped but keep their queue
        # position. Only the promoted learner is removed, so the relative
        # order of everyone else is unchanged.
        for index, learner in enumerate(self.course.waitlist):
            if learner.prerequisite_completed:
                del self.course.waitlist[index]
                self.course.enrolled[learner.learner_id] = learner
                return learner

        return None