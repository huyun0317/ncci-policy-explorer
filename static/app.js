"use strict";

const numberFormat = new Intl.NumberFormat("en-US");
const conversation = document.querySelector("#conversation");
const form = document.querySelector("#question-form");
const questionInput = document.querySelector("#question");
const askButton = document.querySelector("#ask-button");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function linkedAnswer(text, sources) {
  const safe = escapeHtml(text);
  return safe.replace(/\[(\d+)\]/g, (match, value) => {
    const source = sources.find((item) => item.citation === Number(value));
    if (!source) return match;
    return `<a class="citation-link" href="/manual#page=${source.page}" target="_blank" rel="noreferrer">[${value}]</a>`;
  });
}

function sourceMarkup(sources) {
  if (!sources.length) return "";
  return `<div class="sources">${sources.map((source) => {
    const snippet = source.text.length > 180 ? `${source.text.slice(0, 177)}...` : source.text;
    return `
      <a class="source-row" href="/manual#page=${source.page}" target="_blank" rel="noreferrer">
        <span class="source-number">${source.citation}</span>
        <span>
          <span class="source-title">${escapeHtml(source.chapter_code)}: ${escapeHtml(source.chapter_title)}</span>
          <span class="source-snippet">${escapeHtml(snippet)}</span>
        </span>
        <span class="source-page">Page ${source.page}</span>
      </a>`;
  }).join("")}</div>`;
}

function addMessage(role, html, extraClass = "") {
  const article = document.createElement("article");
  article.className = `message ${role === "user" ? "user-message" : "assistant-message"} ${extraClass}`.trim();
  article.innerHTML = html;
  conversation.append(article);
  conversation.scrollTop = conversation.scrollHeight;
  return article;
}

function loadingMessage() {
  return addMessage(
    "assistant",
    `<div class="message-label">Policy assistant</div><div class="loading-line">Retrieving evidence <span></span><span></span><span></span></div>`,
    "loading-message",
  );
}

function renderBars(containerId, rows, valueKey, label, limit = rows.length) {
  const container = document.querySelector(containerId);
  const visible = rows.slice(0, limit);
  const max = Math.max(...visible.map((row) => row[valueKey]), 1);
  container.innerHTML = visible.map((row) => `
    <div class="bar-row" title="${escapeHtml(row[label])}: ${numberFormat.format(row[valueKey])}">
      <span class="bar-label">${escapeHtml(row[label])}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${Math.max(2, (row[valueKey] / max) * 100)}%"></span></span>
      <span class="bar-value">${numberFormat.format(row[valueKey])}</span>
    </div>`).join("");
}

async function loadInsights() {
  const [healthResponse, insightResponse] = await Promise.all([
    fetch("/api/health"),
    fetch("/api/insights"),
  ]);
  if (!healthResponse.ok || !insightResponse.ok) throw new Error("Could not load the manual index.");
  const health = await healthResponse.json();
  const insights = await insightResponse.json();

  const badge = document.querySelector("#mode-badge");
  if (health.answer_mode === "openai") {
    const effort = health.reasoning_effort ? ` - ${health.reasoning_effort} reasoning` : "";
    badge.textContent = `Grounded answers - ${health.model}${effort}`;
  } else {
    badge.textContent = "Evidence search mode";
    badge.classList.add("offline");
  }

  document.querySelector("#pages-count").textContent = numberFormat.format(insights.pages);
  document.querySelector("#chunks-count").textContent = numberFormat.format(insights.chunks);
  document.querySelector("#chapters-count").textContent = numberFormat.format(insights.chapters.length);
  if (insights.indexed_at) {
    const date = new Date(insights.indexed_at);
    document.querySelector("#indexed-date").textContent = `Indexed ${date.toLocaleDateString()}`;
  }

  renderBars("#topic-bars", insights.topics, "count", "label", 7);
  renderBars("#chapter-bars", insights.chapters, "words", "title");
  document.querySelector("#code-list").innerHTML = insights.frequent_codes
    .map((item) => `<span class="code-pill">${escapeHtml(item.code)}<span>${numberFormat.format(item.count)}</span></span>`)
    .join("");
}

async function askQuestion(question) {
  addMessage("user", `<div class="message-label">You</div><p>${escapeHtml(question)}</p>`);
  const pending = loadingMessage();
  askButton.disabled = true;
  questionInput.disabled = true;
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "The request failed.");
    pending.remove();
    const warning = payload.citation_warning
      ? `<div class="citation-warning">${escapeHtml(payload.citation_warning)}</div>`
      : "";
    const modelNote = payload.model_used
      ? `<div class="model-note">Answered with ${escapeHtml(payload.model_used)}${payload.fallback_used ? " because the configured primary model was unavailable to this API project" : ""}.</div>`
      : "";
    addMessage(
      "assistant",
      `<div class="message-label">Policy assistant</div><div class="answer-text">${linkedAnswer(payload.answer, payload.sources)}</div>${warning}${modelNote}${sourceMarkup(payload.sources)}`,
    );
  } catch (error) {
    pending.remove();
    addMessage(
      "assistant",
      `<div class="message-label">Policy assistant</div><p>I could not complete that request. ${escapeHtml(error.message)}</p>`,
    );
  } finally {
    askButton.disabled = false;
    questionInput.disabled = false;
    questionInput.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;
  questionInput.value = "";
  askQuestion(question);
});

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => askQuestion(button.dataset.question));
});

loadInsights().catch((error) => {
  addMessage("assistant", `<div class="message-label">System</div><p>${escapeHtml(error.message)}</p>`);
});
