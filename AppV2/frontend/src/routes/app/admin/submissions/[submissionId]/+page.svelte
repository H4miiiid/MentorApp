<script lang="ts">
  import { page } from "$app/stores";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import SubmissionStatusBadge from "$lib/components/SubmissionStatusBadge.svelte";
  import {
    fetchAssignment,
    fetchSubmission,
    fetchUsers,
    type AssignmentRead,
    type SubmissionRead,
    type UserRead,
  } from "$lib/api";
  import { formatDateTime, formatSubmissionGrade } from "$lib/format";
  import { PATH_ADMIN_HOME } from "$lib/paths";

  let submission: SubmissionRead | null = null;
  let assignment: AssignmentRead | null = null;
  let student: UserRead | undefined;
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
      const [a, users] = await Promise.all([fetchAssignment(sub.assignment_id), fetchUsers()]);
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
      { label: "Admin", href: PATH_ADMIN_HOME },
      { label: "Users", href: "/app/admin/users" },
      {
        label: student?.full_name ?? "User",
        href: student ? `/app/admin/users/${student.id}` : "/app/admin/users",
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
    <h1 class="gh-title" style="margin-top: 0; margin-bottom: 8px;">Submission (admin)</h1>
    <p class="gh-muted" style="margin-bottom: 20px;">
      Student: <strong>{student?.full_name ?? submission.student_id}</strong> · Assignment:{" "}
      <strong>{assignment.title}</strong>
    </p>

    <div class="gh-card" style="max-width: none; margin-bottom: 20px;">
      <dl class="gh-dl">
        <dt>Status</dt>
        <dd><SubmissionStatusBadge status={submission.status} /></dd>
        <dt>Grade</dt>
        <dd>{formatSubmissionGrade(submission.grade, submission.status)}</dd>
        <dt>Updated</dt>
        <dd>{formatDateTime(submission.updated_at)}</dd>
      </dl>
    </div>

    <h2 class="gh-title" style="font-size: 15px; margin-bottom: 8px;">Code</h2>
    <div class="gh-code-view-shell">
      <div class="gh-code-editor-toolbar">Python</div>
      <pre class="gh-code-block gh-code-block-python">{submission.code || "—"}</pre>
    </div>
  {/if}
</section>
