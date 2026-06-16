# Auto PDF Rotate

[简体中文](README.zh-CN.md)

A local Windows tool that detects sideways and upside-down pages in scanned PDF documents and creates a corrected copy beside the source file.

The application runs entirely on your computer. It does not upload documents, expose a download endpoint, or alter the original PDF.

## Features

- Detects page orientation with RapidOCR and ONNX Runtime.
- Preserves the original PDF and saves a corrected sibling file.
- Supports selecting PDFs by clicking the dropzone or dragging a PDF onto it.
- Uses conservative confidence thresholds to leave uncertain pages unchanged.
- Retries difficult pages at a higher rendering resolution.
- Shows progress, elapsed time, average page time, and estimated remaining time.
- Provides English and Simplified Chinese documentation; English is the default README.
- Provides browser mode and a portable Windows desktop build.
- Cleans worker threads, task metadata, and temporary files when the application closes.

## Output

Selecting:

```text
document.pdf
```

creates:

```text
document_已修正方向版.pdf
```

in the same directory. The original file is not modified.

## Requirements

- Windows 10 or Windows 11
- Python 3.12 recommended

## Run From Source

```powershell
git clone https://github.com/openzzm/auto-pdf-rotate.git
cd auto-pdf-rotate
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:8765` after the server starts.

On Windows, `启动网页.bat` can also start browser mode. In the portable desktop app, drag a PDF onto the dropzone or click it to choose a file. Browser drag-and-drop cannot expose the source folder path reliably, so browser mode keeps the click-to-select fallback.

## Build The Portable Application

Install build dependencies:

```powershell
python -m pip install -r requirements-build.txt
```

Build the PyInstaller `onedir` package:

```powershell
.\build-portable.ps1 -PythonExecutable "C:\Path\To\Python312\python.exe"
```

The portable application is generated at:

```text
release\AutoPDFRotate-Portable\AutoPDFRotate.exe
```

Copy the entire `AutoPDFRotate-Portable` directory when moving the application to another computer.

## Tests

```powershell
python -m unittest discover -s tests -v
```

The test suite covers rotation decisions, output naming, automatic sibling-file saving, cleanup behavior, and the desktop bridge.

## How It Works

1. Render each page at a lightweight analysis resolution.
2. Detect text regions and classify their orientation.
3. Rotate only when vote count, confidence, and margin thresholds are met.
4. Retry sparse or conflicting pages at a higher resolution.
5. Save the corrected PDF and an internal analysis report.
6. Remove temporary task data when the service closes.

## Project Structure

```text
app.py                  Flask server, PDF processing, desktop startup
templates/index.html    Application interface
static/app.js           UI behavior
static/style.css        Interface styling
tests/                  Automated regression tests
portable.spec           PyInstaller configuration
build-portable.ps1      Portable build script
```

## Privacy

All PDF processing is local. Temporary analysis reports are stored under `jobs` while the application is running and are deleted during normal shutdown. Corrected PDF files are retained beside their source files.

## Known Limitations

- Text-free pages and unusual layouts may not provide enough orientation evidence.
- The desktop build targets Windows x64.
- Closing the process forcibly may prevent graceful cleanup.
