<script lang="ts">
  import { page } from "$app/stores";
  import { goto, invalidate } from "$app/navigation";
  import { clearToken } from "$lib/api";
  import { SESSION_DEPENDENCY } from "$lib/session";
  import { PATH_STUDENT_HOME } from "$lib/paths";

  $: me = $page.data.user;
  $: path = $page.url.pathname;
  $: assignmentsActive =
    path.startsWith("/app/student/assignments") && !path.includes("/submissions");
  $: submissionsActive = path.startsWith("/app/student/submissions");
  $: profileActive = path.startsWith("/app/student/profile");

  async function signOut() {
    clearToken();
    await invalidate(SESSION_DEPENDENCY);
    goto("/auth");
  }
</script>

<svelte:head>
  <title>Student — MentorApp</title>
</svelte:head>

{#if me}
  <div class="gh-page gh-page-app">
    <aside class="gh-sidebar" aria-label="Student navigation">
      <a href="/" class="gh-sidebar-brand">
        <img src="/logo.svg" alt="" width="28" height="28" />
        MentorApp
      </a>
      <p class="gh-sidebar-context">Student</p>
      <nav class="gh-sidebar-nav">
        <a
          href={PATH_STUDENT_HOME}
          class="gh-sidebar-link"
          class:gh-sidebar-link-active={assignmentsActive}>Assignments</a
        >
        <a
          href="/app/student/submissions"
          class="gh-sidebar-link"
          class:gh-sidebar-link-active={submissionsActive}>Submissions</a
        >
        <a
          href="/app/student/profile"
          class="gh-sidebar-link"
          class:gh-sidebar-link-active={profileActive}>Profile</a
        >
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
        <slot />
      </div>
    </div>
  </div>
{:else}
  <div class="gh-page">
    <main class="gh-main"><p class="gh-muted">Loading…</p></main>
  </div>
{/if}
