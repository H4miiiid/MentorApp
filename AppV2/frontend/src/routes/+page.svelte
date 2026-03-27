<svelte:head>
  <title>MentorApp — Learning platform</title>
  <meta
    name="description"
    content="Assignments, submissions, and documents for students and teachers."
  />
</svelte:head>

<div class="gh-page">
  <header class="gh-header">
    <div class="gh-header-inner">
      <span class="gh-logo" style="cursor: default;">
        <img src="/logo.svg" alt="" width="32" height="32" />
        MentorApp
      </span>
      <nav style="display: flex; align-items: center; gap: 16px;">
        <a href="/admin/login" class="gh-link-muted" style="font-size: 13px;">Admin</a>
        <a href="/auth" class="gh-btn gh-btn-primary" style="padding: 8px 16px;">Enter</a>
      </nav>
    </div>
  </header>

  <main class="gh-main">
    <section class="gh-hero">
      <h1>Teach and learn in one place</h1>
      <p>
        MentorApp helps students submit work, teachers manage assignments, and everyone stay
        organized with a simple document workflow—built for clarity, not clutter.
      </p>
      <a href="/auth" class="gh-btn gh-btn-primary" style="padding: 10px 22px; font-size: 15px;">
        Enter
      </a>
    </section>

    <div
      style="display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); margin-top: 24px;"
    >
      <div class="gh-card" style="max-width: none;">
        <h2 class="gh-title" style="font-size: 16px; margin-bottom: 8px;">For students</h2>
        <p class="gh-muted" style="margin: 0;">
          View assignments, upload submissions, and track your progress alongside your class.
        </p>
      </div>
      <div class="gh-card" style="max-width: none;">
        <h2 class="gh-title" style="font-size: 16px; margin-bottom: 8px;">For teachers</h2>
        <p class="gh-muted" style="margin: 0;">
          Create assignments, collect submissions, and keep course materials in one place.
        </p>
      </div>
      <div class="gh-card" style="max-width: none;">
        <h2 class="gh-title" style="font-size: 16px; margin-bottom: 8px;">Secure access</h2>
        <p class="gh-muted" style="margin: 0;">
          Role-based accounts keep admin tools separate from everyday teaching and learning.
        </p>
      </div>
    </div>
  </main>

  <footer class="gh-footer">MentorApp · First iteration</footer>
</div>
