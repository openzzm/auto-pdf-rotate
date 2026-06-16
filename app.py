import json
import os
import re
import shutil
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path

BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
APP_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else BUNDLE_ROOT
sys.path.insert(0, str(BUNDLE_ROOT / "vendor"))

import cv2
import fitz
import numpy as np
from flask import Flask, jsonify, render_template
from rapidocr_onnxruntime import RapidOCR


app = Flask(
    __name__,
    template_folder=str(BUNDLE_ROOT / "templates"),
    static_folder=str(BUNDLE_ROOT / "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024
JOBS = {}
JOBS_LOCK = threading.Lock()
SHUTDOWN_EVENT = threading.Event()
WORKERS = []
WORKERS_LOCK = threading.Lock()
JOB_ROOT = APP_ROOT / "jobs"
if getattr(sys, "frozen", False):
    shutil.rmtree(JOB_ROOT, ignore_errors=True)
JOB_ROOT.mkdir(exist_ok=True)
OCR = RapidOCR()
INVALID_FILENAME_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class DesktopApi:
    def __init__(self):
        self.window = None

    def select_pdf(self):
        source = select_pdf_path(self.window)
        if not source:
            return {"ok": False, "cancelled": True}
        try:
            return {"ok": True, "job_id": create_path_job(source), "source": str(source)}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def start_pdf_path(self, source):
        source = Path(source)
        try:
            return {"ok": True, "job_id": create_path_job(source), "source": str(source)}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}


def setup_desktop_drag_and_drop(window, desktop_api):
    from webview.dom import DOMEventHandler

    def emit(name, detail):
        window.evaluate_js(
            "window.dispatchEvent(new CustomEvent("
            + json.dumps(name)
            + ", { detail: "
            + json.dumps(detail, ensure_ascii=False)
            + " }));"
        )

    def prevent_default(_event):
        return None

    def on_drop(event):
        files = event.get("dataTransfer", {}).get("files", [])
        source = None
        for file in files:
            path = file.get("pywebviewFullPath") or file.get("path")
            if path and Path(path).suffix.lower() == ".pdf":
                source = path
                break
        if not source:
            emit("pdf-drop-error", {"message": "请拖拽有效的 PDF 文件，或点击选择文件"})
            return
        emit("pdf-path-selected", desktop_api.start_pdf_path(source))

    def attach_handlers():
        document = window.dom.document
        document.events.dragover += DOMEventHandler(prevent_default, prevent_default=True)
        document.events.drop += DOMEventHandler(on_drop, prevent_default=True)

    window.events.loaded += attach_handlers


def set_job(job_id, **values):
    with JOBS_LOCK:
        JOBS.setdefault(job_id, {}).update(values)


def output_filename_for(source_filename):
    source_name = source_filename.replace("\\", "/").rsplit("/", 1)[-1]
    stem = Path(source_name).stem.strip(" .") or "document"
    safe_stem = INVALID_FILENAME_CHARACTERS.sub("_", stem).strip(" .") or "document"
    return f"{safe_stem}_已修正方向版.pdf"


def output_path_for(source):
    source = Path(source)
    return source.with_name(output_filename_for(source.name))


def select_pdf_path(window=None):
    if window is not None:
        paths = window.create_file_dialog(dialog_type=10, file_types=("PDF 文件 (*.pdf)",))
        if not paths:
            return None
        return Path(paths[0] if isinstance(paths, (list, tuple)) else paths)

    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askopenfilename(filetypes=[("PDF 文件", "*.pdf")])
        return Path(selected) if selected else None
    finally:
        root.destroy()


def cleanup_jobs():
    for _ in range(5):
        shutil.rmtree(JOB_ROOT, ignore_errors=True)
        if not JOB_ROOT.exists():
            return
        time.sleep(0.2)


def shutdown_cleanup():
    SHUTDOWN_EVENT.set()
    with WORKERS_LOCK:
        workers = list(WORKERS)
    for worker in workers:
        if worker is not threading.current_thread() and worker.is_alive():
            worker.join()
    cleanup_jobs()
    with JOBS_LOCK:
        JOBS.clear()
    with WORKERS_LOCK:
        WORKERS.clear()


def run_self_test(report_path):
    test_doc = fitz.open()
    test_doc.new_page()
    test_bytes = test_doc.tobytes()
    test_doc.close()
    JOB_ROOT.mkdir(exist_ok=True)
    (JOB_ROOT / "self-test.tmp").write_text("temporary", encoding="utf-8")
    shutdown_cleanup()
    result = {
        "status": "ok",
        "pdf_bytes": len(test_bytes),
        "opencv": cv2.__version__,
        "ocr_loaded": OCR is not None,
        "jobs_removed": not JOB_ROOT.exists(),
    }
    Path(report_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def choose_rotation(image):
    def analyze_axis(angle, rotated):
        raw_boxes, _ = OCR(rotated, use_det=True, use_cls=False, use_rec=False)
        boxes = np.array(raw_boxes or [], dtype=np.float32)
        horizontal_score = 0.0
        vertical_score = 0.0
        horizontal_count = 0
        vertical_count = 0
        for box in boxes:
            width = max(np.linalg.norm(box[0] - box[1]), np.linalg.norm(box[2] - box[3]))
            height = max(np.linalg.norm(box[0] - box[3]), np.linalg.norm(box[1] - box[2]))
            if width > height * 1.3:
                horizontal_score += width
                horizontal_count += 1
            elif height > width * 1.3:
                vertical_score += height
                vertical_count += 1
        return {
            "angle": angle,
            "image": rotated,
            "boxes": boxes,
            "score": float(horizontal_score),
            "count": horizontal_count,
            "vertical_score": float(vertical_score),
            "vertical_count": vertical_count,
        }

    original = analyze_axis(0, image)
    axes = [original]
    # Normal pages need only one detection. Check the 90-degree axis only when
    # the first result is sparse or dominated by vertical text.
    needs_axis_check = (
        original["count"] < 4
        or original["vertical_count"] > original["count"]
        or original["vertical_score"] > original["score"] * 1.15
    )
    if needs_axis_check:
        axes.append(analyze_axis(90, cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)))

    best = max(axes, key=lambda item: item["score"])
    if best["angle"] == 90 and best["count"] < 4:
        best = original

    crops = OCR.get_crop_img_list(best["image"], best["boxes"]) if len(best["boxes"]) else []
    # Large crops carry more useful direction evidence; cap the batch for predictable speed.
    crops = sorted(crops, key=lambda crop: crop.shape[0] * crop.shape[1], reverse=True)[:24]
    _, classifications, _ = OCR.text_cls(crops) if crops else ([], [], 0)
    reliable = [item for item in classifications if float(item[1]) >= 0.8]
    upright = sum(float(item[1]) for item in reliable if item[0] == "0")
    upside_down = sum(float(item[1]) for item in reliable if item[0] == "180")

    angle = best["angle"]
    if len(reliable) >= 4 and upside_down >= 2.8 and upside_down > upright * 1.6:
        angle = (angle + 180) % 360

    details = {
        "angle": angle,
        "axis_scores": [
            {
                "angle": item["angle"],
                "score": round(item["score"], 2),
                "count": item["count"],
                "vertical_score": round(item["vertical_score"], 2),
                "vertical_count": item["vertical_count"],
            }
            for item in axes
        ],
        "direction_votes": {
            "upright": round(upright, 2),
            "upside_down": round(upside_down, 2),
            "reliable": len(reliable),
        },
    }
    return angle, details


def render_page(page, scale):
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
    image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)


def needs_high_resolution_retry(angle, analysis):
    votes = analysis["direction_votes"]
    return (
        angle == 0
        and votes["reliable"] >= 4
        and votes["upside_down"] >= 3
        and votes["upside_down"] > votes["upright"] * 1.2
    )


def process_pdf(job_id, source, output):
    started_at = time.time()
    doc = None
    try:
        doc = fitz.open(source)
        changes = []
        details = []
        total = doc.page_count
        set_job(
            job_id,
            status="processing",
            total=total,
            current=0,
            elapsed_seconds=0,
            average_page_seconds=0,
            eta_seconds=None,
            message="正在分析页面方向",
        )

        for index, page in enumerate(doc):
            if SHUTDOWN_EVENT.is_set():
                raise InterruptedError("程序正在退出")
            image = render_page(page, 0.75)
            angle, analysis = choose_rotation(image)
            if needs_high_resolution_retry(angle, analysis):
                retry_angle, retry_analysis = choose_rotation(render_page(page, 1.0))
                retry_analysis["high_resolution_retry"] = True
                angle, analysis = retry_angle, retry_analysis
            if angle:
                page.set_rotation((page.rotation + angle) % 360)
                changes.append({"page": index + 1, "rotation": angle})
            details.append({"page": index + 1, "rotation": angle, "analysis": analysis})
            elapsed = time.time() - started_at
            completed = index + 1
            average = elapsed / completed
            set_job(
                job_id,
                current=completed,
                progress=round(completed * 100 / total),
                elapsed_seconds=round(elapsed, 1),
                average_page_seconds=round(average, 2),
                eta_seconds=round(average * (total - completed), 1),
                message=f"正在分析第 {completed} / {total} 页",
            )

        doc.save(output, garbage=4, deflate=True)
        doc.close()
        doc = None
        JOB_ROOT.mkdir(exist_ok=True)
        report = JOB_ROOT / f"{job_id}.json"
        report.write_text(
            json.dumps({"pages": total, "changes": changes, "details": details}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        set_job(
            job_id,
            status="done",
            progress=100,
            elapsed_seconds=round(time.time() - started_at, 1),
            eta_seconds=0,
            changes=changes,
            saved_path=str(output),
            message=f"处理完成，共自动旋转 {len(changes)} 页",
        )
    except Exception as exc:
        if not SHUTDOWN_EVENT.is_set():
            set_job(
                job_id,
                status="error",
                elapsed_seconds=round(time.time() - started_at, 1),
                message=f"处理失败：{exc}",
            )
    finally:
        if doc is not None:
            doc.close()


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/select-pdf")
def select_pdf():
    source = select_pdf_path()
    if not source:
        return jsonify({"ok": False, "cancelled": True})
    try:
        return jsonify({"ok": True, "job_id": create_path_job(source), "source": str(source)})
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400


def create_path_job(source):
    source = Path(source).resolve()
    if not source.is_file() or source.suffix.lower() != ".pdf":
        raise ValueError("请选择有效的 PDF 文件")
    job_id = uuid.uuid4().hex
    output = output_path_for(source)
    set_job(
        job_id,
        status="queued",
        progress=0,
        current=0,
        total=0,
        elapsed_seconds=0,
        average_page_seconds=0,
        eta_seconds=None,
        source=str(source),
        output=str(output),
        name=output.name,
        saved_path=str(output),
    )
    worker = threading.Thread(target=process_pdf, args=(job_id, str(source), str(output)), daemon=True)
    with WORKERS_LOCK:
        WORKERS.append(worker)
    worker.start()
    return job_id


@app.get("/api/jobs/<job_id>")
def job_status(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "任务不存在"}), 404
        return jsonify({key: value for key, value in job.items() if key != "output"})


if __name__ == "__main__":
    if getattr(sys, "frozen", False) and "--self-test" in sys.argv:
        run_self_test(APP_ROOT / "self-test.json")
    elif getattr(sys, "frozen", False):
        import webview
        from werkzeug.serving import make_server

        desktop_api = DesktopApi()
        server = make_server("127.0.0.1", 8765, app, threaded=True)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        window = webview.create_window(
            "PDF 页面方向自动修正",
            "http://127.0.0.1:8765/?desktop=1",
            js_api=desktop_api,
            width=1180,
            height=780,
            min_size=(820, 620),
        )
        desktop_api.window = window
        setup_desktop_drag_and_drop(window, desktop_api)
        try:
            webview.start()
        finally:
            server.shutdown()
            shutdown_cleanup()
    else:
        if os.environ.get("OPEN_BROWSER") == "1":
            threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:8765")).start()
        try:
            app.run(host="127.0.0.1", port=8765, threaded=True)
        finally:
            shutdown_cleanup()
