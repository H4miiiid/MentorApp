<script lang="ts">
  import { onMount } from "svelte";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import {
    fetchAssignments,
    fetchSubmissions,
    type AssignmentRead,
    type SubmissionRead,
  } from "$lib/api";
  import SubmissionStatusBadge from "$lib/components/SubmissionStatusBadge.svelte";
  import { formatDateTime, formatSubmissionGrade } from "$lib/format";
  import { tableRowClick, tableRowKeydown } from "$lib/tableRowNav";
  import { PATH_STUDENT_HOME } from "$lib/paths";

  let submissions: SubmissionRead[] = [];
  let assignmentsById = new Map<string, AssignmentRead>();
  let errorMsg = "";
  let loading = true;

  onMount(async () => {
    loading = true;
    errorMsg = "";
    try {
      const [subs, assigns] = await Promise.all([fetchSubmissions(), fetchAssignments()]);
      submissions = subs;
      assignmentsById = new Map(assigns.map((a) => [a.id, a]));
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Failed to load submissions";
    } finally {
      loading = false;
    }
  });

  function assignmentTitle(id: string): string {
    return assignmentsById.get(id)?.title ?? id.slice(0, 8) + "…";
  }
</script>

<section>
  <Breadcrumbs
    items={[
      { label: "Student", href: PATH_STUDENT_HOME },
      { label: "Submissions" },
    ]}
  />
  <h1 class="gh-title" style="margin-top: 0; margin-bottom: 8px;">Submissions</h1>
  <p class="gh-subtitle" style="margin-bottom: 20px;">All submissions you have made across assignments.</p>

  {#if errorMsg}
    <div class="gh-alert gh-alert-error">{errorMsg}</div>
  {/if}

  {#if loading}
    <p class="gh-muted">Loading…</p>
  {:else if submissions.length === 0}
    <div class="gh-card" style="max-width: none;">
      <p class="gh-muted" style="margin: 0;">No submissions yet.</p>
    </div>
  {:else}
    <div class="gh-table-wrap">
      <table class="gh-table">
        <thead>
          <tr>
            <th>Assignment</th>
            <th>Status</th>
            <th>Grade</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {#each submissions as s (s.id)}
            <tr
              class="gh-table-row-click"
              role="link"
              tabindex="0"
              aria-label="Open submission for {assignmentTitle(s.assignment_id)}"
              on:click={(e) => tableRowClick(e, `/app/student/submissions/${s.id}`)}
              on:keydown={(e) => tableRowKeydown(e, `/app/student/submissions/${s.id}`)}
            >
              <td><strong>{assignmentTitle(s.assignment_id)}</strong></td>
              <td><SubmissionStatusBadge status={s.status} /></td>
              <td>{formatSubmissionGrade(s.grade, s.status)}</td>
              <td class="gh-muted">{formatDateTime(s.updated_at)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>
