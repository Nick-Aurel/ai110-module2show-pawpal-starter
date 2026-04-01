"""PawPal+ logic layer: domain classes and scheduling utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Optional


def _due_time_to_minutes(value: Optional[str]) -> int:
    """Minutes since midnight for sorting; missing/invalid sorts last."""
    if not value or not str(value).strip():
        return 24 * 60 + 1
    try:
        parts = str(value).strip().split(":")
        h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        return h * 60 + m
    except (ValueError, IndexError):
        return 24 * 60 + 1


@dataclass
class Task:
    """One pet care item: title, duration, priority, optional due time / recurrence."""

    title: str
    duration_minutes: int
    priority: str
    completed: bool = False
    due_time: Optional[str] = None  # "HH:MM" (24h) for sorting & conflict checks
    recurrence: Optional[str] = None  # "daily", "weekly", or None
    due_date: Optional[date] = None  # anchor for spawning the next recurring instance

    def __post_init__(self) -> None:
        """Validate duration, priority, optional due_time and recurrence."""
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        normalized = self.priority.strip().lower()
        if normalized not in {"low", "medium", "high"}:
            raise ValueError("priority must be one of: low, medium, high")
        self.priority = normalized
        if self.due_time is not None and str(self.due_time).strip():
            dt = str(self.due_time).strip()
            if not re.fullmatch(r"([01]?\d|2[0-3]):[0-5]\d", dt):
                raise ValueError(f"due_time must be HH:MM (24h), got {dt!r}")
            h, m = dt.split(":")
            self.due_time = f"{int(h):02d}:{int(m):02d}"
        else:
            self.due_time = None
        if self.recurrence is not None:
            r = self.recurrence.strip().lower()
            if r not in {"daily", "weekly"}:
                raise ValueError("recurrence must be 'daily', 'weekly', or None")
            self.recurrence = r

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
        when = f", due {self.due_time}" if self.due_time else ""
        rec = f", {self.recurrence}" if self.recurrence else ""
        return f"{self.title} ({self.duration_minutes} min, {self.priority}{when}{rec}, {status})"

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def spawn_next_occurrence(self) -> Task:
        """Create the next pending instance for a daily/weekly recurring task."""
        if self.recurrence not in {"daily", "weekly"}:
            raise ValueError("spawn_next_occurrence requires recurrence daily or weekly")
        base = self.due_date or date.today()
        delta = 1 if self.recurrence == "daily" else 7
        next_d = base + timedelta(days=delta)
        return Task(
            title=self.title,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            completed=False,
            due_time=self.due_time,
            recurrence=self.recurrence,
            due_date=next_d,
        )


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

    def finalize_recurring_task(self, task: Task) -> Optional[Task]:
        """Mark task complete; if daily/weekly, append the next occurrence."""
        if task not in self.tasks:
            raise ValueError("task must belong to this pet")
        if not task.recurrence:
            task.mark_complete()
            return None
        task.mark_complete()
        nxt = task.spawn_next_occurrence()
        self.add_task(nxt)
        return nxt


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

    def sort_tasks_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted by ``due_time`` (HH:MM); tasks without time sort last."""
        return sorted(
            tasks,
            key=lambda t: (_due_time_to_minutes(t.due_time), t.title.lower()),
        )

    def filter_by_completion(self, tasks: list[Task], completed: Optional[bool] = None) -> list[Task]:
        """Keep all tasks, or only completed / only pending when ``completed`` is set."""
        if completed is None:
            return list(tasks)
        return [t for t in tasks if t.completed is completed]

    def tasks_for_pet_name(self, owner: Owner, pet_name: str) -> list[Task]:
        """Return a copy of tasks for the first pet whose name matches (case-insensitive)."""
        needle = pet_name.strip().lower()
        for pet in owner.get_pets():
            if pet.name.lower() == needle:
                return pet.get_tasks()
        return []

    def find_due_time_conflicts(self, tasks: list[Task]) -> list[str]:
        """Warn when two or more pending tasks share the same ``due_time`` (lightweight)."""
        pending = [t for t in tasks if not t.completed and t.due_time]
        by_time: dict[str, list[str]] = {}
        for t in pending:
            by_time.setdefault(t.due_time, []).append(t.title)
        notes: list[str] = []
        for hhmm, titles in sorted(by_time.items(), key=lambda x: _due_time_to_minutes(x[0])):
            if len(titles) > 1:
                names = ", ".join(sorted(titles))
                notes.append(
                    f"Due-time conflict at {hhmm}: multiple tasks want that slot ({names}). "
                    "Adjust times or priorities so the owner can do one thing at a time."
                )
        return notes

    def detect_plan_overlaps(self, plan: list[dict[str, Any]]) -> list[str]:
        """Detect overlapping intervals in a built plan (sanity check; should usually be empty)."""
        notes: list[str] = []
        intervals: list[tuple[int, int, str]] = []
        for row in plan:
            s = datetime.strptime(row["start"], "%H:%M")
            e = datetime.strptime(row["end"], "%H:%M")
            sm = s.hour * 60 + s.minute
            em = e.hour * 60 + e.minute
            intervals.append((sm, em, row["task"]))
        intervals.sort(key=lambda x: x[0])
        for i in range(1, len(intervals)):
            prev_end = intervals[i - 1][1]
            cur_start, _, cur_title = intervals[i]
            if cur_start < prev_end:
                notes.append(
                    f"Scheduled overlap: '{intervals[i - 1][2]}' and '{cur_title}' both occupy time."
                )
        return notes

    def build_plan(
        self,
        owner: Owner,
        pet: Optional[Pet] = None,
        tasks: Optional[list[Task]] = None,
        start_time: str = "08:00",
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Build an ordered schedule and return ``(plan_rows, warning_messages)``."""
        if tasks is not None:
            source_tasks = list(tasks)
        elif pet is not None:
            source_tasks = pet.get_tasks()
        else:
            source_tasks = owner.get_all_tasks()

        warnings = list(self.find_due_time_conflicts(source_tasks))

        pending = [task for task in source_tasks if not task.completed]
        # Order: earlier due_time first, then higher priority, shorter duration, title.
        ranked = sorted(
            pending,
            key=lambda task: (
                _due_time_to_minutes(task.due_time),
                -task.priority_rank(),
                task.duration_minutes,
                task.title.lower(),
            ),
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

        warnings.extend(self.detect_plan_overlaps(plan))
        return plan, warnings

    def explain_placement(self, task: Task, context: str) -> str:
        """Describe why a task was placed in the plan (for UI or logs)."""
        return (
            f"Selected '{task.title}' because it is {task.priority} priority, "
            f"fits the remaining time, and helps maximize important care first "
            f"({context})."
        )


class DailyPlanner(Scheduler):
    """Backward-compatible name from earlier UML drafts."""
