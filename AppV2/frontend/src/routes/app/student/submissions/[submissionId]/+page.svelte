<script lang="ts">
  import { page } from "$app/stores";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import { fetchAssignment, fetchSubmission, type AssignmentRead, type SubmissionRead } from "$lib/api";
  import FeedbackPanel from "$lib/components/FeedbackPanel.svelte";
  import SubmissionStatusBadge from "$lib/components/SubmissionStatusBadge.svelte";
  import UnifiedDiffView from "$lib/components/UnifiedDiffView.svelte";
  import { formatDateTime, formatSubmissionGrade } from "$lib/format";
  import { PATH_STUDENT_HOME, PATH_STUDENT_SUBMISSIONS } from "$lib/paths";

  let submission: SubmissionRead | null = null;
  let assignment: AssignmentRead | null = null;
  let errorMsg = "";
  let loading = true;

  $: submissionId = $page.params.submissionId ?? "";

  $: gradingDone =
    submission != null && (submission.status === "completed" || submission.status === "failed");

  function parseMistakeCount(feedback: string | undefined): number {
    const src = (feedback ?? "").trim();
    if (!src) return 0;
    try {
      const parsed = JSON.parse(src) as { mistake_count?: unknown };
      const raw = parsed.mistake_count;
      return typeof raw === "number" && Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : 0;
    } catch {
      return 0;
    }
  }

  $: mistakeCount = gradingDone && submission ? parseMistakeCount(submission.feedback) : 0;

  async function load(id: string) {
    if (!id) {
      loading = false;
      return;
    }
    loading = true;
    errorMsg = "";
    try {
      const sub = await fetchSubmission(id);
      submission = sub;
      assignment = await fetchAssignment(sub.assignment_id);
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Failed to load";
      submission = null;
      assignment = null;
    } finally {
      loading = false;
    }
  }

  $: load(submissionId);
</script>

<section>
  <Breadcrumbs
    items={[
      { label: "Student", href: PATH_STUDENT_HOME },
      { label: "Submissions", href: PATH_STUDENT_SUBMISSIONS },
      {
        label: assignment?.title ?? "…",
        href: assignment ? `/app/student/assignments/${assignment.id}` : undefined,
      },
      { label: "Submission" },
    ]}
  />

  {#if errorMsg}
    <div class="gh-alert gh-alert-error">{errorMsg}</div>
  {/if}

  {#if loading}
    <p class="gh-muted">Loading…</p>
  {:else if submission && assignment}
    <h1 class="gh-title" style="margin-top: 0; margin-bottom: 8px;">Your submission</h1>
    <p class="gh-muted" style="margin-bottom: 20px;">
      Assignment: <strong>{assignment.title}</strong> · Updated {formatDateTime(submission.updated_at)}
    </p>

    <div class="gh-card" style="max-width: none; margin-bottom: 20px;">
      <dl class="gh-dl">
        <dt>Status</dt>
        <dd><SubmissionStatusBadge status={submission.status} /></dd>
        <dt>Grade</dt>
        <dd>{formatSubmissionGrade(submission.grade, submission.status)}</dd>
        <dt>Mistakes</dt>
        <dd>{mistakeCount > 0 ? mistakeCount : "—"}</dd>
        <dt>Created</dt>
        <dd>{formatDateTime(submission.created_at)}</dd>
      </dl>
    </div>

    <h2 class="gh-title" style="font-size: 15px; margin-bottom: 8px;">Submitted code</h2>
    <div class="gh-code-view-shell">
      <div class="gh-code-editor-toolbar">Python · your upload</div>
      <pre class="gh-code-block gh-code-block-python">{submission.code || "—"}</pre>
    </div>

    {#if !gradingDone}
      <p class="gh-muted" style="margin: 20px 0 0; font-size: 14px;">
        Grading is still running. When it finishes, <strong>errors (stderr)</strong>,
        <strong>corrected code</strong>, <strong>diff</strong>, and test output will appear below. Refresh if needed.
      </p>
    {:else}
      <h2 class="gh-title" style="font-size: 15px; margin: 24px 0 8px;">Errors (stderr)</h2>
      <p class="gh-muted" style="margin: 0 0 10px; font-size: 13px;">
        Runtime or checker errors from the autograder sandbox (same field teachers see).
      </p>
      <div class="gh-code-view-shell gh-code-shell-error">
        <div class="gh-code-editor-toolbar">Stderr</div>
        <pre class="gh-code-block gh-code-block-stderr">{submission.stderr?.trim() || "—"}</pre>
      </div>

      <h2 class="gh-title" style="font-size: 15px; margin: 24px 0 8px;">Corrected code</h2>
      <p class="gh-muted" style="margin: 0 0 10px; font-size: 13px;">
        Suggested or auto-fixed code from the grader (when provided).
      </p>
      <div class="gh-code-view-shell">
        <div class="gh-code-editor-toolbar">Python · suggested</div>
        <pre class="gh-code-block gh-code-block-python">{submission.corrected_code?.trim() || "—"}</pre>
      </div>

      <h2 class="gh-title" style="font-size: 15px; margin: 24px 0 8px;">Diff</h2>
      <p class="gh-muted" style="margin: 0 0 10px; font-size: 13px;">
        Unified diff between your submission and the corrected version.
      </p>
      <UnifiedDiffView diff={submission.diff ?? ""} />

      <h2 class="gh-title" style="font-size: 15px; margin: 24px 0 8px;">Stdout</h2>
      <div class="gh-code-view-shell">
        <div class="gh-code-editor-toolbar">Stdout</div>
        <pre class="gh-code-block gh-code-block-python">{submission.stdout?.trim() || "—"}</pre>
      </div>

      <h2 class="gh-title" style="font-size: 15px; margin: 24px 0 8px;">Grader feedback</h2>
      <p class="gh-muted" style="margin: 0 0 10px; font-size: 13px;">
        Summary of what the autograder found, which repair strategies it tried, and why it stopped.
      </p>
      <FeedbackPanel feedback={submission.feedback ?? ""} studentView={true} />
    {/if}
  {/if}
</section>
