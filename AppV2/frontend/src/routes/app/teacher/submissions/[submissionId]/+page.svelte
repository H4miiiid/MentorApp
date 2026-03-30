<script lang="ts">
  import { page } from "$app/stores";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import { PATH_TEACHER_HOME } from "$lib/paths";
  import {
    fetchAssignment,
    fetchSubmission,
    fetchUsers,
    type AssignmentRead,
    type SubmissionRead,
    type UserRead,
  } from "$lib/api";
  import SubmissionStatusBadge from "$lib/components/SubmissionStatusBadge.svelte";
  import { formatDateTime, formatSubmissionGrade } from "$lib/format";

  let submission: SubmissionRead | null = null;
  let assignment: AssignmentRead | null = null;
  let student: UserRead | undefined;
  let errorMsg = "";
  let loading = true;

  $: submissionId = $page.params.submissionId ?? "";

  $: gradingDone =
    submission != null && (submission.status === "completed" || submission.status === "failed");

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
      const [a, users] = await Promise.all([
        fetchAssignment(sub.assignment_id),
        fetchUsers(),
      ]);
      assignment = a;
      student = users.find((u) => u.id === sub.student_id);
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
      { label: "Teacher", href: PATH_TEACHER_HOME },
      { label: "Assignments", href: PATH_TEACHER_HOME },
      {
        label: assignment?.title ?? "…",
        href: assignment ? `/app/teacher/assignments/${assignment.id}` : undefined,
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
    <h1 class="gh-title" style="margin-top: 0; margin-bottom: 8px;">Submission</h1>
    <p class="gh-muted" style="margin-bottom: 20px;">
      Student: <strong>{student?.full_name ?? submission.student_id}</strong>
      ({student?.email ?? "—"}) · Updated {formatDateTime(submission.updated_at)}
    </p>

    <div class="gh-card" style="max-width: none; margin-bottom: 20px;">
      <dl class="gh-dl">
        <dt>Assignment</dt>
        <dd>{assignment.title}</dd>
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
      <div class="gh-code-editor-toolbar">Python · student upload</div>
      <pre class="gh-code-block gh-code-block-python">{submission.code || "—"}</pre>
    </div>

    {#if !gradingDone}
      <p class="gh-muted" style="margin: 20px 0 0;">Grading not finished yet.</p>
    {:else}
      <h2 class="gh-title" style="font-size: 15px; margin: 24px 0 8px;">Errors (stderr)</h2>
      <div class="gh-code-view-shell gh-code-shell-error">
        <div class="gh-code-editor-toolbar">Stderr</div>
        <pre class="gh-code-block gh-code-block-stderr">{submission.stderr?.trim() || "—"}</pre>
      </div>

      <h2 class="gh-title" style="font-size: 15px; margin: 24px 0 8px;">Corrected code</h2>
      <div class="gh-code-view-shell">
        <div class="gh-code-editor-toolbar">Python · suggested</div>
        <pre class="gh-code-block gh-code-block-python">{submission.corrected_code?.trim() || "—"}</pre>
      </div>

      <h2 class="gh-title" style="font-size: 15px; margin: 24px 0 8px;">Diff</h2>
      <div class="gh-code-view-shell">
        <div class="gh-code-editor-toolbar">Diff</div>
        <pre class="gh-code-block gh-code-block-python">{submission.diff?.trim() || "—"}</pre>
      </div>

      <h2 class="gh-title" style="font-size: 15px; margin: 24px 0 8px;">Stdout</h2>
      <div class="gh-code-view-shell">
        <div class="gh-code-editor-toolbar">Stdout</div>
        <pre class="gh-code-block gh-code-block-python">{submission.stdout?.trim() || "—"}</pre>
      </div>

      <h2 class="gh-title" style="font-size: 15px; margin: 24px 0 8px;">Feedback</h2>
      <div class="gh-code-view-shell">
        <div class="gh-code-editor-toolbar">Text</div>
        <pre class="gh-code-block gh-code-block-python">{submission.feedback?.trim() || "—"}</pre>
      </div>
    {/if}
  {/if}
</section>
