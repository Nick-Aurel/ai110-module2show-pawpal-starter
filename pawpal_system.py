"""PawPal+ logic layer: domain classes and scheduling (skeleton from UML)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Task:
    """One pet care item: title, duration, and priority."""

    title: str
    duration_minutes: int
    priority: str

    def duration(self) -> int:
        pass

    def priority_rank(self) -> int:
        pass

    def summary(self) -> str:
        pass


@dataclass
class Pet:
    """A pet with an optional owner link and a backlog of tasks."""

    name: str
    species: str
    owner: Optional[Owner] = None
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        pass

    def get_tasks(self) -> list[Task]:
        pass


@dataclass
class Owner:
    """Pet owner: time budget and preferences for planning."""

    name: str
    minutes_available_today: int
    preferences: dict[str, Any] = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        pass

    def get_pets(self) -> list[Pet]:
        pass

    def available_minutes(self) -> int:
        pass


class DailyPlanner:
    """Builds a daily plan and explanations; no persistent state in the skeleton."""

    def build_plan(self, owner: Owner, pet: Pet, tasks: list[Task]) -> object:
        pass

    def explain_placement(self, task: Task, context: str) -> str:
        pass
