<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import SubmissionStatusBadge from "$lib/components/SubmissionStatusBadge.svelte";
  import {
    deleteUserAccount,
    fetchAdminUserInsights,
    patchUser,
    type AdminUserInsightsResponse,
    type UserRole,
  } from "$lib/api";
  import { formatDateTime, formatSubmissionGrade } from "$lib/format";
  import { PATH_ADMIN_HOME } from "$lib/paths";
  import { tableRowClick, tableRowKeydown } from "$lib/tableRowNav";

  let insights: AdminUserInsightsResponse | null = null;
  let errorMsg = "";
  let loading = true;
  let saving = false;
  let formError = "";

  let email = "";
  let fullName = "";
  let studentIdNumber = "";
  let role: UserRole = "student";
  let isActive = true;
  let newPassword = "";

  $: userId = $page.params.userId ?? "";
  $: u = insights?.user;
  $: me = $page.data.user;
  /** Other admins are read-only; you may edit your own admin row. */
  $: isReadOnlyAdmin = u?.role === "admin" && u.id !== me?.id;
  $: isSelf = me?.id === userId;

  async function load() {
    if (!userId) {
      loading = false;
      return;
    }
    loading = true;
    errorMsg = "";
    try {
      insights = await fetchAdminUserInsights(userId);
      const x = insights.user;
      email = x.email;
      fullName = x.full_name;
      studentIdNumber = x.student_id_number;
      role = x.role;
      isActive = x.is_active;
      newPassword = "";
      formError = "";
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Failed to load";
      insights = null;
    } finally {
      loading = false;
    }
  }

  $: if (userId) void load();

  async function save() {
    if (!userId || isReadOnlyAdmin) return;
    formError = "";
    saving = true;
    try {
      const body: Parameters<typeof patchUser>[1] = {
        email: email.trim(),
        full_name: fullName.trim(),
        role,
        student_id_number: studentIdNumber.trim(),
        is_active: isActive,
      };
      if (newPassword.trim().length >= 6) {
        body.password = newPassword.trim();
      }
      await patchUser(userId, body);
      newPassword = "";
      await load();
    } catch (e) {
      formError = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }

  async function remove() {
    if (!userId || isReadOnlyAdmin) return;
    if (!confirm("Delete this user and related data? This cannot be undone.")) return;
    try {
      await deleteUserAccount(userId);
      await goto("/app/admin/users");
    } catch (e) {
      formError = e instanceof Error ? e.message : "Delete failed";
    }
  }
</script>

<section>
  <Breadcrumbs
    items={[
      { label: "Admin", href: PATH_ADMIN_HOME },
      { label: "Users", href: "/app/admin/users" },
      { label: u?.full_name ?? "…" },
    ]}
  />

  {#if errorMsg}
    <div class="gh-alert gh-alert-error">{errorMsg}</div>
  {/if}

  {#if loading}
    <p class="gh-muted">Loading…</p>
  {:else if insights && u}
    <h1 class="gh-title" style="margin-top: 0; margin-bottom: 8px;">{u.full_name}</h1>
    <p class="gh-muted" style="margin-bottom: 20px;">
      <code>{u.id}</code>
    </p>

    <div class="gh-card" style="max-width: none; margin-bottom: 20px;">
      <h2 class="gh-title" style="font-size: 16px; margin-bottom: 12px;">Profile</h2>
      <dl class="gh-dl">
        <dt>Email</dt>
        <dd>{u.email}</dd>
        <dt>Role</dt>
        <dd>{u.role}</dd>
        <dt>Student ID</dt>
        <dd>{u.student_id_number || "—"}</dd>
        <dt>Active</dt>
        <dd>{u.is_active ? "yes" : "no"}</dd>
        <dt>Created</dt>
        <dd>{formatDateTime(u.created_at)}</dd>
        <dt>Updated</dt>
        <dd>{formatDateTime(u.updated_at)}</dd>
      </dl>
    </div>

    {#if isReadOnlyAdmin}
      <div class="gh-alert gh-alert-error" style="margin-bottom: 16px;">
        Administrator accounts are read-only in this panel (other admins cannot be edited or deleted).
      </div>
    {:else}
      <div class="gh-card" style="max-width: none; margin-bottom: 20px;">
        <h2 class="gh-title" style="font-size: 16px; margin-bottom: 12px;">Edit user</h2>
        {#if formError}
          <div class="gh-alert gh-alert-error">{formError}</div>
        {/if}
        <div class="gh-field">
          <label class="gh-label" for="em">Email</label>
          <input id="em" class="gh-input" type="email" bind:value={email} disabled={saving} />
        </div>
        <div class="gh-field">
          <label class="gh-label" for="fn">Full name</label>
          <input id="fn" class="gh-input" type="text" bind:value={fullName} disabled={saving} />
        </div>
        <div class="gh-field">
          <label class="gh-label" for="ro">Role</label>
          <select id="ro" class="gh-input" bind:value={role} disabled={saving}>
            <option value="student">student</option>
            <option value="teacher">teacher</option>
            <option value="admin">admin</option>
          </select>
        </div>
        <div class="gh-field">
          <label class="gh-label" for="sid">Student ID number</label>
          <input id="sid" class="gh-input" type="text" bind:value={studentIdNumber} disabled={saving} />
        </div>
        <div class="gh-field">
          <label class="gh-label" for="act">Active</label>
          <input id="act" type="checkbox" bind:checked={isActive} disabled={saving} />
        </div>
        <div class="gh-field">
          <label class="gh-label" for="pw">New password (optional)</label>
          <input
            id="pw"
            class="gh-input"
            type="password"
            autocomplete="new-password"
            placeholder="Leave blank to keep current"
            bind:value={newPassword}
            disabled={saving}
          />
        </div>
        <div class="gh-form-actions">
          <button type="button" class="gh-btn gh-btn-primary" disabled={saving} on:click={save}>
            {saving ? "Saving…" : "Save"}
          </button>
          {#if !isSelf}
            <button type="button" class="gh-btn" disabled={saving} on:click={remove}>Delete user</button>
          {/if}
        </div>
      </div>
    {/if}

    {#if insights.teacher_assignments && insights.teacher_assignments.length > 0}
      <h2 class="gh-title" style="font-size: 16px; margin-bottom: 12px;">Created assignments</h2>
      <div class="gh-table-wrap" style="margin-bottom: 24px;">
        <table class="gh-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Due</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {#each insights.teacher_assignments as a (a.id)}
              <tr>
                <td><strong>{a.title}</strong></td>
                <td class="gh-muted">{formatDateTime(a.due_date)}</td>
                <td class="gh-muted">{formatDateTime(a.updated_at)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}

    {#if insights.student_enrollments && insights.student_enrollments.length > 0}
      <h2 class="gh-title" style="font-size: 16px; margin-bottom: 12px;">Assigned assignments</h2>
      <div class="gh-table-wrap" style="margin-bottom: 24px;">
        <table class="gh-table">
          <thead>
            <tr>
              <th>Assignment</th>
              <th>Assigned at</th>
            </tr>
          </thead>
          <tbody>
            {#each insights.student_enrollments as row (row.assignment.id + row.assigned_at)}
              <tr>
                <td><strong>{row.assignment.title}</strong></td>
                <td class="gh-muted">{formatDateTime(row.assigned_at)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}

    {#if insights.student_submissions && insights.student_submissions.length > 0}
      <h2 class="gh-title" style="font-size: 16px; margin-bottom: 12px;">Submissions</h2>
      <div class="gh-table-wrap">
        <table class="gh-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Grade</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {#each insights.student_submissions as s (s.id)}
              <tr
                class="gh-table-row-click"
                role="link"
                tabindex="0"
                aria-label="Open submission"
                on:click={(e) => tableRowClick(e, `/app/admin/submissions/${s.id}`)}
                on:keydown={(e) => tableRowKeydown(e, `/app/admin/submissions/${s.id}`)}
              >
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
