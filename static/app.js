const DEFAULT_LANGUAGE = "en";
const LANGUAGE_STORAGE_KEY = "auto-pdf-rotate-language";
const SUPPORTED_LANGUAGES = ["en", "zh-CN"];

const selectFile = document.querySelector("#selectFile");
const startupLoading = document.querySelector("#startupLoading");
const languageSelect = document.querySelector("#languageSelect");
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
let translations = {};
let currentJob = null;
let currentLanguage = normalizeLanguage(localStorage.getItem(LANGUAGE_STORAGE_KEY));
const isDesktop = new URL(window.location.href).searchParams.get("desktop") === "1";

initializeApp();

async function initializeApp() {
  await loadLanguage(currentLanguage);
  applyLanguage();
  bindEvents();
  initializeInterface();
}

function bindEvents() {
  languageSelect.addEventListener("change", async () => {
    currentLanguage = normalizeLanguage(languageSelect.value);
    localStorage.setItem(LANGUAGE_STORAGE_KEY, currentLanguage);
    await loadLanguage(currentLanguage);
    applyLanguage();
    if (currentJob) renderJob(currentJob);
  });

  selectFile.addEventListener("click", async () => {
    selectFile.disabled = true;
    error.classList.add("hidden");
    result.classList.add("hidden");
    try {
      const response = await selectPdf();
      startJobFromResponse(response);
    } catch (e) {
      showError(e.message);
    }
  });

  selectFile.addEventListener("dragover", event => {
    event.preventDefault();
    if (!selectFile.disabled) selectFile.classList.add("drag-over");
  });

  selectFile.addEventListener("dragleave", event => {
    if (!selectFile.contains(event.relatedTarget)) {
      selectFile.classList.remove("drag-over");
    }
  });

  selectFile.addEventListener("drop", async event => {
    event.preventDefault();
    selectFile.classList.remove("drag-over");
    error.classList.add("hidden");
    result.classList.add("hidden");
    const file = event.dataTransfer?.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      showError(t("error.invalidDrop"));
      return;
    }
    if (isDesktop) {
      const path = file.pywebviewFullPath || file.path;
      if (!path) return;
      selectFile.disabled = true;
      try {
        await waitForDesktopApi();
        startJobFromResponse(await window.pywebview.api.start_pdf_path(path, currentLanguage));
      } catch (e) {
        showError(e.message);
      }
      return;
    }
    showError(t("error.browserDropNoPath"));
  });

  window.addEventListener("pdf-path-selected", event => {
    selectFile.disabled = true;
    error.classList.add("hidden");
    result.classList.add("hidden");
    try {
      startJobFromResponse(event.detail);
    } catch (e) {
      showError(e.message);
    }
  });

  window.addEventListener("pdf-drop-error", event => {
    showError(t(event.detail.key || "error.invalidDrop", event.detail.params || {}));
  });
}

function normalizeLanguage(language) {
  return SUPPORTED_LANGUAGES.includes(language) ? language : DEFAULT_LANGUAGE;
}

async function loadLanguage(language) {
  const response = await fetch(`/static/locales/${language}.json`);
  if (!response.ok) throw new Error(`Failed to load language: ${language}`);
  translations = await response.json();
}

function applyLanguage() {
  document.documentElement.lang = currentLanguage;
  document.title = t("app.title");
  window.autoPdfRotateLanguage = currentLanguage;
  languageSelect.value = currentLanguage;
  document.querySelectorAll("[data-i18n]").forEach(element => {
    element.textContent = t(element.dataset.i18n);
  });
}

function t(key, params = {}) {
  const template = translations[key] || key;
  return Object.entries(params).reduce(
    (text, [name, value]) => text.replaceAll(`{${name}}`, value),
    template,
  );
}

function startJobFromResponse(response) {
  if (response.cancelled) {
    selectFile.disabled = false;
    return;
  }
  if (!response.ok) {
    throw new Error(t(response.message_key || "error.selectFailed", response.message_params || {}));
  }

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
}

async function selectPdf() {
  if (isDesktop) {
    await waitForDesktopApi();
    return window.pywebview.api.select_pdf(currentLanguage);
  }
  return selectPdfFromLocalServer();
}

async function initializeInterface() {
  try {
    if (isDesktop) await waitForDesktopApi();
    setInterfaceReady();
  } catch (e) {
    startupLoading.querySelector("strong").textContent = t("startup.failed");
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
        () => reject(new Error(t("error.desktopApiTimeout"))),
        10000,
      );
      window.addEventListener("pywebviewready", () => {
        clearTimeout(timeout);
        if (typeof window.pywebview?.api?.select_pdf === "function") {
          resolve();
        } else {
          reject(new Error(t("error.desktopApiMissing")));
        }
      }, { once: true });
    });
  }
  return desktopApiReadyPromise;
}

async function selectPdfFromLocalServer() {
  const response = await fetch("/api/select-pdf", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ language: currentLanguage }),
  });
  const body = await response.json();
  if (!response.ok) throw new Error(t(body.message_key || "error.selectFailed", body.message_params || {}));
  return body;
}

async function poll(jobId) {
  try {
    const response = await fetch(`/api/jobs/${jobId}`);
    const job = await response.json();
    if (!response.ok) throw new Error(t(job.error_key || "error.jobNotFound"));
    currentJob = job;
    renderJob(job);
    if (job.status === "done") {
      clearInterval(timer);
      selectFile.disabled = false;
      return;
    }
    if (job.status === "error") {
      throw new Error(t(job.message_key || "error.processingFailed", job.message_params || {}));
    }
    setTimeout(() => poll(jobId), 800);
  } catch (e) {
    showError(e.message);
  }
}

function renderJob(job) {
  message.textContent = t(job.message_key || "job.queued", job.message_params || {});
  displayedElapsed = Math.max(displayedElapsed, job.elapsed_seconds || 0);
  average.textContent = job.average_page_seconds
    ? `${job.average_page_seconds.toFixed(2)} ${t("stats.seconds")}`
    : "--";
  eta.textContent = job.eta_seconds === 0
    ? "00:00"
    : job.eta_seconds
      ? formatDuration(job.eta_seconds)
      : t("stats.calculating");
  updateTimeDisplay();
  percent.textContent = `${job.progress || 0}%`;
  bar.style.width = `${job.progress || 0}%`;

  if (job.status === "done") {
    const pages = job.changes.map(change => change.page).join(currentLanguage === "zh-CN" ? "、" : ", ");
    const changeSummary = job.changes.length
      ? t("result.rotatedPages", { count: job.changes.length, pages })
      : t("result.noRotations");
    summary.textContent = `${changeSummary} ${t("result.totalTime", { duration: formatDuration(job.elapsed_seconds) })}`;
    savedPath.textContent = t("result.savedPath", { path: job.saved_path });
    result.classList.remove("hidden");
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
