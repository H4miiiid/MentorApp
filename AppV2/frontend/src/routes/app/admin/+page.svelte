<script lang="ts">
  import { page } from "$app/stores";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import { PATH_ADMIN_HOME } from "$lib/paths";

  $: me = $page.data.user;
</script>

<section>
  <Breadcrumbs items={[{ label: "Admin", href: PATH_ADMIN_HOME }, { label: "Overview" }]} />
  <h1 class="gh-title" style="margin-top: 0; margin-bottom: 8px;">Admin overview</h1>
  <p class="gh-subtitle" style="margin-bottom: 20px;">
    Use the sidebar for configuration, documents, live backend logs, and user management.
  </p>
  {#if me}
    <div class="gh-card" style="max-width: none;">
      <p style="margin: 0;">
        Signed in as <strong>{me.full_name}</strong>
        <span class="gh-muted">({me.email})</span>
      </p>
      <p class="gh-muted" style="margin: 12px 0 0;">Role: <strong>{me.role}</strong></p>
    </div>
  {/if}
</section>
