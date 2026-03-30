<script lang="ts">
  import { onMount } from "svelte";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import { fetchAdminUsers, type UserRead, type UserRole } from "$lib/api";
  import { formatDateTime } from "$lib/format";
  import { PATH_ADMIN_HOME } from "$lib/paths";
  import { tableRowClick, tableRowKeydown } from "$lib/tableRowNav";

  let rows: UserRead[] = [];
  let errorMsg = "";
  let loading = true;
  let roleFilter: "" | UserRole = "";

  async function load() {
    loading = true;
    errorMsg = "";
    try {
      rows = await fetchAdminUsers(roleFilter || undefined);
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Failed to load users";
    } finally {
      loading = false;
    }
  }

  onMount(load);
</script>

<section>
  <Breadcrumbs
    items={[
      { label: "Admin", href: PATH_ADMIN_HOME },
      { label: "User management" },
    ]}
  />
  <h1 class="gh-title" style="margin-top: 0; margin-bottom: 8px;">User management</h1>
  <p class="gh-subtitle" style="margin-bottom: 16px;">
    Filter by role. Open a row to view profile and role-specific data. Other administrators are read-only.
  </p>

  <div class="gh-toolbar-filters">
    <label class="gh-label" for="role-f" style="margin: 0;">Role</label>
    <select id="role-f" class="gh-input" bind:value={roleFilter} style="width: auto;" on:change={load}>
      <option value="">All roles</option>
      <option value="student">student</option>
      <option value="teacher">teacher</option>
      <option value="admin">admin</option>
    </select>
  </div>

  {#if errorMsg}
    <div class="gh-alert gh-alert-error">{errorMsg}</div>
  {/if}

  {#if loading}
    <p class="gh-muted">Loading…</p>
  {:else if rows.length === 0}
    <p class="gh-muted">No users match.</p>
  {:else}
    <div class="gh-table-wrap">
      <table class="gh-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Active</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {#each rows as u (u.id)}
            <tr
              class="gh-table-row-click"
              role="link"
              tabindex="0"
              aria-label="Open user {u.full_name}"
              on:click={(e) => tableRowClick(e, `/app/admin/users/${u.id}`)}
              on:keydown={(e) => tableRowKeydown(e, `/app/admin/users/${u.id}`)}
            >
              <td><strong>{u.full_name}</strong></td>
              <td class="gh-muted">{u.email}</td>
              <td class="gh-muted">{u.role}</td>
              <td>{u.is_active ? "yes" : "no"}</td>
              <td class="gh-muted">{formatDateTime(u.updated_at)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>
