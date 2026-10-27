from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass
class Learner:
    learner_id: str
    prerequisite_completed: bool


@dataclass
class CourseState:
    capacity: int
    enrolled: dict[str, Learner] = field(default_factory=dict)
    waitlist: Deque[Learner] = field(default_factory=deque)