<script lang="ts">
  import { goto, invalidate } from "$app/navigation";
  import { apiFetch, clearToken, fetchMe, setToken } from "$lib/api";
  import { SESSION_DEPENDENCY } from "$lib/session";

  let email = "";
  let password = "";
  let loading = false;
  let errorMsg = "";

  async function submit() {
    errorMsg = "";
    loading = true;
    clearToken();
    try {
      const res = await apiFetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        errorMsg = (data as { detail?: string }).detail ?? "Sign in failed";
        return;
      }
      setToken((data as { access_token: string }).access_token);
      const me = await fetchMe();
      if (me.role !== "admin") {
        clearToken();
        errorMsg = "This portal is for administrators only.";
        return;
      }
      await invalidate(SESSION_DEPENDENCY);
      await goto("/app");
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Something went wrong";
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>Admin sign in — MentorApp</title>
</svelte:head>

<div class="gh-page">
  <header class="gh-header">
    <div class="gh-header-inner">
      <a href="/" class="gh-logo">
        <img src="/logo.svg" alt="" width="32" height="32" />
        MentorApp
      </a>
      <a href="/auth" class="gh-link-muted" style="font-size: 13px;">User sign in</a>
    </div>
  </header>

  <main class="gh-main gh-center" style="padding-top: 24px;">
    <div class="gh-card gh-card-wide">
      <h1 class="gh-title">Admin</h1>
      <p class="gh-subtitle">Administrator sign-in. Student and teacher accounts use the main portal.</p>

      {#if errorMsg}
        <div class="gh-alert gh-alert-error">{errorMsg}</div>
      {/if}

      <form on:submit|preventDefault={submit}>
        <div class="gh-field">
          <label class="gh-label" for="a-email">Email</label>
          <input
            id="a-email"
            class="gh-input"
            type="email"
            bind:value={email}
            required
            autocomplete="username"
          />
        </div>
        <div class="gh-field">
          <label class="gh-label" for="a-password">Password</label>
          <input
            id="a-password"
            class="gh-input"
            type="password"
            bind:value={password}
            required
            autocomplete="current-password"
          />
        </div>
        <button type="submit" class="gh-btn gh-btn-primary gh-btn-block" disabled={loading}>
          {loading ? "Please wait…" : "Sign in as admin"}
        </button>
      </form>

      <p class="gh-muted" style="margin-top: 20px; text-align: center;">
        <a href="/">← Back to home</a>
      </p>
    </div>
  </main>
</div>
