<script lang="ts">
  import { onMount } from "svelte";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import { fetchAssignments, type AssignmentRead } from "$lib/api";
  import { formatDateTime } from "$lib/format";
  import { tableRowClick, tableRowKeydown } from "$lib/tableRowNav";
  import { PATH_STUDENT_HOME } from "$lib/paths";

  let rows: AssignmentRead[] = [];
  let errorMsg = "";
  let loading = true;

  onMount(async () => {
    loading = true;
    errorMsg = "";
    try {
      rows = await fetchAssignments();
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Failed to load assignments";
    } finally {
      loading = false;
    }
  });
</script>

<section>
  <Breadcrumbs
    items={[
      { label: "Student", href: PATH_STUDENT_HOME },
      { label: "Assignments" },
    ]}
  />
  <h1 class="gh-title" style="margin-top: 0; margin-bottom: 8px;">Assignments</h1>
  <p class="gh-subtitle" style="margin-bottom: 20px;">
    Assignments you are enrolled in. Open one for details and your work.
  </p>

  {#if errorMsg}
    <div class="gh-alert gh-alert-error">{errorMsg}</div>
  {/if}

  {#if loading}
    <p class="gh-muted">Loading…</p>
  {:else if rows.length === 0}
    <div class="gh-card" style="max-width: none;">
      <p class="gh-muted" style="margin: 0;">You are not assigned to any assignment yet.</p>
    </div>
  {:else}
    <div class="gh-table-wrap">
      <table class="gh-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Due</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {#each rows as a (a.id)}
            <tr
              class="gh-table-row-click"
              role="link"
              tabindex="0"
              aria-label="Open assignment {a.title}"
              on:click={(e) => tableRowClick(e, `/app/student/assignments/${a.id}`)}
              on:keydown={(e) => tableRowKeydown(e, `/app/student/assignments/${a.id}`)}
            >
              <td><strong>{a.title}</strong></td>
              <td class="gh-muted">{formatDateTime(a.due_date)}</td>
              <td class="gh-muted">{formatDateTime(a.updated_at)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>
