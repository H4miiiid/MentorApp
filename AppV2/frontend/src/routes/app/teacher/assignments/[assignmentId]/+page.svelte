<script lang="ts">
  import { page } from "$app/stores";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import DocumentPicker from "$lib/components/DocumentPicker.svelte";
  import { PATH_TEACHER_HOME } from "$lib/paths";
  import {
    addAssignmentStudents,
    fetchAssignment,
    fetchAssignmentDocuments,
    fetchAssignmentStudents,
    fetchDocuments,
    fetchSubmissions,
    fetchUsers,
    setAssignmentDocuments,
    type AssignmentRead,
    type AssignmentStudentRead,
    type DocumentRead,
    type SubmissionRead,
    type SubmissionStatus,
    type UserRead,
  } from "$lib/api";
  import SubmissionStatusBadge from "$lib/components/SubmissionStatusBadge.svelte";
  import { formatDateTime, formatSubmissionGrade } from "$lib/format";
  import { tableRowClick, tableRowKeydown } from "$lib/tableRowNav";

  type StatusFilter = "all" | "none" | SubmissionStatus;

  let assignment: AssignmentRead | null = null;
  let enrollments: AssignmentStudentRead[] = [];
  let submissions: SubmissionRead[] = [];
  let usersById = new Map<string, UserRead>();
  let errorMsg = "";
  let loading = true;

  let selectedToAdd: string[] = [];
  let addSearchQuery = "";
  let addingStudents = false;
  let addStudentsError = "";
  let showAddStudentsPanel = false;

  let studentNameSearch = "";
  let statusFilter: StatusFilter = "all";
  let sortBy: "name" | "activity" = "name";
  let sortOrder: "asc" | "desc" = "asc";

  let attachedDocs: DocumentRead[] = [];
  let libraryDocs: DocumentRead[] = [];
  let selectedDocIds: string[] = [];
  let docsSaving = false;
  let docsError = "";
  let docsMessage = "";

  $: assignmentId = $page.params.assignmentId ?? "";

  function nameForUser(id: string): string {
    return usersById.get(id)?.full_name ?? id.slice(0, 8) + "…";
  }

  function emailForUser(id: string): string {
    return usersById.get(id)?.email ?? "—";
  }

  async function load(id: string) {
    if (!id) {
      loading = false;
      return;
    }
    loading = true;
    errorMsg = "";
    try {
      const [a, studs, subs, users, attached, lib] = await Promise.all([
        fetchAssignment(id),
        fetchAssignmentStudents(id),
        fetchSubmissions(),
        fetchUsers(),
        fetchAssignmentDocuments(id),
        fetchDocuments({ includeArchived: false }),
      ]);
      assignment = a;
      enrollments = studs;
      submissions = subs.filter((s) => s.assignment_id === id);
      usersById = new Map(users.map((u) => [u.id, u]));
      attachedDocs = attached;
      libraryDocs = lib;
      selectedDocIds = attached.map((d) => d.id);
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Failed to load";
      assignment = null;
    } finally {
      loading = false;
    }
  }

  async function saveAttachedDocs() {
    if (!assignmentId) return;
    docsError = "";
    docsMessage = "";
    docsSaving = true;
    try {
      const next = await setAssignmentDocuments(assignmentId, selectedDocIds);
      attachedDocs = next;
      selectedDocIds = next.map((d) => d.id);
      docsMessage = `Saved ${next.length} document${next.length === 1 ? "" : "s"} to this assignment.`;
    } catch (e) {
      docsError = e instanceof Error ? e.message : "Failed to save attached documents";
    } finally {
      docsSaving = false;
    }
  }

  $: hasDocsChanges = (() => {
    const a = new Set(attachedDocs.map((d) => d.id));
    const b = new Set(selectedDocIds);
    if (a.size !== b.size) return true;
    for (const id of a) if (!b.has(id)) return true;
    return false;
  })();

  $: load(assignmentId);

  $: allStudents = Array.from(usersById.values()).filter(
    (u) => u.role === "student" && u.is_active
  );
  $: enrolledIds = new Set(enrollments.map((e) => e.student_id));
  $: studentsNotOnAssignment = allStudents.filter((s) => !enrolledIds.has(s.id));
  $: filteredForAdd = studentsNotOnAssignment.filter((s) => {
    const q = addSearchQuery.trim().toLowerCase();
    if (!q) return true;
    return (
      s.full_name.toLowerCase().includes(q) ||
      s.email.toLowerCase().includes(q) ||
      (s.student_id_number && s.student_id_number.toLowerCase().includes(q))
    );
  });
  $: selectedToAddCount = selectedToAdd.length;

  /** Most recently updated submission per student for this assignment. */
  $: latestByStudent = (() => {
    const m = new Map<string, SubmissionRead>();
    for (const s of submissions) {
      const cur = m.get(s.student_id);
      if (!cur || new Date(s.updated_at) > new Date(cur.updated_at)) {
        m.set(s.student_id, s);
      }
    }
    return m;
  })();

  function rowStatus(row: AssignmentStudentRead): "none" | SubmissionStatus {
    const latest = latestByStudent.get(row.student_id);
    return latest ? latest.status : "none";
  }

  $: filteredRows = enrollments.filter((row) => {
    const q = studentNameSearch.trim().toLowerCase();
    if (q) {
      const name = nameForUser(row.student_id).toLowerCase();
      const email = emailForUser(row.student_id).toLowerCase();
      if (!name.includes(q) && !email.includes(q)) return false;
    }
    const st = rowStatus(row);
    if (statusFilter !== "all") {
      if (statusFilter === "none") return st === "none";
      return st === statusFilter;
    }
    return true;
  });

  $: displayRows = [...filteredRows].sort((a, b) => {
    if (sortBy === "name") {
      const na = nameForUser(a.student_id);
      const nb = nameForUser(b.student_id);
      const c = na.localeCompare(nb);
      return sortOrder === "asc" ? c : -c;
    }
    const ta = latestByStudent.get(a.student_id)?.updated_at ?? "";
    const tb = latestByStudent.get(b.student_id)?.updated_at ?? "";
    const da = ta ? new Date(ta).getTime() : 0;
    const db = tb ? new Date(tb).getTime() : 0;
    const c = da - db;
    return sortOrder === "asc" ? c : -c;
  });

  function selectAllFilteredAdd() {
    const set = new Set(selectedToAdd);
    for (const s of filteredForAdd) {
      set.add(s.id);
    }
    selectedToAdd = [...set];
  }

  function clearFilteredAdd() {
    const remove = new Set(filteredForAdd.map((s) => s.id));
    selectedToAdd = selectedToAdd.filter((id) => !remove.has(id));
  }

  async function submitAddStudents() {
    addStudentsError = "";
    if (selectedToAdd.length === 0 || !assignmentId) return;
    addingStudents = true;
    try {
      await addAssignmentStudents(assignmentId, selectedToAdd);
      selectedToAdd = [];
      addSearchQuery = "";
      await load(assignmentId);
    } catch (e) {
      addStudentsError = e instanceof Error ? e.message : "Failed to add students";
    } finally {
      addingStudents = false;
    }
  }
</script>

<section>
  <Breadcrumbs
    items={[
      { label: "Teacher", href: PATH_TEACHER_HOME },
      { label: "Assignments", href: PATH_TEACHER_HOME },
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
      Due: {formatDateTime(assignment.due_date)} · Updated {formatDateTime(assignment.updated_at)}
    </p>

    <div class="gh-card" style="max-width: none; margin-bottom: 24px;">
      <h2 class="gh-title" style="font-size: 16px; margin-bottom: 8px;">Description</h2>
      <p style="margin: 0; white-space: pre-wrap;">{assignment.description || "—"}</p>
    </div>

    <div class="gh-card" style="max-width: none; margin-bottom: 24px;">
      <h2 class="gh-title" style="font-size: 16px; margin-bottom: 4px;">Attached documents</h2>
      <p class="gh-subtitle" style="margin: 0 0 12px;">
        Select previously uploaded documents that students may download for this assignment. Attached
        files are also made available inside the grading sandbox via
        <code>$ASSIGNMENT_DATA_DIR</code>. Upload new files from the
        <a href="/app/teacher/documents">Documents tab</a>.
      </p>

      {#if docsError}
        <div class="gh-alert gh-alert-error" style="margin-bottom: 12px;">{docsError}</div>
      {/if}
      {#if docsMessage}
        <div class="gh-alert" style="margin-bottom: 12px;">{docsMessage}</div>
      {/if}

      <div style="margin-bottom: 12px;">
        <DocumentPicker
          documents={libraryDocs}
          bind:selectedIds={selectedDocIds}
          idPrefix="attach-doc"
          summaryLabel="Select documents to attach"
          emptyLabel="Your library is empty. Upload documents first, then return to attach them here."
          open={attachedDocs.length > 0}
        />
      </div>
      <div class="gh-form-actions" style="margin: 0;">
        <button
          type="button"
          class="gh-btn gh-btn-primary"
          disabled={docsSaving || !hasDocsChanges || libraryDocs.length === 0}
          on:click={saveAttachedDocs}
        >
          {docsSaving ? "Saving…" : "Save attached documents"}
        </button>
        <span class="gh-muted" style="font-size: 12px;">
          {selectedDocIds.length} selected · {attachedDocs.length} currently attached
        </span>
      </div>
    </div>

    <div
      style="display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 12px;"
    >
      <div>
        <h2 class="gh-title" style="font-size: 16px; margin: 0 0 4px;">Students</h2>
        <p class="gh-subtitle" style="margin: 0;">
          Latest submission per enrolled student (status updates as work is processed).
        </p>
      </div>
      <button
        type="button"
        class="gh-btn gh-btn-primary"
        style="white-space: nowrap;"
        on:click={() => (showAddStudentsPanel = !showAddStudentsPanel)}
      >
        {showAddStudentsPanel ? "Close add students" : "Add students"}
      </button>
    </div>

    {#if showAddStudentsPanel}
      <div class="gh-card" style="max-width: none; margin-bottom: 20px;">
        <h3 class="gh-title" style="font-size: 15px; margin-bottom: 8px;">Enroll more students</h3>
        {#if allStudents.length === 0}
          <p class="gh-muted" style="margin: 0;">
            There are no active student accounts in the system yet, so no one can be enrolled.
          </p>
        {:else if studentsNotOnAssignment.length === 0}
          <p class="gh-muted" style="margin: 0;">
            Every active student is already enrolled on this assignment. Create new student accounts or deactivate
            users elsewhere if you need different rosters.
          </p>
        {:else}
          <p class="gh-muted" style="margin: 0 0 12px; font-size: 13px;">
            Select students below, then add them to this assignment.
          </p>
          {#if addStudentsError}
            <div class="gh-alert gh-alert-error" style="margin-bottom: 12px;">{addStudentsError}</div>
          {/if}
          <details class="gh-student-dropdown" open>
            <summary>
              Choose students to add ({selectedToAddCount} selected)
            </summary>
            <div class="gh-student-dropdown-tools">
              <input
                class="gh-input"
                type="search"
                placeholder="Filter by name, email, or student ID…"
                bind:value={addSearchQuery}
                aria-label="Filter students to add"
              />
              <button
                type="button"
                class="gh-btn"
                style="padding: 6px 10px; font-size: 12px;"
                on:click={selectAllFilteredAdd}
              >
                Select all shown
              </button>
              <button
                type="button"
                class="gh-btn"
                style="padding: 6px 10px; font-size: 12px;"
                on:click={clearFilteredAdd}
              >
                Clear shown
              </button>
            </div>
            <div class="gh-checkbox-list">
              {#each filteredForAdd as s (s.id)}
                <div class="gh-checkbox-row">
                  <input id="add-st-{s.id}" type="checkbox" value={s.id} bind:group={selectedToAdd} />
                  <label for="add-st-{s.id}">
                    <strong>{s.full_name}</strong>
                    <span class="gh-muted" style="display: block; font-size: 12px;">{s.email}</span>
                    {#if s.student_id_number}
                      <span class="gh-muted" style="font-size: 12px;">ID: {s.student_id_number}</span>
                    {/if}
                  </label>
                </div>
              {:else}
                <p class="gh-muted" style="margin: 0;">No students match your filter.</p>
              {/each}
            </div>
          </details>
          <div class="gh-form-actions" style="margin-top: 16px; margin-bottom: 0;">
            <button
              type="button"
              class="gh-btn gh-btn-primary"
              disabled={addingStudents || selectedToAdd.length === 0}
              on:click={submitAddStudents}
            >
              {addingStudents ? "Adding…" : "Add selected to assignment"}
            </button>
          </div>
        {/if}
      </div>
    {/if}

    {#if enrollments.length === 0}
      <div class="gh-card" style="max-width: none;">
        <p class="gh-muted" style="margin: 0;">
          No students enrolled yet. Use <strong>Add students</strong> to enroll learners on this assignment.
        </p>
      </div>
    {:else}
      <p class="gh-muted" style="margin: 0 0 10px; font-size: 13px;">
        Showing {displayRows.length} of {enrollments.length} student{enrollments.length === 1 ? "" : "s"}
        {#if filteredRows.length !== enrollments.length}
          (filters applied)
        {/if}
      </p>
      <div class="gh-toolbar-filters">
        <input
          class="gh-input"
          type="search"
          placeholder="Search name or email…"
          bind:value={studentNameSearch}
          aria-label="Search students"
          style="flex: 1; min-width: 180px;"
        />
        <select class="gh-input" bind:value={statusFilter} aria-label="Filter by status" style="width: auto;">
          <option value="all">All statuses</option>
          <option value="none">No submission</option>
          <option value="pending">pending</option>
          <option value="running">running</option>
          <option value="completed">completed</option>
          <option value="failed">failed</option>
        </select>
        <select class="gh-input" bind:value={sortBy} aria-label="Sort by" style="width: auto;">
          <option value="name">Sort by name</option>
          <option value="activity">Sort by last activity</option>
        </select>
        <select class="gh-input" bind:value={sortOrder} aria-label="Order" style="width: auto;">
          <option value="asc">Ascending (A→Z / oldest first)</option>
          <option value="desc">Descending (Z→A / newest first)</option>
        </select>
      </div>
      <div class="gh-table-wrap">
        <table class="gh-table">
          <thead>
            <tr>
              <th>Student</th>
              <th>Email</th>
              <th>Enrolled</th>
              <th>Latest status</th>
              <th>Grade</th>
              <th>Last activity</th>
            </tr>
          </thead>
          <tbody>
            {#each displayRows as row (row.student_id)}
              {@const latest = latestByStudent.get(row.student_id)}
              <tr
                class:gh-table-row-click={!!latest}
                role={latest ? "link" : undefined}
                tabindex={latest ? 0 : undefined}
                aria-label={latest
                  ? `Open latest submission for ${nameForUser(row.student_id)}`
                  : undefined}
                on:click={latest
                  ? (e) => tableRowClick(e, `/app/teacher/submissions/${latest.id}`)
                  : undefined}
                on:keydown={latest
                  ? (e) => tableRowKeydown(e, `/app/teacher/submissions/${latest.id}`)
                  : undefined}
              >
                <td>{nameForUser(row.student_id)}</td>
                <td class="gh-muted">{emailForUser(row.student_id)}</td>
                <td class="gh-muted">{formatDateTime(row.assigned_at)}</td>
                <td>
                  {#if latest}
                    <SubmissionStatusBadge status={latest.status} />
                  {:else}
                    <span class="gh-muted">No submission yet</span>
                  {/if}
                </td>
                <td>
                  {#if latest}
                    {formatSubmissionGrade(latest.grade, latest.status)}
                  {:else}
                    <span class="gh-muted">—</span>
                  {/if}
                </td>
                <td class="gh-muted">
                  {#if latest}
                    {formatDateTime(latest.updated_at)}
                  {:else}
                    —
                  {/if}
                </td>
              </tr>
            {:else}
              <tr>
                <td colspan="6" class="gh-muted">No students match the current filters.</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  {/if}
</section>
