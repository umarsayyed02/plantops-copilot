const $ = (selector) => document.querySelector(selector);

const elements = {
  status: $("#system-status"),
  documentCount: $("#document-count"),
  documentList: $("#document-list"),
  fileInput: $("#file-input"),
  uploadZone: $("#upload-zone"),
  uploadStatus: $("#upload-status"),
  benchmark: $("#benchmark-summary"),
  hero: $("#hero"),
  conversation: $("#conversation"),
  form: $("#query-form"),
  input: $("#question-input"),
  submit: $("#submit-button"),
};

function node(tag, className, text) {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text !== undefined) item.textContent = text;
  return item;
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch (_) {
      // Keep the status-based message when the response is not JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}

function setSystemStatus(kind, label) {
  elements.status.className = `system-status ${kind}`;
  elements.status.lastElementChild.textContent = label;
}

async function loadHealth() {
  try {
    const health = await api("/health");
    const backend = health.embedding_backend === "fastembed" ? "Semantic" : "Baseline";
    setSystemStatus("online", `${backend} · ${health.chunks} chunks`);
    if (!health.uploads_enabled) {
      elements.fileInput.disabled = true;
      elements.uploadZone.classList.add("disabled");
      elements.uploadZone.querySelector("strong").textContent = "Demo library locked";
      elements.uploadZone.querySelector("strong + span").textContent = "Uploads are available when run locally";
      elements.uploadStatus.textContent = "Public demo mode protects the shared index.";
    }
  } catch (error) {
    setSystemStatus("error", "Service unavailable");
  }
}

function extensionLabel(source) {
  const extension = source.split(".").pop()?.toUpperCase();
  return extension && extension.length <= 4 ? extension : "DOC";
}

async function loadDocuments() {
  const documents = await api("/documents");
  elements.documentCount.textContent = documents.length;
  elements.documentList.replaceChildren();
  for (const document of documents) {
    const item = node("div", "document-item");
    item.append(node("span", "document-icon", extensionLabel(document.source)));
    const details = node("div");
    details.append(node("div", "document-name", document.source));
    details.append(node("div", "document-meta", `${document.chunks} indexed chunks`));
    item.append(details, node("span", "document-check", "✓"));
    elements.documentList.append(item);
  }
  if (!documents.length) {
    elements.documentList.append(node("p", "inline-status", "No documents indexed yet."));
  }
}

function metric(label, value) {
  const item = node("div", "metric");
  item.append(node("strong", "", value), node("span", "", label));
  return item;
}

async function loadBenchmark() {
  try {
    const benchmark = await api("/benchmark");
    elements.benchmark.replaceChildren();
    for (const result of benchmark.results) {
      const card = node("article", "benchmark-card");
      const header = node("header");
      header.append(
        node("h3", "", result.label),
        node("span", "benchmark-tag", result.name === "hash" ? "Fastest" : "Semantic")
      );
      const metrics = node("div", "metric-row");
      metrics.append(
        metric("Recall@5", result.metrics.recall_at_5.toFixed(2)),
        metric("MRR", result.metrics.mrr.toFixed(3)),
        metric("p95", `${result.metrics.latency_p95_ms.toFixed(1)}ms`)
      );
      card.append(header, metrics);
      elements.benchmark.append(card);
    }
    elements.benchmark.append(node("p", "benchmark-note", benchmark.note));
  } catch (error) {
    elements.benchmark.replaceChildren(node("p", "inline-status", error.message));
  }
}

function showConversation() {
  elements.hero.classList.add("hidden");
  elements.conversation.classList.add("active");
}

function addUserMessage(question) {
  showConversation();
  const wrapper = node("article", "message user");
  wrapper.append(node("div", "message-bubble", question));
  elements.conversation.append(wrapper);
}

function addThinking() {
  const wrapper = node("article", "message assistant thinking");
  wrapper.dataset.thinking = "true";
  wrapper.append(node("div", "assistant-mark", "PO"));
  const card = node("div", "answer-card");
  const label = node("span", "", "Searching indexed evidence");
  const dots = node("span", "thinking-dots");
  dots.append(node("span"), node("span"), node("span"));
  card.append(label, dots);
  wrapper.append(card);
  elements.conversation.append(wrapper);
  wrapper.scrollIntoView({ behavior: "smooth", block: "end" });
  return wrapper;
}

async function sendFeedback(button, question, answer, rating) {
  try {
    await api("/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, answer, rating, comment: null }),
    });
    button.parentElement.querySelectorAll("button").forEach((item) => item.classList.remove("selected"));
    button.classList.add("selected");
    button.textContent = rating === "positive" ? "Helpful ✓" : "Needs work ✓";
  } catch (error) {
    button.textContent = "Could not save";
  }
}

function addAssistantMessage(question, response) {
  const wrapper = node("article", "message assistant");
  wrapper.append(node("div", "assistant-mark", "PO"));
  const card = node("div", "answer-card");
  const body = node("div", "answer-body");
  body.append(node("p", "answer-text", response.answer));
  const meta = node("div", "answer-meta");
  meta.append(node("span", "meta-pill", `${Math.round(response.confidence * 100)}% evidence score`));
  meta.append(node("span", "meta-pill", response.generator));
  if (response.abstained) meta.append(node("span", "meta-pill warning", "Safely abstained"));
  body.append(meta);
  card.append(body);

  if (response.citations.length) {
    const citations = node("section", "citations");
    citations.append(node("h3", "", `${response.citations.length} evidence source${response.citations.length === 1 ? "" : "s"}`));
    const list = node("div", "citation-list");
    for (const citation of response.citations) {
      const item = node("article", "citation");
      const header = node("header");
      header.append(
        node("span", "", `[${citation.citation_id}] ${citation.source}`),
        node("span", "", `Page ${citation.page} · ${Math.round(citation.score * 100)}%`)
      );
      item.append(header, node("p", "", citation.excerpt));
      list.append(item);
    }
    citations.append(list);
    card.append(citations);
  }

  const footer = node("footer", "answer-footer");
  const positive = node("button", "feedback-button", "Helpful");
  positive.type = "button";
  positive.addEventListener("click", () => sendFeedback(positive, question, response.answer, "positive"));
  const negative = node("button", "feedback-button", "Needs work");
  negative.type = "button";
  negative.addEventListener("click", () => sendFeedback(negative, question, response.answer, "negative"));
  footer.append(positive, negative);
  card.append(footer);
  wrapper.append(card);
  elements.conversation.append(wrapper);
  wrapper.scrollIntoView({ behavior: "smooth", block: "end" });
}

function addErrorMessage(message) {
  addAssistantMessage("Request error", {
    answer: message,
    citations: [],
    confidence: 0,
    abstained: true,
    generator: "request-error",
  });
}

async function ask(question) {
  const cleaned = question.trim();
  if (!cleaned || elements.submit.disabled) return;
  addUserMessage(cleaned);
  elements.input.value = "";
  elements.input.style.height = "auto";
  elements.submit.disabled = true;
  const thinking = addThinking();
  try {
    const response = await api("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: cleaned }),
    });
    thinking.remove();
    addAssistantMessage(cleaned, response);
  } catch (error) {
    thinking.remove();
    addErrorMessage(error.message);
  } finally {
    elements.submit.disabled = false;
    elements.input.focus();
  }
}

async function upload(file) {
  if (!file || elements.fileInput.disabled) return;
  elements.uploadStatus.textContent = `Indexing ${file.name}…`;
  const formData = new FormData();
  formData.append("file", file);
  try {
    const result = await api("/documents/ingest", { method: "POST", body: formData });
    elements.uploadStatus.textContent = `Indexed ${result.chunks} chunks from ${result.documents} document${result.documents === 1 ? "" : "s"}.`;
    await Promise.all([loadDocuments(), loadHealth()]);
  } catch (error) {
    elements.uploadStatus.textContent = error.message;
  } finally {
    elements.fileInput.value = "";
  }
}

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  ask(elements.input.value);
});

elements.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.form.requestSubmit();
  }
});

elements.input.addEventListener("input", () => {
  elements.input.style.height = "auto";
  elements.input.style.height = `${Math.min(elements.input.scrollHeight, 140)}px`;
});

elements.fileInput.addEventListener("change", () => upload(elements.fileInput.files[0]));
elements.uploadZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  if (elements.fileInput.disabled) return;
  elements.uploadZone.classList.add("dragging");
});
elements.uploadZone.addEventListener("dragleave", () => elements.uploadZone.classList.remove("dragging"));
elements.uploadZone.addEventListener("drop", (event) => {
  event.preventDefault();
  elements.uploadZone.classList.remove("dragging");
  if (elements.fileInput.disabled) return;
  upload(event.dataTransfer.files[0]);
});

document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => ask(button.dataset.question));
});

Promise.allSettled([loadHealth(), loadDocuments(), loadBenchmark()]);
