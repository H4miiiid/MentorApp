<script lang="ts">
  import { page } from "$app/stores";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import { fetchAssignment, fetchSubmission, type AssignmentRead, type SubmissionRead } from "$lib/api";
  import SubmissionStatusBadge from "$lib/components/SubmissionStatusBadge.svelte";
  import { formatDateTime, formatSubmissionGrade } from "$lib/format";
  import { PATH_STUDENT_HOME, PATH_STUDENT_SUBMISSIONS } from "$lib/paths";

  let submission: SubmissionRead | null = null;
  let assignment: AssignmentRead | null = null;
  let errorMsg = "";
  let loading = true;

  $: submissionId = $page.params.submissionId ?? "";

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
        <dt>Created</dt>
        <dd>{formatDateTime(submission.created_at)}</dd>
      </dl>
    </div>

    <h2 class="gh-title" style="font-size: 15px; margin-bottom: 8px;">Submitted code</h2>
    <div class="gh-code-view-shell">
      <div class="gh-code-editor-toolbar">Python</div>
      <pre class="gh-code-block gh-code-block-python">{submission.code || "—"}</pre>
    </div>

    {#if submission.corrected_code}
      <h2 class="gh-title" style="font-size: 15px; margin: 20px 0 8px;">Corrected code</h2>
      <div class="gh-code-view-shell">
        <div class="gh-code-editor-toolbar">Python</div>
        <pre class="gh-code-block gh-code-block-python">{submission.corrected_code}</pre>
      </div>
    {/if}

    {#if submission.diff}
      <h2 class="gh-title" style="font-size: 15px; margin: 20px 0 8px;">Diff</h2>
      <div class="gh-code-view-shell">
        <div class="gh-code-editor-toolbar">Diff</div>
        <pre class="gh-code-block gh-code-block-python">{submission.diff}</pre>
      </div>
    {/if}

    <h2 class="gh-title" style="font-size: 15px; margin: 20px 0 8px;">Stdout</h2>
    <div class="gh-code-view-shell">
      <div class="gh-code-editor-toolbar">Stdout</div>
      <pre class="gh-code-block gh-code-block-python">{submission.stdout || "—"}</pre>
    </div>

    <h2 class="gh-title" style="font-size: 15px; margin: 20px 0 8px;">Stderr</h2>
    <div class="gh-code-view-shell">
      <div class="gh-code-editor-toolbar">Stderr</div>
      <pre class="gh-code-block gh-code-block-python">{submission.stderr || "—"}</pre>
    </div>

    <h2 class="gh-title" style="font-size: 15px; margin: 20px 0 8px;">Feedback</h2>
    <div class="gh-code-view-shell">
      <div class="gh-code-editor-toolbar">Text</div>
      <pre class="gh-code-block gh-code-block-python">{submission.feedback || "—"}</pre>
    </div>
  {/if}
</section>
