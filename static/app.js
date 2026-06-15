const selectFile = document.querySelector("#selectFile");
const startupLoading = document.querySelector("#startupLoading");
const fileName = document.querySelector("#fileName");
const progressBox = document.querySelector("#progressBox");
const result = document.querySelector("#result");
const error = document.querySelector("#error");
const message = document.querySelector("#message");
const percent = document.querySelector("#percent");
const bar = document.querySelector("#bar");
const summary = document.querySelector("#summary");
const savedPath = document.querySelector("#savedPath");
const elapsed = document.querySelector("#elapsed");
const average = document.querySelector("#average");
const eta = document.querySelector("#eta");
let timer = null;
let displayedElapsed = 0;
let desktopApiReadyPromise = null;
const isDesktop = new URL(window.location.href).searchParams.get("desktop") === "1";

initializeInterface();

selectFile.addEventListener("click", async () => {
  selectFile.disabled = true;
  error.classList.add("hidden");
  result.classList.add("hidden");
  try {
    const response = await selectPdf();
    if (response.cancelled) {
      selectFile.disabled = false;
      return;
    }
    if (!response.ok) throw new Error(response.message || "选择文件失败");

    fileName.textContent = response.source;
    progressBox.classList.remove("hidden");
    displayedElapsed = 0;
    updateTimeDisplay();
    clearInterval(timer);
    timer = setInterval(() => {
      displayedElapsed += 1;
      updateTimeDisplay();
    }, 1000);
    poll(response.job_id);
  } catch (e) {
    showError(e.message);
  }
});

async function selectPdf() {
  if (isDesktop) {
    await waitForDesktopApi();
    return window.pywebview.api.select_pdf();
  }
  return selectPdfFromLocalServer();
}

async function initializeInterface() {
  try {
    if (isDesktop) await waitForDesktopApi();
    setInterfaceReady();
  } catch (e) {
    startupLoading.querySelector("strong").textContent = "初始化失败";
    startupLoading.querySelector("small").textContent = e.message;
    showError(e.message);
  }
}

function setInterfaceReady() {
  startupLoading.classList.add("hidden");
  selectFile.disabled = false;
}

function waitForDesktopApi() {
  if (typeof window.pywebview?.api?.select_pdf === "function") {
    return Promise.resolve();
  }
  if (!desktopApiReadyPromise) {
    desktopApiReadyPromise = new Promise((resolve, reject) => {
      const timeout = setTimeout(
        () => reject(new Error("桌面文件选择器初始化超时，请重新启动程序")),
        10000,
      );
      window.addEventListener("pywebviewready", () => {
        clearTimeout(timeout);
        if (typeof window.pywebview?.api?.select_pdf === "function") {
          resolve();
        } else {
          reject(new Error("桌面文件选择器初始化失败，请重新启动程序"));
        }
      }, { once: true });
    });
  }
  return desktopApiReadyPromise;
}

async function selectPdfFromLocalServer() {
  const response = await fetch("/api/select-pdf", { method: "POST" });
  const body = await response.json();
  if (!response.ok) throw new Error(body.message || "选择文件失败");
  return body;
}

async function poll(jobId) {
  try {
    const response = await fetch(`/api/jobs/${jobId}`);
    const job = await response.json();
    if (!response.ok) throw new Error(job.error);
    message.textContent = job.message || "正在准备";
    displayedElapsed = Math.max(displayedElapsed, job.elapsed_seconds || 0);
    average.textContent = job.average_page_seconds
      ? `${job.average_page_seconds.toFixed(2)} 秒`
      : "--";
    eta.textContent = job.eta_seconds === 0
      ? "00:00"
      : job.eta_seconds
        ? formatDuration(job.eta_seconds)
        : "计算中";
    updateTimeDisplay();
    percent.textContent = `${job.progress || 0}%`;
    bar.style.width = `${job.progress || 0}%`;
    if (job.status === "done") {
      const pages = job.changes.map(x => x.page).join("、");
      const changeSummary = job.changes.length
        ? `自动旋转了 ${job.changes.length} 页：第 ${pages} 页`
        : "未检测到需要旋转的页面";
      summary.textContent = `${changeSummary}；总耗时 ${formatDuration(job.elapsed_seconds)}`;
      savedPath.textContent = `已自动保存：${job.saved_path}`;
      result.classList.remove("hidden");
      clearInterval(timer);
      selectFile.disabled = false;
      return;
    }
    if (job.status === "error") throw new Error(job.message);
    setTimeout(() => poll(jobId), 800);
  } catch (e) {
    showError(e.message);
  }
}

function showError(text) {
  clearInterval(timer);
  error.textContent = text;
  error.classList.remove("hidden");
  selectFile.disabled = false;
}

function updateTimeDisplay() {
  elapsed.textContent = formatDuration(displayedElapsed);
}

function formatDuration(seconds) {
  const value = Math.max(0, Math.round(seconds || 0));
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  const secs = value % 60;
  return hours
    ? `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`
    : `${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}
