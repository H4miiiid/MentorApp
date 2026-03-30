<script lang="ts">
  import { browser } from "$app/environment";
  import { onDestroy, onMount } from "svelte";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import { apiFetch } from "$lib/api";
  import { PATH_ADMIN_HOME } from "$lib/paths";

  const STORAGE_KEY = "mentorapp_admin_monitoring_refresh_ms";
  const INTERVAL_OPTIONS = [
    { label: "1s", ms: 1000 },
    { label: "5s", ms: 5000 },
    { label: "10s", ms: 10_000 },
    { label: "30s", ms: 30_000 },
  ] as const;

  const MAX_LINES = 4000;
  /** Recent full log lines (timestamp + body) to skip snapshot replay on reconnect. */
  const LINE_DEDUPE_WINDOW = 6000;

  type LogKind = "backend" | "agent" | "sandbox";

  type LogLine = {
    text: string;
    kind: LogKind;
    agent: string | null;
    level: string;
    phase: string | null;
  };

  let lines: LogLine[] = [];
  const recentLineQueue: string[] = [];
  const recentLineSet = new Set<string>();
  let errorMsg = "";
  let status: "connecting" | "live" | "error" | "stopped" = "connecting";
  let logEl: HTMLDivElement | null = null;
  let abort: AbortController | null = null;
  /** Increments on each connect(); stale stream handlers ignore AbortError. */
  let activeStreamId = 0;
  /** True until the first successful stream open; used for empty-state copy only. */
  let firstConnect = true;
  /** When true, `connect` does not set status to Connecting (avoids flicker on interval refresh). */
  let softReconnect = false;

  let refreshIntervalMs = 5000;
  let autoRefreshPaused = false;
  let refreshTimer: ReturnType<typeof setInterval> | null = null;

  function scrollToBottom() {
    if (logEl) {
      logEl.scrollTop = logEl.scrollHeight;
    }
  }

  $: if (lines.length) queueMicrotask(scrollToBottom);

  function loadStoredInterval() {
    if (!browser) return;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const n = Number.parseInt(raw, 10);
      if (INTERVAL_OPTIONS.some((o) => o.ms === n)) {
        refreshIntervalMs = n;
      }
    } catch {
      /* ignore */
    }
  }

  function persistInterval() {
    if (!browser) return;
    try {
      localStorage.setItem(STORAGE_KEY, String(refreshIntervalMs));
    } catch {
      /* ignore */
    }
  }

  function clearRefreshTimer() {
    if (refreshTimer !== null) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  }

  function startRefreshTimer() {
    clearRefreshTimer();
    if (autoRefreshPaused) return;
    refreshTimer = setInterval(() => {
      cycleStream();
    }, refreshIntervalMs);
  }

  function tryAcceptSeenLine(line: string): boolean {
    if (recentLineSet.has(line)) return false;
    recentLineSet.add(line);
    recentLineQueue.push(line);
    while (recentLineQueue.length > LINE_DEDUPE_WINDOW) {
      const old = recentLineQueue.shift();
      if (old !== undefined) recentLineSet.delete(old);
    }
    return true;
  }

  function agentColor(agent: string): string {
    let h = 0;
    for (let i = 0; i < agent.length; i++) h = (h * 33 + agent.charCodeAt(i)) % 360;
    return `hsl(${h} 82% 68%)`;
  }

  function appendLogPayload(payload: {
    seq?: number;
    line?: string;
    kind?: string;
    agent?: string | null;
    level?: string;
    phase?: string | null;
  }) {
    const line = payload.line;
    if (line == null || line === "") return;
    if (!tryAcceptSeenLine(line)) return;
    let kind: LogKind = "backend";
    if (payload.kind === "agent") kind = "agent";
    else if (payload.kind === "sandbox") kind = "sandbox";
    const agent = typeof payload.agent === "string" && payload.agent ? payload.agent : null;
    const level = typeof payload.level === "string" ? payload.level : "INFO";
    const phase = typeof payload.phase === "string" && payload.phase ? payload.phase : null;
    lines = [...lines.slice(-MAX_LINES), { text: line, kind, agent, level, phase }];
  }

  /** Periodic reconnect: abort current stream and open a new one (hybrid refresh). */
  function cycleStream() {
    softReconnect = status === "live";
    void connect();
  }

  async function connect() {
    const id = ++activeStreamId;
    abort?.abort();
    abort = new AbortController();
    if (!softReconnect) {
      status = "connecting";
    }
    softReconnect = false;
    errorMsg = "";
    try {
      const res = await apiFetch("/api/admin/logs/stream", { signal: abort.signal });
      if (id !== activeStreamId) return;
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail ?? `HTTP ${res.status}`);
      }
      if (!res.body) throw new Error("No response body");
      if (id !== activeStreamId) return;
      status = "live";
      firstConnect = false;
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (id !== activeStreamId) break;
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const chunks = buf.split("\n\n");
        buf = chunks.pop() ?? "";
        for (const block of chunks) {
          for (const row of block.split("\n")) {
            if (!row.startsWith("data: ")) continue;
            try {
              const payload = JSON.parse(row.slice(6)) as {
                seq?: number;
                line?: string;
                kind?: string;
                agent?: string | null;
                level?: string;
                phase?: string | null;
              };
              appendLogPayload(payload);
            } catch {
              /* ignore malformed */
            }
          }
        }
      }
    } catch (e) {
      if ((e as Error).name === "AbortError") {
        if (id !== activeStreamId) return;
        status = "stopped";
        return;
      }
      if (id !== activeStreamId) return;
      status = "error";
      errorMsg = e instanceof Error ? e.message : "Stream failed";
    }
  }

  function refreshNow() {
    softReconnect = status === "live";
    void connect();
  }

  function clearView() {
    lines = [];
  }

  function togglePause() {
    autoRefreshPaused = !autoRefreshPaused;
    if (autoRefreshPaused) {
      clearRefreshTimer();
    } else {
      startRefreshTimer();
    }
  }

  function onIntervalChange(ev: Event) {
    const raw = (ev.currentTarget as HTMLSelectElement).value;
    const n = Number.parseInt(raw, 10);
    if (!Number.isNaN(n) && INTERVAL_OPTIONS.some((o) => o.ms === n)) {
      refreshIntervalMs = n;
    }
    persistInterval();
    clearRefreshTimer();
    if (!autoRefreshPaused) {
      startRefreshTimer();
    }
  }

  onMount(() => {
    loadStoredInterval();
    void connect();
    startRefreshTimer();
  });

  onDestroy(() => {
    clearRefreshTimer();
    activeStreamId++;
    abort?.abort();
  });

  $: statusLabel =
    status === "connecting"
      ? "Connecting…"
      : status === "live"
        ? "Live"
        : status === "error"
          ? "Error"
          : "Stopped";

  $: statusClass =
    status === "live"
      ? "gh-monitoring-pill-live"
      : status === "error"
        ? "gh-monitoring-pill-error"
        : status === "connecting"
          ? "gh-monitoring-pill-warn"
          : "gh-monitoring-pill-muted";

  $: emptyHint =
    !lines.length && status === "connecting" && firstConnect
      ? "Connecting to log stream…"
      : !lines.length
        ? "Waiting for log lines…"
        : "";
</script>

<section class="gh-monitoring-section">
  <Breadcrumbs
    items={[
      { label: "Admin", href: PATH_ADMIN_HOME },
      { label: "Monitoring" },
    ]}
  />
  <header class="gh-monitoring-header">
    <div>
      <h1 class="gh-title gh-monitoring-title">Monitoring</h1>
      <p class="gh-subtitle gh-monitoring-subtitle">
        In-memory log tail from this backend process. Agent graph nodes, sandbox runs, and severity levels use
        distinct colors; correlation IDs appear in structured fields when present.
      </p>
    </div>
  </header>

  <div class="gh-monitoring-card">
    <div class="gh-monitoring-toolbar" role="toolbar" aria-label="Log stream controls">
      <div class="gh-monitoring-toolbar-left">
        <span class="gh-monitoring-meta-label">Status</span>
        <span class="gh-monitoring-pill {statusClass}" title="Connection state">{statusLabel}</span>
      </div>

      <div class="gh-monitoring-toolbar-right">
        <label class="gh-monitoring-interval">
          <span class="gh-monitoring-meta-label">Interval</span>
          <select
            class="gh-select gh-monitoring-select"
            value={refreshIntervalMs}
            on:change={onIntervalChange}
          >
            {#each INTERVAL_OPTIONS as opt}
              <option value={opt.ms}>{opt.label}</option>
            {/each}
          </select>
        </label>
        <button type="button" class="gh-btn gh-btn-sm" on:click={togglePause}>
          {autoRefreshPaused ? "Resume" : "Pause"}
        </button>
        <button type="button" class="gh-btn gh-btn-sm gh-btn-primary" on:click={refreshNow}>Refresh now</button>
        <button type="button" class="gh-btn gh-btn-sm" on:click={clearView}>Clear view</button>
      </div>
    </div>

    {#if errorMsg}
      <div class="gh-alert gh-alert-error gh-monitoring-alert">{errorMsg}</div>
    {/if}

    <div class="gh-monitoring-terminal-wrap">
      <div
        class="gh-admin-log-terminal gh-monitoring-terminal gh-log-scroll"
        bind:this={logEl}
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        aria-label="Backend log output"
      >
        {#if lines.length === 0}
          <span class="gh-log-empty">{emptyHint}</span>
        {:else}
          {#each lines as entry}
            <div
              class="gh-log-row"
              class:gh-log-backend={entry.kind === "backend"}
              class:gh-log-agent={entry.kind === "agent"}
              class:gh-log-sandbox={entry.kind === "sandbox"}
              class:gh-log-error={entry.level === "ERROR" || entry.level === "CRITICAL"}
              class:gh-log-warning={entry.level === "WARNING"}
              class:gh-log-phase-grading={entry.phase === "grading" || entry.phase === "workflow_node"}
              style={entry.kind === "agent" &&
              entry.agent &&
              entry.level !== "ERROR" &&
              entry.level !== "CRITICAL"
                ? `color: ${agentColor(entry.agent)}`
                : undefined}
            >
              {entry.text}
            </div>
          {/each}
        {/if}
      </div>
    </div>
  </div>
</section>
