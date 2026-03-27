<script lang="ts">
  import { page } from "$app/stores";
  import { goto, invalidate } from "$app/navigation";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import { clearToken } from "$lib/api";
  import { SESSION_DEPENDENCY } from "$lib/session";
  import { PATH_ADMIN_HOME } from "$lib/paths";

  $: me = $page.data.user;

  async function signOut() {
    clearToken();
    await invalidate(SESSION_DEPENDENCY);
    goto(me?.role === "admin" ? "/admin/login" : "/auth");
  }
</script>

<svelte:head>
  <title>App — MentorApp</title>
</svelte:head>

{#if me}
  <div class="gh-page gh-page-app">
    <aside class="gh-sidebar" aria-label="Admin navigation">
      <a href="/" class="gh-sidebar-brand">
        <img src="/logo.svg" alt="" width="28" height="28" />
        MentorApp
      </a>
      <p class="gh-sidebar-context">Admin</p>
      <nav class="gh-sidebar-nav">
        <a href={PATH_ADMIN_HOME} class="gh-sidebar-link gh-sidebar-link-active">Overview</a>
      </nav>
      <div class="gh-sidebar-footer">
        <div class="gh-sidebar-user">{me.full_name}</div>
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
        <Breadcrumbs items={[{ label: "Admin", href: PATH_ADMIN_HOME }, { label: "Overview" }]} />
        <h1 class="gh-title" style="margin-top: 0; margin-bottom: 8px;">Signed in</h1>
        <p class="gh-subtitle" style="margin-bottom: 16px;">
          You are connected as <strong>{me.full_name}</strong> ({me.email}).
        </p>
        <p class="gh-muted" style="margin: 0;">
          Role: <strong style="color: var(--gh-text);">{me.role}</strong>
        </p>
        <p class="gh-muted" style="margin-top: 16px;">
          Admin tools can be expanded here; you are signed in with an administrator account.
        </p>
      </div>
    </div>
  </div>
{:else}
  <div class="gh-page">
    <main class="gh-main"><p class="gh-muted">Loading…</p></main>
  </div>
{/if}
