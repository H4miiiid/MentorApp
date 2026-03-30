<script lang="ts">
  import { page } from "$app/stores";
  import { goto, invalidate } from "$app/navigation";
  import { clearToken } from "$lib/api";
  import { SESSION_DEPENDENCY } from "$lib/session";
  import { PATH_ADMIN_HOME } from "$lib/paths";

  $: path = $page.url.pathname;

  async function signOut() {
    clearToken();
    await invalidate(SESSION_DEPENDENCY);
    await goto("/admin/login");
  }
</script>

<div class="gh-page gh-page-app">
  <aside class="gh-sidebar" aria-label="Admin navigation">
    <a href={PATH_ADMIN_HOME} class="gh-sidebar-brand">
      <img src="/logo.svg" alt="" width="28" height="28" />
      MentorApp
    </a>
    <p class="gh-sidebar-context">Administration</p>
    <nav class="gh-sidebar-nav">
      <a
        href={PATH_ADMIN_HOME}
        class="gh-sidebar-link"
        class:gh-sidebar-link-active={path === PATH_ADMIN_HOME}>Overview</a
      >
      <a
        href="/app/admin/configuration"
        class="gh-sidebar-link"
        class:gh-sidebar-link-active={path.startsWith("/app/admin/configuration")}
        >Configuration</a
      >
      <a
        href="/app/admin/documents"
        class="gh-sidebar-link"
        class:gh-sidebar-link-active={path.startsWith("/app/admin/documents")}>Documents</a
      >
      <a
        href="/app/admin/monitoring"
        class="gh-sidebar-link"
        class:gh-sidebar-link-active={path.startsWith("/app/admin/monitoring")}>Monitoring</a
      >
      <a
        href="/app/admin/users"
        class="gh-sidebar-link"
        class:gh-sidebar-link-active={path.startsWith("/app/admin/users")}>User management</a
      >
    </nav>
    <div class="gh-sidebar-footer">
      <div class="gh-sidebar-user">{$page.data.user?.full_name ?? ""}</div>
      <button
        type="button"
        class="gh-btn gh-sidebar-signout"
        style="padding: 6px 12px; font-size: 13px;"
        on:click={signOut}>Sign out</button
      >
    </div>
  </aside>
  <div class="gh-panel">
    <div class="gh-panel-body">
      <slot />
    </div>
  </div>
</div>
