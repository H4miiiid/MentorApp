<script lang="ts">
  import { onMount } from "svelte";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import {
    fetchAssignments,
    removeAssignmentFromLists,
    type AssignmentRead,
  } from "$lib/api";
  import { formatDateTime } from "$lib/format";
  import { tableRowClick, tableRowKeydown } from "$lib/tableRowNav";
  import { PATH_TEACHER_HOME, PATH_TEACHER_NEW_ASSIGNMENT } from "$lib/paths";

  let rows: AssignmentRead[] = [];
  let errorMsg = "";
  let loading = true;
  let removeBusyId: string | null = null;

  async function load() {
    loading = true;
    errorMsg = "";
    try {
      rows = await fetchAssignments();
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Failed to load assignments";
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    void load();
  });

  async function removeFromLists(assignmentId: string, e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (
      !confirm(
        "Remove this assignment from your list and from all students’ assignment lists? Past submissions and grades stay in the system."
      )
    ) {
      return;
    }
    removeBusyId = assignmentId;
    errorMsg = "";
    try {
      await removeAssignmentFromLists(assignmentId);
      rows = rows.filter((r) => r.id !== assignmentId);
    } catch (err) {
      errorMsg = err instanceof Error ? err.message : "Could not remove assignment";
    } finally {
      removeBusyId = null;
    }
  }
</script>

<section>
  <Breadcrumbs
    items={[
      { label: "Teacher", href: PATH_TEACHER_HOME },
      { label: "Assignments" },
    ]}
  />
  <div
    style="display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 20px;"
  >
    <div>
      <h1 class="gh-title" style="margin: 0 0 8px;">Assignments</h1>
      <p class="gh-subtitle" style="margin: 0;">
        Assignments you created. Open one to see enrolled students and submissions.
      </p>
    </div>
    <a href={PATH_TEACHER_NEW_ASSIGNMENT} class="gh-btn gh-btn-primary" style="white-space: nowrap;">
      Create new assignment
    </a>
  </div>

  {#if errorMsg}
    <div class="gh-alert gh-alert-error">{errorMsg}</div>
  {/if}

  {#if loading}
    <p class="gh-muted">Loading…</p>
  {:else if rows.length === 0}
    <div class="gh-card" style="max-width: none;">
      <p class="gh-muted" style="margin: 0;">
        No assignments yet. Use <strong>Create new assignment</strong> to add one.
      </p>
    </div>
  {:else}
    <div class="gh-table-wrap">
      <table class="gh-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Due</th>
            <th>Updated</th>
            <th scope="col" class="gh-muted" style="text-align: right; width: 1%; white-space: nowrap;">Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each rows as a (a.id)}
            <tr
              class="gh-table-row-click"
              role="link"
              tabindex="0"
              aria-label="Open assignment {a.title}"
              on:click={(e) => tableRowClick(e, `/app/teacher/assignments/${a.id}`)}
              on:keydown={(e) => tableRowKeydown(e, `/app/teacher/assignments/${a.id}`)}
            >
              <td><strong>{a.title}</strong></td>
              <td class="gh-muted">{formatDateTime(a.due_date)}</td>
              <td class="gh-muted">{formatDateTime(a.updated_at)}</td>
              <td style="text-align: right;" on:click|stopPropagation>
                <button
                  type="button"
                  class="gh-btn gh-btn-sm"
                  disabled={removeBusyId === a.id}
                  title="Remove from your list and students’ lists (assignment data is kept)"
                  aria-label="Remove assignment from lists"
                  on:click={(e) => removeFromLists(a.id, e)}
                >
                  {removeBusyId === a.id ? "…" : "Remove"}
                </button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>
