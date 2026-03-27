<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import { PATH_STUDENT_HOME } from "$lib/paths";
  import {
    createSubmission,
    fetchAssignment,
    fetchSubmissions,
    fetchUsers,
    type AssignmentRead,
    type SubmissionRead,
    type UserRead,
  } from "$lib/api";
  import PythonCodeEditor from "$lib/components/PythonCodeEditor.svelte";
  import SubmissionStatusBadge from "$lib/components/SubmissionStatusBadge.svelte";
  import { formatDateTime, formatSubmissionGrade } from "$lib/format";
  import { tableRowClick, tableRowKeydown } from "$lib/tableRowNav";

  let assignment: AssignmentRead | null = null;
  let mySubmissions: SubmissionRead[] = [];
  let teacherName = "—";
  let errorMsg = "";
  let loading = true;

  const pythonCodePlaceholder = "# Your solution\ndef main():\n    pass";

  let showCreateForm = false;
  let newCode = "";
  let formError = "";
  let submitting = false;

  $: assignmentId = $page.params.assignmentId ?? "";
  $: me = $page.data.user;
  $: submissionCount = mySubmissions.length;

  async function load(id: string) {
    if (!id || !me) {
      loading = false;
      return;
    }
    loading = true;
    errorMsg = "";
    try {
      const [a, subs, users] = await Promise.all([
        fetchAssignment(id),
        fetchSubmissions(),
        fetchUsers(),
      ]);
      assignment = a;
      const byUser = users.reduce<Record<string, UserRead>>((acc, u) => {
        acc[u.id] = u;
        return acc;
      }, {});
      teacherName = byUser[a.teacher_id]?.full_name ?? a.teacher_id.slice(0, 8) + "…";
      const mine = subs.filter((s) => s.assignment_id === id && s.student_id === me.id);
      mySubmissions = mine.sort(
        (x, y) => new Date(y.updated_at).getTime() - new Date(x.updated_at).getTime()
      );
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Failed to load";
      assignment = null;
      mySubmissions = [];
    } finally {
      loading = false;
    }
  }

  $: {
    const id = assignmentId;
    const u = me;
    if (id && u) void load(id);
  }

  function openCreateForm() {
    formError = "";
    newCode = "";
    showCreateForm = true;
  }

  function cancelCreateForm() {
    showCreateForm = false;
    formError = "";
    newCode = "";
  }

  async function submitNewSubmission() {
    formError = "";
    if (!assignment || !me || me.role !== "student") {
      formError = "You must be signed in as a student.";
      return;
    }
    const code = newCode.trim();
    if (code.length < 1) {
      formError = "Enter your submission (code or text).";
      return;
    }
    submitting = true;
    try {
      const created = await createSubmission({
        assignment_id: assignment.id,
        student_id: me.id,
        code,
      });
      showCreateForm = false;
      newCode = "";
      await goto(`/app/student/submissions/${created.id}`);
    } catch (e) {
      formError = e instanceof Error ? e.message : "Could not create submission";
    } finally {
      submitting = false;
    }
  }
</script>

<section>
  <Breadcrumbs
    items={[
      { label: "Student", href: PATH_STUDENT_HOME },
      { label: "Assignments", href: PATH_STUDENT_HOME },
      { label: assignment?.title ?? "…" },
    ]}
  />

  {#if errorMsg}
    <div class="gh-alert gh-alert-error">{errorMsg}</div>
  {/if}

  {#if loading}
    <p class="gh-muted">Loading…</p>
  {:else if assignment}
    <h1 class="gh-title" style="margin-top: 0; margin-bottom: 8px;">{assignment.title}</h1>
    <p class="gh-muted" style="margin-bottom: 20px;">
      Teacher: {teacherName} · Due: {formatDateTime(assignment.due_date)} · Updated{" "}
      {formatDateTime(assignment.updated_at)}
    </p>

    <div class="gh-card" style="max-width: none; margin-bottom: 20px;">
      <h2 class="gh-title" style="font-size: 16px; margin-bottom: 8px;">Description</h2>
      <p style="margin: 0; white-space: pre-wrap;">{assignment.description || "—"}</p>
    </div>

    <div
      class="gh-card"
      style="max-width: none; margin-bottom: 20px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px;"
    >
      <div>
        <p style="margin: 0; font-size: 15px;">
          <strong>{submissionCount}</strong>
          {submissionCount === 1 ? "submission" : "submissions"}
          for this assignment (by you).
        </p>
        <p class="gh-muted" style="margin: 6px 0 0; font-size: 13px;">
          Each new submission is stored separately. You can open past submissions below.
        </p>
      </div>
      {#if !showCreateForm}
        <button type="button" class="gh-btn gh-btn-primary" style="white-space: nowrap;" on:click={openCreateForm}>
          Create new submission
        </button>
      {/if}
    </div>

    {#if showCreateForm}
      <div class="gh-card" style="max-width: none; margin-bottom: 24px;">
        <h2 class="gh-title" style="font-size: 16px; margin-bottom: 12px;">New submission</h2>
        <p class="gh-muted" style="margin-bottom: 12px;">
          Paste your answer, code, or text for this assignment. Your teacher will see this submission in their
          panel.
        </p>
        {#if formError}
          <div class="gh-alert gh-alert-error">{formError}</div>
        {/if}
        <div class="gh-field" style="margin-bottom: 0;">
          <span class="gh-label">Your work (Python)</span>
          <div class="gh-code-view-shell">
            <div class="gh-code-editor-toolbar">Python · syntax highlighting</div>
            <div class="gh-cm-editor-host">
              <PythonCodeEditor bind:value={newCode} placeholderText={pythonCodePlaceholder} />
            </div>
          </div>
        </div>
        <div class="gh-form-actions" style="margin-top: 16px;">
          <button
            type="button"
            class="gh-btn gh-btn-primary"
            disabled={submitting}
            on:click={submitNewSubmission}
          >
            {submitting ? "Submitting…" : "Submit"}
          </button>
          <button type="button" class="gh-btn" disabled={submitting} on:click={cancelCreateForm}>
            Cancel
          </button>
        </div>
      </div>
    {/if}

    <h2 class="gh-title" style="font-size: 16px; margin-bottom: 12px;">Your submissions</h2>
    {#if mySubmissions.length === 0}
      <p class="gh-muted">You have not submitted anything for this assignment yet.</p>
    {:else}
      <div class="gh-table-wrap">
        <table class="gh-table">
          <thead>
            <tr>
              <th style="width: 48px;">#</th>
              <th>Status</th>
              <th>Grade</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {#each mySubmissions as s, i (s.id)}
              <tr
                class="gh-table-row-click"
                role="link"
                tabindex="0"
                aria-label="Open submission {i + 1}"
                on:click={(e) => tableRowClick(e, `/app/student/submissions/${s.id}`)}
                on:keydown={(e) => tableRowKeydown(e, `/app/student/submissions/${s.id}`)}
              >
                <td class="gh-muted">{i + 1}</td>
                <td><SubmissionStatusBadge status={s.status} /></td>
                <td>{formatSubmissionGrade(s.grade, s.status)}</td>
                <td class="gh-muted">{formatDateTime(s.updated_at)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  {/if}
</section>
