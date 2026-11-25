"""Local study app for the eight-week ML engineering program.

    pip install -r requirements-app.txt
    streamlit run app/study_app.py          # opens http://localhost:8501

It reads course.json and the lesson Markdown, and reads and writes the same progress files as
`python wb.py` (progress/progress.json, progress/notes.md), so the app and the CLI always agree.
It runs only on your machine (bound to 127.0.0.1 by .streamlit/config.toml).
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import coursedocs as cd  # noqa: E402

# Mermaid 11.4.1 (MIT, app/static/MERMAID_LICENSE) is bundled so diagrams render offline. Streamlit serves
# app/static/ at /app/static/ because .streamlit/config.toml sets server.enableStaticServing.
MERMAID_JS = "/app/static/mermaid.min.js"
WEEK_THEMES = {
    1: "From research code to software",
    2: "Data: SQL, pandas, quality, features, baselines",
    3: "Evaluation you can defend",
    4: "Time-series modelling and model choice",
    5: "Inference, artifacts and a prediction API",
    6: "Containers, CI/CD and one cloud deployment",
    7: "Operating a model",
    8: "Finish, document, explain",
}

st.set_page_config(page_title="ML Engineering Program", page_icon=":material/school:", layout="wide")


# --------------------------------------------------------------------------- helpers
def go(**params: str) -> None:
    st.query_params.clear()
    st.query_params.update({k: v for k, v in params.items() if v})
    st.rerun()


def render_mermaid(source: str) -> None:
    html = f"""
    <div class="mermaid">{source.replace("<", "&lt;")}</div>
    <script src="{MERMAID_JS}"></script>
    <script>
      mermaid.initialize({{ startOnLoad: false, theme: "neutral", securityLevel: "strict" }});
      mermaid.run();
    </script>"""
    # Mermaid source comes from the course's own Markdown files (trusted, '<' escaped), never from user input.
    st.iframe(html, height="content")  # sizes the frame to the rendered diagram


def render_document(path: Path) -> None:
    text = cd.rewrite_links(path.read_text(), path)
    for block in cd.split_blocks(text, path.parent):
        if block.kind == "mermaid":
            render_mermaid(block.text)
        elif block.kind == "image":
            img = Path(block.text)
            if img.is_file():
                st.image(str(img), caption=block.alt or None, width="stretch")
            else:
                st.caption(f"(missing figure: {block.alt})")
        else:
            st.markdown(block.text, unsafe_allow_html=False)


def unit_doc(unit: dict) -> Path | None:
    if not unit.get("path"):
        return None
    p = cd.ROOT / unit["path"] / "README.md"
    return p if p.is_file() else None


def flag_editor(unit: dict, progress: dict, key_prefix: str) -> None:
    entry = progress.get("units", {}).get(unit["id"], {})
    cols = st.columns(len(cd.FLAGS))
    for col, flag in zip(cols, cd.FLAGS):
        current = bool(entry.get(flag))
        new = col.checkbox(cd.FLAG_LABELS[flag], value=current, key=f"{key_prefix}-{unit['id']}-{flag}")
        if new != current:
            cd.set_flag(unit["id"], flag, new)
            st.rerun()


def status_badge(unit: dict, progress: dict) -> str:
    p = progress.get("units", {}).get(unit["id"], {})
    if p.get("independent"):
        return ":green-badge[independent]"
    if p.get("guided"):
        return ":blue-badge[guided]"
    if p.get("reading"):
        return ":gray-badge[read]"
    return ":gray-badge[not started]"


# --------------------------------------------------------------------------- pages
def page_today(units: list[dict], progress: dict) -> None:
    st.title("ML Engineering Program")
    st.caption("Eight weeks, six core days and one review day per week. Progress is stored in progress/.")
    nxt = cd.next_unit(units, progress)
    done = progress.get("units", {})
    counts = Counter(f for u in done.values() for f in cd.FLAGS if u.get(f))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sessions", len(units))
    c2.metric("Guided practice done", counts["guided"])
    c3.metric("Independent skill shown", counts["independent"])
    c4.metric("Marked for review", counts["review"])

    st.subheader("Next session")
    if nxt is None:
        st.success("Every session is marked done. See STATUS.md and the retrospective (w8d7).")
    else:
        with st.container(border=True):
            st.markdown(f"**`{nxt['id']}`** — {nxt['title']}  \nWeek {nxt['week']}, day {nxt['day']}")
            st.markdown(f"**Objective.** {nxt['objective']}")
            st.markdown(f"**Deliverable.** {nxt['deliverable']}")
            st.markdown(f"**Prerequisites.** {nxt['prerequisites']}")
            if st.button("Open this session", type="primary"):
                go(page="unit", unit=nxt["id"])

    st.subheader("Weeks")
    for week, theme in WEEK_THEMES.items():
        wk = [u for u in units if u["week"] == week]
        n_done = sum(1 for u in wk if done.get(u["id"], {}).get("guided") or done.get(u["id"], {}).get("independent"))
        st.progress(n_done / len(wk), text=f"Week {week} — {theme}: {n_done}/{len(wk)} sessions done")


def page_schedule(units: list[dict], progress: dict) -> None:
    st.title("Schedule")
    week = st.segmented_control("Week", list(WEEK_THEMES), default=1, format_func=lambda w: f"Week {w}")
    if week is None:
        return
    st.caption(WEEK_THEMES[week])
    for unit in [u for u in units if u["week"] == week]:
        with st.container(border=True):
            left, right = st.columns([5, 1])
            left.markdown(f"**Day {unit['day']} · `{unit['id']}`** {status_badge(unit, progress)}  \n{unit['title']}")
            left.caption(unit["objective"])
            if right.button("Open", key=f"open-{unit['id']}"):
                go(page="unit", unit=unit["id"])


def page_unit(units: list[dict], progress: dict, unit_id: str) -> None:
    unit = next((u for u in units if u["id"] == unit_id), None)
    if unit is None:
        st.error(f"Unknown session {unit_id!r}.")
        return
    st.title(unit["title"])
    st.caption(f"`{unit['id']}` · Week {unit['week']}, day {unit['day']} · content status: {unit['status']}")
    flag_editor(unit, progress, "unit")

    tab_lesson, tab_checks, tab_more, tab_notes = st.tabs(["Lesson", "Checks", "Hints & solutions", "Notes"])
    with tab_lesson:
        doc = unit_doc(unit)
        if doc:
            render_document(doc)
        else:
            st.info("This session has no lesson page.")

    with tab_checks:
        dirs = cd.check_dirs(unit["path"]) if unit.get("path") else []
        if not dirs:
            st.info("No automated checks for this session (written or rubric-graded work).")
        st.caption("Checks grade the files in your lab/ or challenge/ folder. Passing is guided practice, not mastery.")
        for d in dirs:
            rel = d.relative_to(cd.ROOT).as_posix()
            if st.button(f"Run {rel}", key=f"run-{rel}"):
                with st.spinner(f"Running {rel} ..."):
                    result = cd.run_checks(d)
                (st.success if result.passed else st.error)(result.summary)
                if result.passed and d.name == "checks":
                    st.caption("You can now tick 'Guided practice completed' above.")
                with st.expander("Full output", expanded=not result.passed):
                    st.code(result.output[-20000:] or "(no output)", language="text")

    with tab_more:
        base = cd.ROOT / unit["path"] if unit.get("path") else None
        hints = sorted(base.glob("hints/*.md")) if base else []
        for h in hints:
            with st.expander(f"Hint: {h.stem.replace('_', ' ')}"):
                render_document(h)
        extra = [p for p in (base / "assessment.md", base / "challenge" / "README.md") if base and p.is_file()]
        for p in extra:
            with st.expander(p.relative_to(base).as_posix()):
                render_document(p)
        sol = cd.ROOT / "solutions" / unit["path"] if unit.get("path") else None
        if sol and sol.is_dir():
            st.warning("Solutions are for after a real attempt. Opening them first turns the session into reading.")
            if st.toggle("Show solution documents", key=f"sol-{unit['id']}"):
                for p in sorted(sol.rglob("*.md")):
                    if "mutants" in p.parts:
                        continue
                    with st.expander(p.relative_to(sol).as_posix()):
                        render_document(p)

    with tab_notes:
        text = st.text_area("Add a dated note (what tripped you up, what to revisit)", key=f"note-{unit['id']}")
        if st.button("Save note", disabled=not text.strip()):
            cd.append_note(unit["id"], text)
            st.success("Saved to progress/notes.md")


def page_handbook() -> None:
    st.title("Handbook")
    sections = cd.handbook_sections()
    labels = [title for _, title, _ in sections]
    choice = st.selectbox("Section", labels, index=0)
    path = sections[labels.index(choice)][2]
    render_document(path)


def page_progress(units: list[dict], progress: dict) -> None:
    st.title("Progress")
    done = progress.get("units", {})
    rows = [
        {"session": u["id"], "week": u["week"], "title": u["title"],
         **{cd.FLAG_LABELS[f]: bool(done.get(u["id"], {}).get(f)) for f in cd.FLAGS}}
        for u in units
    ]
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption("Same data as `python wb.py status`. Edit flags on each session's page.")
    if cd.NOTES.is_file():
        with st.expander("Your notes (progress/notes.md)"):
            st.markdown(cd.NOTES.read_text())


def page_doc(path: Path) -> None:
    st.caption(f"`{path.relative_to(cd.ROOT).as_posix()}`")
    render_document(path)


# --------------------------------------------------------------------------- main
def main() -> None:
    units = cd.load_units()
    progress = cd.load_progress()
    params = st.query_params

    with st.sidebar:
        st.header("ML Engineering")
        for label, page in [("Today", "today"), ("Schedule", "schedule"), ("Handbook", "handbook"),
                            ("Progress", "progress"), ("Project brief", "project"), ("Status", "status")]:
            if st.button(label, width="stretch", key=f"nav-{page}"):
                go(page=page)
        st.divider()
        st.caption("Terminal equivalent: `python wb.py next | check | mark | note`")

    doc = cd.safe_doc(params.get("doc"))
    page = params.get("page", "today")
    if doc is not None:
        page_doc(doc)
    elif page == "schedule":
        page_schedule(units, progress)
    elif page == "unit":
        page_unit(units, progress, params.get("unit", ""))
    elif page == "handbook":
        page_handbook()
    elif page == "progress":
        page_progress(units, progress)
    elif page == "project":
        page_doc(cd.ROOT / "project" / "README.md")
    elif page == "status":
        page_doc(cd.ROOT / "STATUS.md")
    else:
        page_today(units, progress)


main()
