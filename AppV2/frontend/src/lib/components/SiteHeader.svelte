<script lang="ts">
  export let showAdminLink = true;
</script>

<header class="gh-header">
  <div class="gh-header-inner">
    <a href="/" class="gh-logo">
      <img src="/logo.svg" alt="" width="32" height="32" />
      MentorApp
    </a>
    <nav style="display: flex; align-items: center; gap: 16px;">
      {#if showAdminLink}
        <a href="/admin/login" class="gh-link-muted">Admin</a>
      {/if}
      <a href="/auth" class="gh-btn" style="padding: 6px 12px; font-size: 13px;">Sign in</a>
    </nav>
  </div>
</header>
