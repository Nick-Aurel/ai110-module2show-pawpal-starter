"""Temporary CLI entry point for PawPal+ (Phase 2 demo).

This script is not the Streamlit app. It builds sample Owner / Pet / Task
objects, runs :class:`Scheduler` from ``pawpal_system``, and prints a readable
"Today's Schedule" to the terminal so you can sanity-check the logic layer.

Run: ``python main.py``
"""

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
    """Wire demo data and print one day's plan for the sample owner."""
    owner = Owner(name="Jordan", minutes_available_today=120)

    mochi = Pet(name="Mochi", species="dog")
    pixel = Pet(name="Pixel", species="cat")

    owner.add_pet(mochi)
    owner.add_pet(pixel)

    # At least three tasks with different durations, split across pets.
    mochi.add_task(Task("Morning walk", 25, "high"))
    mochi.add_task(Task("Training session", 15, "medium"))

    pixel.add_task(Task("Wet food meal", 10, "high"))

    scheduler = Scheduler()
    plan = scheduler.build_plan(owner, start_time="07:00")

    print_schedule(owner.name, plan)


if __name__ == "__main__":
    main()
