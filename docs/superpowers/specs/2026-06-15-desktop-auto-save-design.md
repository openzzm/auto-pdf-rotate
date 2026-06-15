# Desktop File Selection And Auto-Save Design

## Goal

Replace browser uploads and result downloads with a desktop-only workflow that selects a PDF by native file dialog and automatically writes the corrected PDF beside the source file.

## Workflow

1. The user clicks the PDF selection area.
2. The frontend calls the pywebview desktop API when available, otherwise it calls the local Flask selection endpoint.
3. Python opens a native PDF file picker and receives the absolute source path.
4. Python creates a job whose output path is:
   `source directory/source stem_已修正方向版.pdf`
5. The existing worker processes the source file directly.
6. The frontend polls the existing job status endpoint.
7. On completion, the result panel displays the automatically saved path. There is no download action.

## Constraints

- Browsers do not expose local absolute paths, so ordinary browser mode asks the local Python backend to open the native file picker.
- If an output file already exists, processing overwrites it.
- Source files must never be modified.
- Job cleanup on shutdown must only remove files under `JOB_ROOT`; automatically saved output files remain.

## Backend Changes

- Add `DesktopApi.select_pdf()` and `/api/select-pdf` to open the native picker and create a job.
- Extract job creation into a reusable `create_path_job(source_path)` function.
- `process_pdf` writes directly to the source directory.
- Remove browser upload and download API routes.
- Store the saved output path in public job status.

## Frontend Changes

- Remove the hidden file input and download link.
- Clicking the selection area invokes `window.pywebview.api.select_pdf()` or the local Flask selection endpoint.
- Start polling immediately after selection.
- On completion, show the saved output path.

## Testing

- Source path produces the expected sibling output path.
- Creating a path job records source/output/name and starts processing.
- Output outside `JOB_ROOT` survives shutdown cleanup.
- Existing rotation and shutdown cleanup regressions continue to pass.
