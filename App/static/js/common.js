const SESSION_KEY = "mentorapp_session_v1";

function saveSession(session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

function loadSession() {
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

function setMessage(el, text, kind = "") {
  if (!el) return;
  el.textContent = text || "";
  el.classList.remove("error", "success");
  if (kind) el.classList.add(kind);
}

async function apiFetch(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload.detail || payload.message || "Request failed.";
    throw new Error(message);
  }

  return payload;
}

function toDiffBlock(text) {
  return text || "No differences available.";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderDiffHtml(diffText) {
  const raw = toDiffBlock(diffText);
  if (raw === "No changes were needed.") {
    return '<span class="diff-line header">No changes were needed.</span>';
  }

  const lines = String(raw).split("\n");
  return lines
    .map((line) => {
      let cls = "context";
      if (line.startsWith("+++ ") || line.startsWith("--- ")) {
        cls = "header";
      } else if (line.startsWith("@@")) {
        cls = "hunk";
      } else if (line.startsWith("+") && !line.startsWith("+++")) {
        cls = "added";
      } else if (line.startsWith("-") && !line.startsWith("---")) {
        cls = "removed";
      }
      return `<span class="diff-line ${cls}">${escapeHtml(line || " ")}</span>`;
    })
    .join("");
}
