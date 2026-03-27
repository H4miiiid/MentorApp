<script lang="ts">
  import { page } from "$app/stores";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import { formatDateTime } from "$lib/format";
  import { PATH_STUDENT_HOME } from "$lib/paths";

  $: me = $page.data.user;
</script>

<section>
  <Breadcrumbs
    items={[
      { label: "Student", href: PATH_STUDENT_HOME },
      { label: "Profile" },
    ]}
  />
  <h1 class="gh-title" style="margin-top: 0; margin-bottom: 8px;">Profile</h1>
  <p class="gh-subtitle" style="margin-bottom: 20px;">Your account (read-only for now).</p>

  {#if me}
    <div class="gh-card" style="max-width: 480px;">
      <dl class="gh-dl">
        <dt>Full name</dt>
        <dd>{me.full_name}</dd>
        <dt>Email</dt>
        <dd>{me.email}</dd>
        <dt>Role</dt>
        <dd>{me.role}</dd>
        <dt>Student ID</dt>
        <dd>{me.student_id_number || "—"}</dd>
        <dt>Active</dt>
        <dd>{me.is_active ? "Yes" : "No"}</dd>
        <dt>User ID</dt>
        <dd style="word-break: break-all;">{me.id}</dd>
        <dt>Created</dt>
        <dd>{formatDateTime(me.created_at)}</dd>
        <dt>Updated</dt>
        <dd>{formatDateTime(me.updated_at)}</dd>
      </dl>
    </div>
  {:else}
    <p class="gh-muted">Loading…</p>
  {/if}
</section>
