# PawPal+ Project Reflection

## 1. System Design

### Step 2: Building blocks (four main classes)

**Owner**

- **Attributes:** `name`; `minutes_available_today` (how many minutes the owner can spend on pet care today); optional `preferences` (e.g. preferred walk times or simple flags).
- **Methods:** `add_pet(pet)`; `pets()` / `get_pets()`; `available_minutes()` (read or update the time budget).

**Pet**

- **Attributes:** `name`; `species` (e.g. dog, cat, other); reference to owning **Owner**; a collection of **Task** objects for this planning session.
- **Methods:** `add_task(task)`; `tasks()` / `get_tasks()`; optionally `remove_task(task)` for the UI.

**Task**

- **Attributes:** `title`; `duration_minutes`; `priority` (e.g. low / medium / high, matching the Streamlit inputs in `app.py`).
- **Methods:** `duration()` (accessor); `priority_rank()` (numeric rank for sorting); `__repr__` or `summary()` for display.

**DailyPlanner** (in code the scheduling behavior also appears as **`Scheduler`**, with **`DailyPlanner`** as a subclass for the earlier UML name)

- **Attributes:** none required if it is a **stateless** service; optional `day_start` / slot size if you model a clock explicitly later.
- **Methods:** `build_plan(owner, pet, tasks)` → returns an ordered plan (and per-item explanations); `explain_placement(task, context)` for the “why this task here” strings.

Together, this gives: **Owner has many Pets**, **Pet has many Tasks**, and **DailyPlanner** / **Scheduler** uses Owner + Pet + Tasks to produce the day’s schedule and reasoning.

### Step 3: UML (Mermaid class diagram)

I used Cursor (instead of Copilot in VS Code) with the same idea: describe a **pet care app** with **four classes** and the brainstorm above, then generate a **Mermaid** class diagram. Mermaid is text-based; you can preview it in Cursor’s Markdown preview or paste it into the [Mermaid Live Editor](https://mermaid.live).

```mermaid
classDiagram
    direction LR

    class Owner {
        +str name
        +int minutes_available_today
        +dict preferences
        +add_pet(Pet) void
        +get_pets() list
        +available_minutes() int
        +get_all_tasks() list
    }

    class Pet {
        +str name
        +str species
        +Owner owner
        +list tasks
        +add_task(Task) void
        +get_tasks() list
    }

    class Task {
        +str title
        +int duration_minutes
        +str priority
        +bool completed
        +duration() int
        +priority_rank() int
        +summary() str
        +mark_complete() void
    }

    class DailyPlanner {
        +build_plan() object
        +explain_placement() str
    }

    Owner "1" --> "*" Pet : has
    Pet "1" --> "*" Task : has
    DailyPlanner ..> Owner : reads
    DailyPlanner ..> Pet : reads
    DailyPlanner ..> Task : orders and schedules
```

**Review:** The relationships match the domain: **Owner has Pets**, **Pet has Tasks**, and **DailyPlanner** depends on all three without owning them. The code implements scheduling in a **`Scheduler`** class (with **`DailyPlanner`** as a subclass); **`build_plan`** returns a list of structured entries (times, task, priority, reason).

**a. Initial design**

I chose four classes so the domain stays clear: **who** (owner and pet), **what work exists** (tasks), and **how a day is built** (planner). Responsibilities:

- **Owner** — Stores identity and scheduling inputs: name, how many minutes are available today, and optional preferences. It owns the list of **Pet** objects for this app (`add_pet` / `get_pets`) and exposes `available_minutes()` so the planner can respect the time budget.
- **Pet** — Stores the animal's name and species and holds the **Task** backlog for the current session (`add_task` / `get_tasks`). It can point back to its **Owner** so explanations and UI stay consistent.
- **Task** — One unit of care work: title, duration, priority. Helper methods (`duration`, `priority_rank`, `summary`) support sorting and display without putting all display logic in the UI.
- **DailyPlanner** / **Scheduler** — Stateless service that reads an **Owner**, optional **Pet**, and tasks, then produces an ordered plan plus per-row reasons (`build_plan`, `explain_placement`). **DailyPlanner** in the UML corresponds to the **`Scheduler`** implementation (subclass **`DailyPlanner`** kept as an alias).

Structurally, this separates **data** (Owner → Pet → Task) from **behavior** (planning). The Mermaid diagram in Step 3 matches this split.

**b. Design changes**

**Planned model tweak (output shape):** I still expect to add something like **ScheduledItem** / **PlanEntry** (task + start time or slot + explanation) once the scheduler is real, because a backlog **Task** is not the same as a placed item on the timeline. That is separate from the four-class UML, which stays the core blueprint.

**Refinements after reviewing `pawpal_system.py` (Step 5):** I had an AI assistant review the skeleton and applied small fixes so relationships and accessors match the UML intent:

- **Bidirectional Owner ↔ Pet:** Empty `add_pet` stubs risked an owner's list and a pet's `owner` field getting out of sync. `add_pet` now appends the pet to the owner and sets `pet.owner = self`.
- **Pet ↔ Task:** `add_task` / `get_tasks` now append and return the pet's task list instead of no-ops, so the backlog is usable from code and tests.
- **Getter stubs:** `get_pets`, `get_tasks`, and `available_minutes` used to fall through with `pass` and would have returned `None` by mistake; they now return the underlying values.
- **Task helpers:** `duration`, `priority_rank`, and `summary` are implemented with simple rules so sorting and UI strings work; unknown priority strings default to a middle rank.
- **Potential bottleneck (documented, not a bug):** `build_plan(owner, pet, tasks)` takes both `pet` and a separate `tasks` list. That could duplicate `pet.tasks` if callers are careless. The class docstring notes that callers should pass the same tasks they associate with the pet (e.g. `pet.get_tasks()`) until we refactor to a single source of truth.
- **Scheduling:** `Scheduler.build_plan` and `explain_placement` are implemented in `pawpal_system.py` and exercised from **`main.py`**. **`app.py`** is still the course **starter** Streamlit shell (tasks as dicts, “Generate schedule” not wired)—**Phase 6 UI polish** is intentionally not done yet so skipped modules can be completed first.


---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers **minutes available**, **task priority**, **duration**, **completion** (pending only), optional **`due_time` (HH:MM)** for ordering, and **recurrence** when the owner finalizes a task (daily/weekly spawns the next instance). **Priority** still breaks ties among tasks with the same due window so urgent care is not buried; **due_time** surfaces conflicts when two pending tasks claim the exact same clock time.

**b. Tradeoffs**

**Exact duplicate due-time vs overlapping intervals:** The lightweight conflict check flags **only identical `due_time` strings** on pending tasks—it does not model two tasks at `09:00` and `09:15` with **long durations** that could still overlap in real life. That keeps the rule **simple to explain** in warnings and avoids parsing duration against a global clock for every pair (which would be more accurate but heavier and easier to get wrong in the UI).

That tradeoff is **reasonable** for a teaching MVP: pet owners get a clear signal when they have **two things literally scheduled for 09:00**; true overlap detection could be added later using each task’s **duration** and a timeline data structure.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
