# Desktop Auto-Save Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace browser upload/download with native desktop PDF selection and automatic sibling-file saving.

**Architecture:** The pywebview API or local Flask selection endpoint opens a native file picker and delegates to a reusable path-job creator. Existing background processing and status polling remain, but outputs are written directly beside source PDFs and exposed in job status. The browser upload/download routes and controls are removed.

**Tech Stack:** Python, Flask, pywebview, JavaScript, unittest

---

### Task 1: Path Job Backend

**Files:**
- Modify: `app.py`
- Create: `tests/test_desktop_jobs.py`

- [ ] Write failing tests for sibling output naming, path-job creation, and desktop API cancellation.
- [ ] Run `python -X utf8 -m unittest tests.test_desktop_jobs -v` and confirm failures.
- [ ] Add `output_path_for`, `create_path_job`, and `DesktopApi.select_pdf`.
- [ ] Remove browser upload and download routes.
- [ ] Run backend tests and confirm they pass.

### Task 2: Desktop-Only Frontend

**Files:**
- Modify: `templates/index.html`
- Modify: `static/app.js`

- [ ] Remove file input, start button, and download link.
- [ ] Make the selection panel call `window.pywebview.api.select_pdf()`.
- [ ] Poll the returned job and show the automatically saved output path.
- [ ] Use the local Flask selection endpoint when pywebview is unavailable.
- [ ] Run JavaScript syntax validation.

### Task 3: Full Verification

**Files:**
- Verify: `app.py`
- Verify: `tests/*.py`

- [ ] Run all unit tests.
- [ ] Run Python and JavaScript syntax checks.
- [ ] Confirm shutdown cleanup does not delete sibling output files.
- [ ] Confirm no upload/download route or control remains.
