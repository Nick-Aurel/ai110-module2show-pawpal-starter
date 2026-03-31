"""Tests for PawPal+ domain model."""

from pawpal_system import Pet, Task


# Ensures a task starts incomplete and that mark_complete() updates the flag
# (scheduler and UI rely on completed vs pending).
def test_mark_complete_sets_task_status():
    task = Task("Walk", 20, "high")
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


# Ensures add_task actually appends to the pet's backlog (count grows each time).
def test_add_task_increases_pet_task_count():
    pet = Pet("Mochi", "dog")
    assert len(pet.get_tasks()) == 0
    pet.add_task(Task("Feed", 10, "high"))
    assert len(pet.get_tasks()) == 1
    pet.add_task(Task("Walk", 15, "medium"))
    assert len(pet.get_tasks()) == 2
