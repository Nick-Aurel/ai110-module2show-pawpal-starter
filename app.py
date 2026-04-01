from datetime import datetime

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
This app uses **`pawpal_system`**: your **Owner** and their **Pets** live in **`st.session_state`**
so they survive Streamlit reruns. Use **Add pet** / **Add task** to call **`add_pet`** and **`add_task`**.
"""
)

# --- Phase 3: persist Owner across reruns (Streamlit re-executes the script each interaction) ---
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", minutes_available_today=90)

owner: Owner = st.session_state.owner

with st.expander("Scenario", expanded=False):
    st.markdown(
        """
**PawPal+** plans pet care from tasks, priorities, and the time you have today.
"""
    )

st.divider()

st.subheader("Owner")
col_o1, col_o2 = st.columns(2)
with col_o1:
    name_in = st.text_input("Owner name", value=owner.name, key="owner_name_input")
with col_o2:
    mins_in = st.number_input(
        "Minutes available today",
        min_value=5,
        max_value=600,
        value=int(owner.minutes_available_today),
        step=5,
        key="owner_minutes_input",
    )
owner.name = name_in.strip() or owner.name
owner.minutes_available_today = int(mins_in)

st.subheader("Pets")
st.caption("Submitting **Add pet** creates a **`Pet`** and registers it with **`Owner.add_pet`**.")
pet_name = st.text_input("Pet name", value="Mochi", key="new_pet_name")
species = st.selectbox("Species", ["dog", "cat", "other"], key="new_pet_species")

if st.button("Add pet"):
    if not pet_name.strip():
        st.warning("Enter a pet name.")
    else:
        pet = Pet(name=pet_name.strip(), species=species)
        owner.add_pet(pet)
        st.success(f"Added **{pet.name}** ({pet.species}). `owner.get_pets()` now has {len(owner.get_pets())} pet(s).")
        st.rerun()

pets = owner.get_pets()
if pets:
    st.write("**Your pets** (in memory on this session)")
    st.table(
        [
            {"Name": p.name, "Species": p.species, "Tasks": len(p.get_tasks())}
            for p in pets
        ]
    )
else:
    st.info("No pets yet. Add one above — the **`Pet`** object is stored on **`Owner`** in session state.")

st.divider()

st.subheader("Tasks")
st.caption("Pick a pet, then **Add task** calls **`Pet.add_task(Task(...))`**.")
if not pets:
    st.warning("Add a pet first so tasks can be attached.")
else:
    pet_labels = [f"{p.name} ({p.species})" for p in pets]
    choice = st.selectbox("Pet for this task", range(len(pets)), format_func=lambda i: pet_labels[i])
    selected_pet = pets[choice]

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk", key="task_title_input")
    with col2:
        duration = st.number_input(
            "Duration (minutes)", min_value=1, max_value=240, value=20, key="task_duration_input"
        )
    with col3:
        priority = st.selectbox(
            "Priority", ["low", "medium", "high"], index=2, key="task_priority_input"
        )
    due_time = st.text_input(
        "Due time (optional HH:MM)",
        value="",
        placeholder="09:00",
        key="task_due_time_input",
        help="Used for ordering and conflict detection when two tasks share the same time.",
    )
    recurrence = st.selectbox(
        "Recurrence",
        ["none", "daily", "weekly"],
        key="task_recurrence_input",
    )

    if st.button("Add task"):
        try:
            kwargs: dict = {
                "title": task_title.strip() or "Untitled",
                "duration_minutes": int(duration),
                "priority": priority,
            }
            if due_time.strip():
                kwargs["due_time"] = due_time.strip()
            if recurrence != "none":
                kwargs["recurrence"] = recurrence
            task = Task(**kwargs)
            selected_pet.add_task(task)
            st.success(
                f"Task **{task.title}** added to **{selected_pet.name}**. "
                f"They now have {len(selected_pet.get_tasks())} task(s)."
            )
            st.rerun()
        except ValueError as e:
            st.warning(str(e))

    pending = [t for t in selected_pet.get_tasks() if not t.completed]
    if pending:
        st.write(f"**Tasks for {selected_pet.name}**")
        st.table(
            [
                {
                    "Title": t.title,
                    "Minutes": t.duration_minutes,
                    "Priority": t.priority,
                    "Summary": t.summary(),
                }
                for t in pending
            ]
        )
    else:
        st.info(f"No pending tasks on **{selected_pet.name}** yet.")

st.divider()

st.subheader("Build schedule")
st.caption("Uses **`Scheduler.build_plan`** across all pets on this owner.")
start_time = st.text_input("Day start (HH:MM)", value="08:00", key="schedule_start")

if st.button("Generate schedule"):
    try:
        datetime.strptime(start_time.strip(), "%H:%M")
    except ValueError:
        st.warning("Use 24-hour **HH:MM** (e.g. `08:00`).")
    else:
        scheduler = Scheduler()
        plan, phase4_warnings = scheduler.build_plan(owner, start_time=start_time.strip())
        if phase4_warnings:
            st.warning("\n\n".join(phase4_warnings))
        if plan:
            st.success(f"Planned **{len(plan)}** block(s).")
            st.table(
                [
                    {
                        "Start": row["start"],
                        "End": row["end"],
                        "Task": row["task"],
                        "Priority": row["priority"],
                        "Minutes": row["duration_minutes"],
                        "Why": row["reason"],
                    }
                    for row in plan
                ]
            )
        elif not phase4_warnings:
            st.info(
                "No blocks scheduled — add pending tasks and/or increase **minutes available**."
            )
        else:
            st.info("Fix due-time conflicts or free more minutes, then try again.")

st.divider()
with st.expander("Design note: form → model → rerun", expanded=False):
    st.markdown(
        """
**Add pet:** the UI calls **`Owner.add_pet(pet)`**, which appends the pet and sets **`pet.owner`**.

**Add task:** the UI builds a **`Task`** and calls **`pet.add_task(task)`**.

Streamlit **reruns** the whole script after each click, so we keep the single **`Owner`** (and its pets/tasks)
in **`st.session_state["owner"]`** instead of creating a new **`Owner()`** at the top every time.
"""
    )
