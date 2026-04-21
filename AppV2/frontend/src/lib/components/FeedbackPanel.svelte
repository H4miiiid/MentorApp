<script lang="ts">
  export let feedback: string = "";
  export let studentView: boolean = false;

  type Attempt = {
    attempt?: number;
    route?: string;
    changed_meaningfully?: boolean;
    timestamp?: string;
    prompt_preview?: string;
  };

  type Parsed = {
    final_status?: string;
    attempt_count?: number;
    max_attempts?: number;
    error_category?: string;
    mistake_count?: number;
    mistake_categories?: string[];
    mistake_lines?: string[];
    stop_reason?: string;
    route_history?: string[];
    attempt_history_tail?: Attempt[];
    no_meaningful_change_count?: number;
    repeated_failure_count?: number;
    sandbox_error?: string;
    // Populated when the student's original submission failed but the autograder
    // eventually succeeded after LLM repair. Displayed as a distinct amber
    // banner with the original error so the student can learn from the mistake
    // instead of silently benefiting from "grade = 100".
    repaired?: boolean;
    initial_error_category?: string;
    initial_error_type?: string;
    initial_error_explanation?: string;
    initial_traceback?: string;
  };

  let parsed: Parsed | null = null;
  let parseError = "";
  $: {
    parsed = null;
    parseError = "";
    const src = (feedback ?? "").trim();
    if (src) {
      try {
        const obj = JSON.parse(src);
        if (obj && typeof obj === "object") parsed = obj as Parsed;
      } catch (e) {
        parseError = e instanceof Error ? e.message : "parse error";
      }
    }
  }

  $: final = (parsed?.final_status ?? "").toLowerCase();
  // A "repaired" run is still a success, but the student didn't earn it on their own,
  // so we treat it as its own visual state (amber, not green) to make that obvious.
  $: isRepaired = final === "success" && !!parsed?.repaired;
  $: isSuccess = final === "success" && !isRepaired;
  $: isSandboxInfra = final === "sandbox_unavailable";
  $: isFailure = !isRepaired && !isSuccess && !isSandboxInfra && !!final;

  $: attempts = parsed?.attempt_count ?? 0;
  $: mistakeCount = parsed?.mistake_count ?? 0;
  $: mistakeCategories = parsed?.mistake_categories ?? [];
  $: maxAttempts = parsed?.max_attempts ?? 0;
  $: attemptPct =
    maxAttempts > 0 ? Math.min(100, Math.round((attempts / maxAttempts) * 100)) : 0;

  $: routeHistory = parsed?.route_history ?? [];
  $: attemptHistory = parsed?.attempt_history_tail ?? [];

  let showRaw = false;

  function routeLabel(node: string): string {
    const map: Record<string, string> = {
      run_checks: "Run sandbox",
      diagnose_failure: "Diagnose",
      choose_next_strategy: "Plan",
      retrieve_local_docs: "RAG retrieve",
      assess_local_context: "Assess RAG",
      web_search_docs: "Web search",
      summarize_context: "Summarize docs",
      attempt_sft_with_rag: "Repair w/ RAG",
      attempt_sft_with_traceback: "Repair w/ traceback",
      reflection_critic: "Reflect",
      attempt_sft_with_reflection: "Repair w/ reflection",
      external_expert_repair: "Expert repair",
      finalize_success: "Finalize ✓",
      finalize_failure: "Finalize ✗",
    };
    return map[node] ?? node.replace(/_/g, " ");
  }

  function statusLabel(s: string): string {
    if (s === "success") return "Passed";
    if (s === "failure") return "Failed";
    if (s === "sandbox_unavailable") return "Infrastructure error";
    return s || "—";
  }

  function repairedStatusLabel(): string {
    return "Passed — after assistant repair";
  }

  function stopReasonLabel(r: string | undefined): string {
    if (!r) return "";
    const map: Record<string, string> = {
      max_attempts_reached: "Ran out of repair attempts",
      no_meaningful_change: "Repair attempts produced no meaningful change",
      all_strategies_exhausted: "Every repair strategy was tried",
      sandbox_unavailable: "Sandbox was unavailable — code was never executed",
    };
    return map[r] ?? r.replace(/_/g, " ");
  }

  function categoryLabel(c: string | undefined): string {
    if (!c) return "";
    const map: Record<string, string> = {
      syntax_error: "Syntax error",
      name_error: "Name error",
      stdin_eof: "Missing stdin input",
      timeout: "Execution timeout",
      local_reasoning_error: "Logic / value error",
      api_library_error: "API / library misuse",
      sandbox_unavailable: "Sandbox unavailable",
    };
    return map[c] ?? c.replace(/_/g, " ");
  }

  function fmtTs(iso: string | undefined): string {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return iso;
    }
  }
</script>

{#if !parsed}
  {#if parseError || (feedback ?? "").trim()}
    <div class="fb-card">
      <div class="fb-header">
        <span class="fb-heading">Feedback</span>
      </div>
      <pre class="fb-raw">{feedback?.trim() || "—"}</pre>
    </div>
  {:else}
    <p class="gh-muted" style="margin: 0;">No feedback yet.</p>
  {/if}
{:else}
  <div class="fb-card">
    <!-- Hero banner -->
    <div
      class="fb-banner"
      class:fb-banner-success={isSuccess}
      class:fb-banner-repaired={isRepaired}
      class:fb-banner-failure={isFailure}
      class:fb-banner-infra={isSandboxInfra}
    >
      <div class="fb-banner-icon" aria-hidden="true">
        {#if isSuccess}✓{:else if isRepaired}⟳{:else if isSandboxInfra}!{:else}✗{/if}
      </div>
      <div class="fb-banner-text">
        <div class="fb-banner-title">
          {#if isRepaired}{repairedStatusLabel()}{:else}{statusLabel(final)}{/if}
        </div>
        <div class="fb-banner-sub">
          {#if isSuccess}
            Your code ran and passed every sandbox check.
          {:else if isRepaired}
            Your original submission did not run — the grading assistant applied a
            minimal fix (see the <strong>Changes</strong> diff below) and the
            corrected version passed. The grade has been capped because
            auto-repair was needed; review the original error so the same issue
            does not come back on your next submission.
          {:else if isSandboxInfra}
            The grading sandbox was unavailable, so your code was not executed.
            This is not your fault — ask the teacher to re-run grading once the
            system is back up.
          {:else if parsed.stop_reason}
            {stopReasonLabel(parsed.stop_reason)}.
          {:else}
            The autograder could not validate your submission.
          {/if}
        </div>
      </div>
    </div>

    {#if isSandboxInfra && parsed.sandbox_error}
      <div class="fb-infra-detail">
        <span class="fb-meta-label">Infrastructure error</span>
        <code class="fb-infra-msg">{parsed.sandbox_error}</code>
      </div>
    {/if}

    {#if isRepaired && (parsed.initial_traceback || parsed.initial_error_category)}
      <div class="fb-repaired-detail">
        <span class="fb-meta-label">
          Original error
          {#if parsed.initial_error_category}
            · {categoryLabel(parsed.initial_error_category)}
          {/if}
          {#if parsed.initial_error_type}
            · {parsed.initial_error_type}
          {/if}
        </span>
        {#if parsed.initial_error_explanation}
          <div class="fb-repaired-explanation">{parsed.initial_error_explanation}</div>
        {/if}
        {#if parsed.initial_traceback}
          <pre class="fb-repaired-trace">{parsed.initial_traceback}</pre>
        {/if}
      </div>
    {/if}

    <!-- Metrics grid -->
    <div class="fb-metrics">
      {#if !isSandboxInfra && (parsed.error_category || (isRepaired && parsed.initial_error_category))}
        <div class="fb-metric">
          <div class="fb-metric-label">
            {isRepaired ? "Original error category" : "Error category"}
          </div>
          <div class="fb-metric-value">
            {categoryLabel(
              isRepaired
                ? (parsed.initial_error_category || parsed.error_category || "")
                : (parsed.error_category || "")
            )}
          </div>
        </div>
      {/if}
      {#if !isSandboxInfra && mistakeCount > 0}
        <div class="fb-metric">
          <div class="fb-metric-label">Mistakes detected</div>
          <div class="fb-metric-value">
            {mistakeCount}
            {#if mistakeCategories.length > 0}
              <span class="gh-muted" style="font-size: 12px; margin-left: 8px;">
                ({mistakeCategories.map(categoryLabel).join(", ")})
              </span>
            {/if}
          </div>
        </div>
      {/if}
      {#if !isSandboxInfra && maxAttempts > 0}
        <div class="fb-metric">
          <div class="fb-metric-label">Repair attempts used</div>
          <div class="fb-metric-value">
            {attempts} / {maxAttempts}
            <div class="fb-bar">
              <div
                class="fb-bar-fill"
                class:fb-bar-fill-danger={attempts >= maxAttempts}
                style="width: {attemptPct}%;"
              ></div>
            </div>
          </div>
        </div>
      {/if}
      {#if parsed.stop_reason && !isSandboxInfra}
        <div class="fb-metric">
          <div class="fb-metric-label">Stop reason</div>
          <div class="fb-metric-value">{stopReasonLabel(parsed.stop_reason)}</div>
        </div>
      {/if}
      {#if (parsed.no_meaningful_change_count ?? 0) > 0}
        <div class="fb-metric">
          <div class="fb-metric-label">No-op repairs</div>
          <div class="fb-metric-value">{parsed.no_meaningful_change_count}</div>
        </div>
      {/if}
      {#if (parsed.repeated_failure_count ?? 0) > 0}
        <div class="fb-metric">
          <div class="fb-metric-label">Same failure repeated</div>
          <div class="fb-metric-value">{parsed.repeated_failure_count}×</div>
        </div>
      {/if}
    </div>

    <!-- Route history -->
    {#if routeHistory.length > 0}
      <div class="fb-section">
        <div class="fb-section-head">
          <span class="fb-heading">Workflow path</span>
          <span class="gh-muted fb-section-hint">
            The grading graph's node trace from start to finish.
          </span>
        </div>
        <ol class="fb-route">
          {#each routeHistory as node, i}
            <li class="fb-route-item" class:fb-route-item-last={i === routeHistory.length - 1}>
              <span class="fb-route-index">{i + 1}</span>
              <span class="fb-route-label">{routeLabel(node)}</span>
            </li>
          {/each}
        </ol>
      </div>
    {/if}

    <!-- Attempt timeline -->
    {#if attemptHistory.length > 0}
      <div class="fb-section">
        <div class="fb-section-head">
          <span class="fb-heading">Repair attempts</span>
          <span class="gh-muted fb-section-hint">
            What the autograder tried in order to fix the code.
          </span>
        </div>
        <ol class="fb-timeline">
          {#each attemptHistory as a}
            <li class="fb-timeline-item">
              <div class="fb-timeline-head">
                <span class="fb-timeline-num">#{a.attempt ?? "?"}</span>
                <span class="fb-timeline-route">{routeLabel(a.route ?? "")}</span>
                <span
                  class="fb-chip"
                  class:fb-chip-ok={a.changed_meaningfully}
                  class:fb-chip-muted={!a.changed_meaningfully}
                  title={a.changed_meaningfully
                    ? "This attempt produced a real edit."
                    : "This attempt did not change the code meaningfully."}
                >
                  {a.changed_meaningfully ? "edit applied" : "no real change"}
                </span>
                <span class="fb-timeline-ts">{fmtTs(a.timestamp)}</span>
              </div>
              {#if !studentView && a.prompt_preview}
                <details class="fb-timeline-prompt">
                  <summary>Prompt preview</summary>
                  <pre>{a.prompt_preview}</pre>
                </details>
              {/if}
            </li>
          {/each}
        </ol>
      </div>
    {/if}

    <!-- Raw JSON fallback for power users -->
    <div class="fb-section">
      <button type="button" class="fb-raw-toggle" on:click={() => (showRaw = !showRaw)}>
        {showRaw ? "Hide" : "Show"} raw feedback (JSON)
      </button>
      {#if showRaw}
        <pre class="fb-raw">{feedback?.trim()}</pre>
      {/if}
    </div>
  </div>
{/if}

<style>
  .fb-card {
    border: 1px solid var(--gh-border);
    border-radius: 8px;
    background: var(--gh-bg-secondary);
    overflow: hidden;
  }

  .fb-header {
    padding: 10px 14px;
    border-bottom: 1px solid var(--gh-border);
    background: rgba(0, 0, 0, 0.15);
  }

  .fb-heading {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--gh-text-muted);
  }

  .fb-section-hint {
    margin-left: 10px;
    text-transform: none;
    letter-spacing: 0;
    font-weight: 400;
  }

  .fb-banner {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 16px 18px;
    border-bottom: 1px solid var(--gh-border);
  }

  .fb-banner-icon {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    font-size: 18px;
    font-weight: 700;
    line-height: 1;
  }

  .fb-banner-success {
    background: rgba(63, 185, 80, 0.08);
  }
  .fb-banner-success .fb-banner-icon {
    background: rgba(63, 185, 80, 0.18);
    color: #3fb950;
    border: 1px solid rgba(63, 185, 80, 0.4);
  }
  .fb-banner-success .fb-banner-title {
    color: #3fb950;
  }

  .fb-banner-failure {
    background: rgba(248, 81, 73, 0.06);
  }
  .fb-banner-failure .fb-banner-icon {
    background: rgba(248, 81, 73, 0.15);
    color: #f85149;
    border: 1px solid rgba(248, 81, 73, 0.4);
  }
  .fb-banner-failure .fb-banner-title {
    color: #f85149;
  }

  .fb-banner-infra {
    background: rgba(210, 153, 34, 0.08);
  }
  .fb-banner-infra .fb-banner-icon {
    background: rgba(210, 153, 34, 0.18);
    color: #d29922;
    border: 1px solid rgba(210, 153, 34, 0.4);
  }
  .fb-banner-infra .fb-banner-title {
    color: #d29922;
  }

  .fb-banner-repaired {
    background: rgba(219, 109, 40, 0.08);
  }
  .fb-banner-repaired .fb-banner-icon {
    background: rgba(219, 109, 40, 0.18);
    color: #db6d28;
    border: 1px solid rgba(219, 109, 40, 0.4);
  }
  .fb-banner-repaired .fb-banner-title {
    color: #db6d28;
  }

  .fb-repaired-detail {
    padding: 12px 18px;
    border-bottom: 1px solid var(--gh-border);
    background: rgba(219, 109, 40, 0.04);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .fb-repaired-explanation {
    font-size: 13px;
    color: var(--gh-text);
    line-height: 1.5;
  }

  .fb-repaired-trace {
    margin: 0;
    padding: 10px 12px;
    background: var(--gh-bg);
    border: 1px solid var(--gh-border);
    border-left: 3px solid #db6d28;
    border-radius: 6px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12px;
    line-height: 1.5;
    color: #e3a473;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 240px;
    overflow: auto;
  }

  .fb-banner-title {
    font-size: 16px;
    font-weight: 600;
    line-height: 1.3;
    margin-bottom: 2px;
  }

  .fb-banner-sub {
    color: var(--gh-text-muted);
    font-size: 13px;
    line-height: 1.5;
  }

  .fb-infra-detail {
    padding: 10px 18px;
    border-bottom: 1px solid var(--gh-border);
    background: rgba(210, 153, 34, 0.04);
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .fb-infra-msg {
    display: block;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12px;
    color: #e3b341;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .fb-meta-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--gh-text-muted);
  }

  .fb-metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1px;
    background: var(--gh-border);
    border-bottom: 1px solid var(--gh-border);
  }

  .fb-metric {
    padding: 12px 16px;
    background: var(--gh-bg-secondary);
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }

  .fb-metric-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--gh-text-muted);
  }

  .fb-metric-value {
    font-size: 14px;
    font-weight: 500;
    color: var(--gh-text);
    word-break: break-word;
  }

  .fb-bar {
    margin-top: 6px;
    height: 4px;
    background: var(--gh-border-muted);
    border-radius: 2px;
    overflow: hidden;
  }

  .fb-bar-fill {
    height: 100%;
    background: var(--gh-accent);
    transition: width 0.3s ease;
  }

  .fb-bar-fill-danger {
    background: #f85149;
  }

  .fb-section {
    padding: 14px 18px;
    border-bottom: 1px solid var(--gh-border);
  }

  .fb-section:last-child {
    border-bottom: none;
  }

  .fb-section-head {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 10px;
  }

  .fb-route {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .fb-route-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px 4px 6px;
    font-size: 12px;
    background: var(--gh-bg);
    border: 1px solid var(--gh-border);
    border-radius: 999px;
    color: var(--gh-text);
    position: relative;
  }

  .fb-route-item:not(:last-child)::after {
    content: "→";
    position: absolute;
    right: -12px;
    color: var(--gh-text-muted);
    font-size: 11px;
    top: 50%;
    transform: translateY(-50%);
  }

  .fb-route-item-last {
    border-color: rgba(63, 185, 80, 0.35);
    background: rgba(63, 185, 80, 0.05);
  }

  .fb-route-index {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 18px;
    height: 18px;
    padding: 0 5px;
    border-radius: 9px;
    background: var(--gh-bg-secondary);
    color: var(--gh-text-muted);
    font-size: 10px;
    font-weight: 600;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }

  .fb-route-label {
    font-weight: 500;
  }

  .fb-timeline {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .fb-timeline-item {
    padding: 10px 12px;
    background: var(--gh-bg);
    border: 1px solid var(--gh-border);
    border-left: 3px solid var(--gh-accent);
    border-radius: 6px;
  }

  .fb-timeline-head {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    font-size: 13px;
  }

  .fb-timeline-num {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-weight: 600;
    color: var(--gh-text-muted);
  }

  .fb-timeline-route {
    font-weight: 500;
    color: var(--gh-text);
  }

  .fb-timeline-ts {
    margin-left: auto;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 11px;
    color: var(--gh-text-muted);
  }

  .fb-chip {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 500;
    border-radius: 999px;
    border: 1px solid var(--gh-border);
    background: var(--gh-bg-secondary);
    color: var(--gh-text-muted);
  }

  .fb-chip-ok {
    color: #3fb950;
    background: rgba(63, 185, 80, 0.1);
    border-color: rgba(63, 185, 80, 0.4);
  }

  .fb-chip-muted {
    color: var(--gh-text-muted);
  }

  .fb-timeline-prompt {
    margin-top: 8px;
  }

  .fb-timeline-prompt summary {
    cursor: pointer;
    font-size: 12px;
    color: var(--gh-text-muted);
    list-style: none;
  }

  .fb-timeline-prompt summary::-webkit-details-marker {
    display: none;
  }

  .fb-timeline-prompt summary::before {
    content: "▸ ";
    font-size: 10px;
  }

  .fb-timeline-prompt[open] summary::before {
    content: "▾ ";
  }

  .fb-timeline-prompt pre {
    margin: 6px 0 0;
    padding: 8px 10px;
    background: var(--gh-bg-secondary);
    border: 1px solid var(--gh-border);
    border-radius: 6px;
    font-size: 11px;
    line-height: 1.5;
    color: var(--gh-text-muted);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 160px;
    overflow: auto;
  }

  .fb-raw-toggle {
    background: none;
    border: none;
    padding: 0;
    font-family: inherit;
    font-size: 12px;
    color: var(--gh-accent);
    cursor: pointer;
  }

  .fb-raw-toggle:hover {
    text-decoration: underline;
  }

  .fb-raw {
    margin: 10px 0 0;
    padding: 10px 12px;
    background: var(--gh-bg);
    border: 1px solid var(--gh-border);
    border-radius: 6px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 11px;
    line-height: 1.5;
    color: var(--gh-text);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 300px;
    overflow: auto;
  }
</style>
