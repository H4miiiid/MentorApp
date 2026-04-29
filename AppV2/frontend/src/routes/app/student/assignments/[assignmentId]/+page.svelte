<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import { PATH_STUDENT_HOME } from "$lib/paths";
  import {
    createSubmission,
    downloadDocumentFile,
    fetchAssignment,
    fetchAssignmentDocuments,
    fetchSubmissions,
    fetchUsers,
    removeSubmissionFromMyList,
    type AssignmentRead,
    type DocumentRead,
    type SubmissionRead,
    type UserRead,
  } from "$lib/api";
  import PythonCodeEditor from "$lib/components/PythonCodeEditor.svelte";
  import SubmissionStatusBadge from "$lib/components/SubmissionStatusBadge.svelte";
  import { formatBytes, formatDateTime, formatSubmissionGrade } from "$lib/format";
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

  let resources: DocumentRead[] = [];
  let busyDocId: string | null = null;
  let resourceError = "";
  let removeBusyId: string | null = null;

  async function removeFromList(submissionId: string, e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (
      !confirm(
        "Remove this submission from your list? It stays in the system for your teacher and grading records."
      )
    ) {
      return;
    }
    if (!assignment || !me) return;
    removeBusyId = submissionId;
    resourceError = "";
    try {
      await removeSubmissionFromMyList(submissionId);
      mySubmissions = mySubmissions.filter((x) => x.id !== submissionId);
    } catch (err) {
      resourceError =
        err instanceof Error ? err.message : "Could not remove submission";
    } finally {
      removeBusyId = null;
    }
  }

  function basename(path: string): string {
    const parts = (path || "").replace(/\\/g, "/").split("/");
    return parts[parts.length - 1] || path;
  }

  async function onDownloadResource(d: DocumentRead) {
    busyDocId = d.id;
    resourceError = "";
    try {
      await downloadDocumentFile(d.id, basename(d.file_path) || d.title);
    } catch (e) {
      resourceError = e instanceof Error ? e.message : "Download failed";
    } finally {
      busyDocId = null;
    }
  }

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
      const [a, subs, users, docs] = await Promise.all([
        fetchAssignment(id),
        fetchSubmissions(),
        fetchUsers(),
        fetchAssignmentDocuments(id).catch(() => [] as DocumentRead[]),
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
      resources = docs;
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Failed to load";
      assignment = null;
      mySubmissions = [];
      resources = [];
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

    {#if resources.length > 0}
      <div class="gh-card" style="max-width: none; margin-bottom: 20px;">
        <h2 class="gh-title" style="font-size: 16px; margin-bottom: 8px;">Assignment resources</h2>
        <p class="gh-subtitle" style="margin: 0 0 12px;">
          Files your teacher attached to this assignment. You can download them locally and they are
          also available inside the grading sandbox.
        </p>
        {#if resourceError}
          <div class="gh-alert gh-alert-error" style="margin-bottom: 12px;">{resourceError}</div>
        {/if}
        <ul style="list-style: none; padding: 0; margin: 0 0 16px;">
          {#each resources as d (d.id)}
            <li
              style="display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--gh-border, rgba(240,246,252,0.1));"
            >
              <div style="min-width: 0;">
                <strong>{d.title}</strong>
                <div class="gh-muted" style="font-size: 12px;">
                  {basename(d.file_path)} · {formatBytes(d.file_size_bytes)}{d.file_type ? ` · ${d.file_type}` : ""}
                </div>
                {#if d.description}
                  <div class="gh-muted" style="font-size: 12px; margin-top: 4px;">{d.description}</div>
                {/if}
              </div>
              <button
                type="button"
                class="gh-btn"
                style="padding: 4px 10px; font-size: 12px; white-space: nowrap;"
                disabled={busyDocId === d.id}
                on:click={() => onDownloadResource(d)}
              >
                {busyDocId === d.id ? "…" : "Download"}
              </button>
            </li>
          {/each}
        </ul>

        <div
          class="gh-alert"
          style="border-left: 3px solid var(--gh-accent, #58a6ff); padding: 12px 14px; font-size: 13px;"
        >
          <strong>How to open these files in your submission</strong>
          <p style="margin: 6px 0 8px;">
            During grading, the files above are copied into a read-only directory inside the sandbox. The
            path is provided via the <code>ASSIGNMENT_DATA_DIR</code> environment variable. Do not
            hard-code filenames or absolute paths — use <code>os.environ</code> so your code runs both
            locally and in the sandbox.
          </p>
          <pre
            style="margin: 0; padding: 10px 12px; background: rgba(110,118,129,0.15); border-radius: 6px; white-space: pre-wrap; overflow-x: auto; font-size: 12px;"
          ><code>{`import os
import pandas as pd

data_dir = os.environ["ASSIGNMENT_DATA_DIR"]
df = pd.read_csv(os.path.join(data_dir, "${basename(resources[0]?.file_path || "file1.csv")}"), sep=";")`}</code></pre>
        </div>
      </div>
    {/if}

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
        {#if resources.length > 0}
          <div
            class="gh-alert"
            style="border-left: 3px solid var(--gh-accent, #58a6ff); padding: 10px 12px; font-size: 12px; margin-bottom: 12px;"
          >
            This assignment has {resources.length} attached file{resources.length === 1 ? "" : "s"}. To
            read them, use <code>os.environ["ASSIGNMENT_DATA_DIR"]</code> — never hard-code paths.
          </div>
        {/if}
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
              <th class="gh-muted" style="text-align: right; width: 1%; white-space: nowrap;">Actions</th>
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
                <td style="text-align: right;" on:click|stopPropagation>
                  <button
                    type="button"
                    class="gh-btn gh-btn-sm"
                    disabled={removeBusyId === s.id}
                    title="Remove from your list (submission is kept for records)"
                    aria-label="Remove submission from list"
                    on:click={(e) => removeFromList(s.id, e)}
                  >
                    {removeBusyId === s.id ? "…" : "Remove"}
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  {/if}
</section>
