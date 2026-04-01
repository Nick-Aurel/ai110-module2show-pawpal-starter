"""CLI demo: exercise Phase 4 sorting, filtering, conflicts, and scheduling.

Run: ``python main.py``
"""

from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task


def print_schedule(owner_name: str, plan: list[dict]) -> None:
    """Format scheduler output as plain text (avoids printing raw object reprs)."""
    print(f"\n{'=' * 60}")
    print(f"  Today's Schedule — {owner_name}")
    print(f"{'=' * 60}")
    if not plan:
        print("  (no tasks fit in the time available)")
        print()
        return
    for i, row in enumerate(plan, start=1):
        print(f"\n  {i}. {row['task']}")
        print(f"     Time:  {row['start']} – {row['end']}  ({row['duration_minutes']} min)")
        print(f"     Priority: {row['priority']}")
        print(f"     Why: {row['reason']}")
    print()


def main() -> None:
    scheduler = Scheduler()
    owner = Owner(name="Jordan", minutes_available_today=120)

    mochi = Pet(name="Mochi", species="dog")
    owner.add_pet(mochi)

    # Tasks added "out of order" by due_time — sorting demo
    mochi.add_task(Task("Brush", 10, "low", due_time="12:30"))
    mochi.add_task(Task("Morning walk", 25, "high", due_time="09:00"))
    mochi.add_task(Task("Meds", 5, "high", due_time="09:00"))  # conflict with walk
    mochi.add_task(Task("Evening feed", 15, "medium", due_time="18:00"))

    all_tasks = owner.get_all_tasks()
    print("\n--- sort_tasks_by_time (due_time order) ---")
    for t in scheduler.sort_tasks_by_time(all_tasks):
        print(f"  {t.due_time or '—':>5}  {t.title}")

    print("\n--- filter_by_completion (pending only) ---")
    for t in scheduler.filter_by_completion(all_tasks, completed=False):
        print(f"  {t.summary()}")

    print("\n--- tasks_for_pet_name('Mochi') ---")
    for t in scheduler.tasks_for_pet_name(owner, "Mochi"):
        print(f"  {t.title}")

    plan, warns = scheduler.build_plan(owner, pet=mochi, start_time="07:00")
    print("\n--- scheduling warnings (due-time conflicts, etc.) ---")
    if warns:
        for w in warns:
            print(f"  ⚠ {w}")
    else:
        print("  (none)")

    print_schedule(owner.name, plan)

    # Recurring: daily task completes → next instance
    print("--- recurring task (daily) ---")
    daily = Task("Fresh water", 5, "medium", recurrence="daily", due_date=date.today())
    mochi.add_task(daily)
    nxt = mochi.finalize_recurring_task(daily)
    print(f"  Completed daily; spawned next: {nxt.summary() if nxt else 'n/a'}")


if __name__ == "__main__":
    main()
