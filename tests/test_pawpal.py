"""Tests for PawPal+ domain model and scheduler."""

from datetime import date, timedelta

from pawpal_system import Pet, Scheduler, Task


def test_mark_complete_sets_task_status():
    task = Task("Walk", 20, "high")
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet("Mochi", "dog")
    assert len(pet.get_tasks()) == 0
    pet.add_task(Task("Feed", 10, "high"))
    assert len(pet.get_tasks()) == 1
    pet.add_task(Task("Walk", 15, "medium"))
    assert len(pet.get_tasks()) == 2


def test_sort_tasks_by_time_is_chronological():
    """Tasks with due_time should sort earliest clock time first; untimed tasks last."""
    scheduler = Scheduler()
    tasks = [
        Task("Evening", 10, "low", due_time="18:00"),
        Task("Morning", 15, "high", due_time="07:30"),
        Task("No time", 5, "medium"),
        Task("Noon", 20, "medium", due_time="12:00"),
    ]
    ordered = scheduler.sort_tasks_by_time(tasks)
    assert [t.title for t in ordered] == ["Morning", "Noon", "Evening", "No time"]


def test_daily_recurrence_spawns_next_day_task():
    """Completing a daily recurring task appends a new pending instance for the next day."""
    pet = Pet("Mochi", "dog")
    today = date(2026, 3, 15)
    daily = Task(
        "Fresh water",
        5,
        "medium",
        recurrence="daily",
        due_date=today,
    )
    pet.add_task(daily)
    nxt = pet.finalize_recurring_task(daily)
    assert daily.completed is True
    assert nxt is not None
    assert nxt.completed is False
    assert nxt.due_date == today + timedelta(days=1)
    assert nxt.recurrence == "daily"
    assert len(pet.get_tasks()) == 2


def test_find_due_time_conflicts_flags_duplicate_times():
    """Two pending tasks at the same HH:MM should produce a conflict warning."""
    scheduler = Scheduler()
    tasks = [
        Task("Walk", 25, "high", due_time="09:00"),
        Task("Meds", 5, "high", due_time="09:00"),
    ]
    notes = scheduler.find_due_time_conflicts(tasks)
    assert len(notes) == 1
    assert "09:00" in notes[0]
    assert "conflict" in notes[0].lower()
