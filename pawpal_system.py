"""PawPal+ logic layer: domain classes and scheduling utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional


@dataclass
class Task:
    """One pet care item: title, duration, and priority."""

    title: str
    duration_minutes: int
    priority: str
    completed: bool = False

    def __post_init__(self) -> None:
        """Validate duration and normalize priority to low, medium, or high."""
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        normalized = self.priority.strip().lower()
        if normalized not in {"low", "medium", "high"}:
            raise ValueError("priority must be one of: low, medium, high")
        self.priority = normalized

    def duration(self) -> int:
        """Return this task's duration in minutes."""
        return self.duration_minutes

    def priority_rank(self) -> int:
        """Return a numeric rank for sorting (higher means more urgent)."""
        order = {"low": 1, "medium": 2, "high": 3}
        return order.get(self.priority.lower(), 2)

    def summary(self) -> str:
        """Return a short human-readable line for display."""
        status = "done" if self.completed else "pending"
        return f"{self.title} ({self.duration_minutes} min, {self.priority}, {status})"

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True


@dataclass
class Pet:
    """A pet with an optional owner link and a backlog of tasks."""

    name: str
    species: str
    owner: Optional[Owner] = None
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a task to this pet's backlog."""
        self.tasks.append(task)

    def get_tasks(self) -> list[Task]:
        """Return a shallow copy of this pet's tasks."""
        return list(self.tasks)


@dataclass
class Owner:
    """Pet owner: time budget and preferences for planning."""

    name: str
    minutes_available_today: int
    preferences: dict[str, Any] = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with this owner and set ``pet.owner``."""
        if pet not in self.pets:
            self.pets.append(pet)
        pet.owner = self

    def get_pets(self) -> list[Pet]:
        """Return a shallow copy of pets owned by this owner."""
        return list(self.pets)

    def available_minutes(self) -> int:
        """Return how many minutes the owner has for pet care today."""
        return self.minutes_available_today

    def get_all_tasks(self) -> list[Task]:
        """Collect tasks from every pet in order."""
        all_tasks: list[Task] = []
        for pet in self.pets:
            all_tasks.extend(pet.get_tasks())
        return all_tasks


class Scheduler:
    """Builds a daily plan and explanations from owner/pet tasks.

    This class is intentionally lightweight and deterministic so it can
    be used from tests and the Streamlit UI.
    """

    def build_plan(
        self,
        owner: Owner,
        pet: Optional[Pet] = None,
        tasks: Optional[list[Task]] = None,
        start_time: str = "08:00",
    ) -> list[dict[str, Any]]:
        """Build an ordered schedule dict for the owner within their time budget."""
        if tasks is not None:
            source_tasks = list(tasks)
        elif pet is not None:
            source_tasks = pet.get_tasks()
        else:
            source_tasks = owner.get_all_tasks()

        # Prioritize by (priority desc, duration asc, title asc) for stable output.
        ranked = sorted(
            (task for task in source_tasks if not task.completed),
            key=lambda task: (-task.priority_rank(), task.duration_minutes, task.title.lower()),
        )

        plan: list[dict[str, Any]] = []
        minutes_left = owner.available_minutes()
        current_time = datetime.strptime(start_time, "%H:%M")

        for task in ranked:
            if task.duration_minutes > minutes_left:
                continue
            end_time = current_time + timedelta(minutes=task.duration_minutes)
            reason = self.explain_placement(
                task,
                context=(
                    f"minutes_left={minutes_left}, "
                    f"priority={task.priority}, "
                    f"duration={task.duration_minutes}"
                ),
            )
            plan.append(
                {
                    "task": task.title,
                    "priority": task.priority,
                    "duration_minutes": task.duration_minutes,
                    "start": current_time.strftime("%H:%M"),
                    "end": end_time.strftime("%H:%M"),
                    "reason": reason,
                }
            )
            minutes_left -= task.duration_minutes
            current_time = end_time

        return plan

    def explain_placement(self, task: Task, context: str) -> str:
        """Describe why a task was placed in the plan (for UI or logs)."""
        return (
            f"Selected '{task.title}' because it is {task.priority} priority, "
            f"fits the remaining time, and helps maximize important care first "
            f"({context})."
        )


class DailyPlanner(Scheduler):
    """Backward-compatible name from earlier UML drafts."""
