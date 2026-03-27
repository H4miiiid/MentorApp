<script lang="ts">
  import { goto, invalidate } from "$app/navigation";
  import SiteHeader from "$lib/components/SiteHeader.svelte";
  import { apiFetch, clearToken, fetchMe, setToken } from "$lib/api";
  import { SESSION_DEPENDENCY } from "$lib/session";

  type Tab = "signin" | "signup";
  let tab: Tab = "signin";

  let email = "";
  let password = "";
  let fullName = "";
  let role: "student" | "teacher" = "student";
  let studentIdNumber = "";

  let loading = false;
  let errorMsg = "";

  /** Store JWT and send user to /app (or block admins on this route). */
  async function applySessionAndGoHome(accessToken: string): Promise<void> {
    setToken(accessToken);
    const me = await fetchMe();
    if (me.role === "admin") {
      clearToken();
      errorMsg = "Administrator accounts must sign in via the admin portal (/admin/login).";
      return;
    }
    await invalidate(SESSION_DEPENDENCY);
    const dest =
      me.role === "teacher"
        ? "/app/teacher/assignments"
        : me.role === "student"
          ? "/app/student/assignments"
          : "/app";
    await goto(dest);
  }

  async function signIn() {
    errorMsg = "";
    loading = true;
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
      await applySessionAndGoHome((data as { access_token: string }).access_token);
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Something went wrong";
    } finally {
      loading = false;
    }
  }

  async function signUp() {
    errorMsg = "";
    loading = true;
    try {
      const res = await apiFetch("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: email.trim(),
          full_name: fullName.trim(),
          password,
          role,
          student_id_number: studentIdNumber.trim(),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        errorMsg =
          typeof (data as { detail?: unknown }).detail === "string"
            ? (data as { detail: string }).detail
            : "Registration failed";
        return;
      }
      const loginRes = await apiFetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const loginData = await loginRes.json().catch(() => ({}));
      if (!loginRes.ok) {
        errorMsg =
          (loginData as { detail?: string }).detail ??
          "Account created but automatic sign-in failed. Use Sign in with your email and password.";
        return;
      }
      await applySessionAndGoHome((loginData as { access_token: string }).access_token);
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Something went wrong";
    } finally {
      loading = false;
    }
  }

  function submit() {
    if (tab === "signin") signIn();
    else signUp();
  }
</script>

<svelte:head>
  <title>Sign in — MentorApp</title>
</svelte:head>

<div class="gh-page">
  <SiteHeader showAdminLink={true} />

  <main class="gh-main gh-center" style="padding-top: 24px;">
    <div class="gh-card gh-card-wide">
      <h1 class="gh-title">Welcome</h1>
      <p class="gh-subtitle">Sign in or create a student or teacher account.</p>

      <div class="gh-tabs">
        <button
          type="button"
          class="gh-tab"
          class:gh-tab-active={tab === "signin"}
          on:click={() => {
            tab = "signin";
            errorMsg = "";
          }}>Sign in</button
        >
        <button
          type="button"
          class="gh-tab"
          class:gh-tab-active={tab === "signup"}
          on:click={() => {
            tab = "signup";
            errorMsg = "";
          }}>Sign up</button
        >
      </div>

      {#if errorMsg}
        <div class="gh-alert gh-alert-error">{errorMsg}</div>
      {/if}

      <form
        on:submit|preventDefault={submit}
        autocomplete={tab === "signup" ? "on" : "on"}
      >
        {#if tab === "signup"}
          <div class="gh-field">
            <label class="gh-label" for="fullName">Full name</label>
            <input
              id="fullName"
              class="gh-input"
              type="text"
              bind:value={fullName}
              required
              minlength="2"
              maxlength="200"
            />
          </div>
          <div class="gh-field">
            <label class="gh-label" for="role">Role</label>
            <select id="role" class="gh-select" bind:value={role}>
              <option value="student">Student</option>
              <option value="teacher">Teacher</option>
            </select>
          </div>
          <div class="gh-field">
            <label class="gh-label" for="sid">Student ID (optional)</label>
            <input
              id="sid"
              class="gh-input"
              type="text"
              bind:value={studentIdNumber}
              maxlength="64"
            />
          </div>
        {/if}

        <div class="gh-field">
          <label class="gh-label" for="email">Email</label>
          <input
            id="email"
            class="gh-input"
            type="email"
            bind:value={email}
            required
            autocomplete="email"
          />
        </div>
        <div class="gh-field">
          <label class="gh-label" for="password">Password</label>
          <input
            id="password"
            class="gh-input"
            type="password"
            bind:value={password}
            required
            minlength={tab === "signup" ? 6 : 1}
            autocomplete={tab === "signup" ? "new-password" : "current-password"}
          />
        </div>

        <button type="submit" class="gh-btn gh-btn-primary gh-btn-block" disabled={loading}>
          {loading ? "Please wait…" : tab === "signin" ? "Sign in" : "Create account"}
        </button>
      </form>

      <p class="gh-muted" style="margin-top: 20px; text-align: center;">
        <a href="/">← Back to home</a>
      </p>
    </div>
  </main>
</div>
