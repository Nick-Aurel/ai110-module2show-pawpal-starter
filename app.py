import sys
from datetime import datetime

import pandas as pd
from streamlit.runtime.scriptrunner import get_script_run_ctx

# Do not `import streamlit` until we know we are inside `streamlit run`.
# `python app.py` has no ScriptRunContext; use suppress_warning=True so checking
# does not log the "missing ScriptRunContext" line (see Streamlit's get_script_run_ctx).
if get_script_run_ctx(suppress_warning=True) is None:
    print(
        "\nPawPal+ is a Streamlit app. Start it with:\n\n"
        "  streamlit run app.py\n",
        file=sys.stderr,
    )
    sys.exit(1)

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task


def _scheduler() -> Scheduler:
    return Scheduler()


def _inject_styles() -> None:
    st.markdown(
        """
<style>
    /* Warm, readable layout */
    .main .block-container {
        max-width: 900px;
        padding-top: 1.25rem;
        padding-bottom: 2rem;
    }
    .pawpal-hero {
        background: linear-gradient(135deg, #fff8f0 0%, #f0f4ff 55%, #f5fff8 100%);
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 14px;
        padding: 1.35rem 1.5rem 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .pawpal-hero h1 {
        font-family: system-ui, -apple-system, sans-serif;
        font-size: 1.85rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0 0 0.35rem 0;
        color: #1a1a1a;
    }
    .pawpal-hero .tagline {
        margin: 0;
        font-size: 1.02rem;
        color: #4a4a4a;
        line-height: 1.45;
    }
    .pawpal-muted {
        color: #6b6b6b;
        font-size: 0.92rem;
    }
</style>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

_inject_styles()

st.markdown(
    """
<div class="pawpal-hero">
    <h1>🐾 PawPal+</h1>
    <p class="tagline">Plan care for your pets in the time you actually have today.</p>
</div>
    """,
    unsafe_allow_html=True,
)

if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", minutes_available_today=90)
if "task_complete_flash" not in st.session_state:
    st.session_state.task_complete_flash = ""

owner: Owner = st.session_state.owner

with st.expander("About PawPal+", expanded=False):
    st.markdown(
        """
PawPal+ helps you list tasks, spot time clashes, and build a simple order for your day.
Your data stays in this browser session until you refresh.
        """
    )

# --- Owner ---
with st.container(border=True):
    st.markdown("### Your profile")
    st.caption("Who you are and how many minutes you can spend on pet care today.")
    col_o1, col_o2 = st.columns(2)
    with col_o1:
        name_in = st.text_input("Your name", value=owner.name, key="owner_name_input")
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

# --- Pets ---
with st.container(border=True):
    st.markdown("### Your pets")
    st.caption("Add each animal you want to plan for.")
    pet_name = st.text_input("Pet name", value="Mochi", key="new_pet_name")
    species = st.selectbox("Species", ["dog", "cat", "other"], key="new_pet_species")

    if st.button("Add pet", type="primary", key="add_pet_btn"):
        if not pet_name.strip():
            st.warning("Please enter a pet name.")
        else:
            pet = Pet(name=pet_name.strip(), species=species)
            owner.add_pet(pet)
            st.success(f"Added **{pet.name}** ({species}). You now have {len(owner.get_pets())} pet(s).")
            st.rerun()

    pets = owner.get_pets()
    if pets:
        df_pets = pd.DataFrame(
            [{"Name": p.name, "Species": p.species, "Open tasks": len(p.get_tasks())} for p in pets]
        )
        st.dataframe(df_pets, hide_index=True, use_container_width=True)
    else:
        st.info("No pets yet—add one above to start building a task list.")

st.divider()

# --- Tasks ---
st.markdown("### Tasks")
st.caption("Choose a pet, add tasks, then mark them done when finished. Recurring tasks roll forward automatically.")

if not pets:
    st.warning("Add a pet first, then you can attach tasks.")
else:
    pet_labels = [f"{p.name} ({p.species})" for p in pets]
    choice = st.selectbox("Which pet is this for?", range(len(pets)), format_func=lambda i: pet_labels[i])
    selected_pet = pets[choice]
    scheduler = _scheduler()

    if st.session_state.task_complete_flash:
        st.success(st.session_state.task_complete_flash)
        st.session_state.task_complete_flash = ""

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("What to do", value="Morning walk", key="task_title_input")
    with col2:
        duration = st.number_input(
            "Duration (minutes)", min_value=1, max_value=240, value=20, key="task_duration_input"
        )
    with col3:
        priority = st.selectbox(
            "Priority",
            ["low", "medium", "high"],
            index=2,
            format_func=lambda x: x.capitalize(),
            key="task_priority_input",
        )
    due_time = st.text_input(
        "Due time (optional)",
        value="",
        placeholder="09:00",
        key="task_due_time_input",
        help="24-hour time (HH:MM). Used to order and compare tasks.",
    )
    recurrence = st.selectbox(
        "Repeat",
        ["none", "daily", "weekly"],
        format_func=lambda x: "Does not repeat" if x == "none" else x.capitalize(),
        key="task_recurrence_input",
    )

    if st.button("Add task", type="primary", key="add_task_btn"):
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
            st.success(f"Added **{task.title}** for **{selected_pet.name}**.")
            st.rerun()
        except ValueError as e:
            st.warning(str(e))

    pending = [t for t in selected_pet.get_tasks() if not t.completed]
    sorted_pending = scheduler.sort_tasks_by_time(pending)
    conflict_notes = scheduler.find_due_time_conflicts(selected_pet.get_tasks())

    if conflict_notes:
        st.warning(
            "**Heads up — same time slot**\n\n"
            "Two or more tasks are set for the same clock time. Consider moving one "
            "or finishing one before the other.\n\n"
            + "\n\n".join(f"- {note}" for note in conflict_notes)
        )

    if sorted_pending:
        st.markdown(f"**Up next for {selected_pet.name}** · earliest first")
        df_tasks = pd.DataFrame(
            [
                {
                    "Due": t.due_time or "—",
                    "Task": t.title,
                    "Minutes": t.duration_minutes,
                    "Priority": t.priority.capitalize(),
                    "Repeat": t.recurrence.capitalize() if t.recurrence else "—",
                }
                for t in sorted_pending
            ]
        )
        st.dataframe(df_tasks, hide_index=True, use_container_width=True)

        st.markdown("**Mark a task complete**")
        st.caption("Daily or weekly tasks will create the next occurrence on the following day or week.")
        labels = [
            f"{t.title} · {t.due_time or 'any time'} · {t.priority.capitalize()}"
            for t in sorted_pending
        ]
        pick = st.selectbox(
            "Select task",
            range(len(sorted_pending)),
            format_func=lambda i: labels[i],
            key="complete_pick",
            label_visibility="collapsed",
        )
        if st.button("Mark complete", key="complete_btn"):
            task = sorted_pending[pick]
            try:
                nxt = selected_pet.finalize_recurring_task(task)
                if nxt:
                    st.session_state.task_complete_flash = (
                        f"Nice — “{task.title}” is done. Next {nxt.recurrence} task: **{nxt.due_date}**."
                    )
                else:
                    st.session_state.task_complete_flash = f"Marked “{task.title}” complete."
                st.rerun()
            except ValueError as e:
                st.warning(str(e))
    else:
        st.info(f"No open tasks for **{selected_pet.name}** yet.")

st.divider()

# --- Schedule ---
with st.container(border=True):
    st.markdown("### Today’s schedule")
    st.caption("Build a suggested order from your open tasks and the time you have.")
    owner_wide = _scheduler().find_due_time_conflicts(owner.get_all_tasks())
    if owner_wide and len(pets) > 1:
        with st.expander("Time conflicts across all pets", expanded=True):
            st.markdown(
                "These tasks share a due time across **all** your pets. "
                "Resolve them before combining everyone into one schedule."
            )
            for note in owner_wide:
                st.warning(note)

    c1, c2 = st.columns([1, 2])
    with c1:
        start_time = st.text_input("Start your day at", value="08:00", key="schedule_start", help="24-hour HH:MM")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        gen = st.button("Generate schedule", type="primary", key="gen_schedule_btn")

    if gen:
        try:
            datetime.strptime(start_time.strip(), "%H:%M")
        except ValueError:
            st.warning("Use 24-hour time like **08:00** or **14:30**.")
        else:
            sched = _scheduler()
            plan, phase4_warnings = sched.build_plan(owner, start_time=start_time.strip())
            if phase4_warnings:
                st.warning("\n\n".join(phase4_warnings))
            if plan:
                st.success(f"Here’s a **{len(plan)}-step** plan for today.")
                df_plan = pd.DataFrame(
                    [
                        {
                            "Start": row["start"],
                            "End": row["end"],
                            "Task": row["task"],
                            "Priority": str(row["priority"]).capitalize(),
                            "Minutes": row["duration_minutes"],
                            "Why here": row["reason"],
                        }
                        for row in plan
                    ]
                )
                st.dataframe(df_plan, hide_index=True, use_container_width=True)
            elif not phase4_warnings:
                st.info(
                    "Nothing fit in the time available—add tasks or increase **minutes available** above."
                )
            else:
                st.info("Adjust conflicting times or free more minutes, then try again.")

st.divider()
with st.expander("Technical notes (for developers)", expanded=False):
    st.markdown(
        """
The domain model lives in **`pawpal_system`**: **`Owner`** → **`Pet`** → **`Task`**.  
The UI keeps one **`Owner`** in **`st.session_state["owner"]`** so Streamlit reruns do not reset data.

**Scheduling:** **`Scheduler.sort_tasks_by_time`**, **`find_due_time_conflicts`**, and **`build_plan`** power ordering, warnings, and the day plan.
        """
    )
