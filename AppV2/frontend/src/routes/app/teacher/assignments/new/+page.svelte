<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import {
    createAssignment,
    fetchUsers,
    type UserRead,
  } from "$lib/api";
  import { PATH_TEACHER_HOME } from "$lib/paths";

  let title = "";
  let description = "";
  /** `datetime-local` value or empty */
  let dueLocal = "";
  let students: UserRead[] = [];
  let searchQuery = "";
  let selectedIds: string[] = [];
  let loadingStudents = true;
  let submitting = false;
  let errorMsg = "";

  $: me = $page.data.user;

  $: filteredStudents = students.filter((s) => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return true;
    return (
      s.full_name.toLowerCase().includes(q) ||
      s.email.toLowerCase().includes(q) ||
      (s.student_id_number && s.student_id_number.toLowerCase().includes(q))
    );
  });

  $: selectedCount = selectedIds.length;

  onMount(async () => {
    loadingStudents = true;
    errorMsg = "";
    try {
      const all = await fetchUsers();
      students = all.filter((u) => u.role === "student" && u.is_active);
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Failed to load students";
    } finally {
      loadingStudents = false;
    }
  });

  function selectAllFiltered() {
    const set = new Set(selectedIds);
    for (const s of filteredStudents) {
      set.add(s.id);
    }
    selectedIds = [...set];
  }

  function clearFiltered() {
    const remove = new Set(filteredStudents.map((s) => s.id));
    selectedIds = selectedIds.filter((id) => !remove.has(id));
  }

  function dueDateIso(): string | null {
    if (!dueLocal.trim()) return null;
    const d = new Date(dueLocal);
    if (Number.isNaN(d.getTime())) return null;
    return d.toISOString();
  }

  async function submit() {
    errorMsg = "";
    if (!me || me.role !== "teacher") {
      errorMsg = "You must be signed in as a teacher.";
      return;
    }
    const t = title.trim();
    if (t.length < 1) {
      errorMsg = "Title is required.";
      return;
    }
    submitting = true;
    try {
      const created = await createAssignment({
        title: t,
        description: description.trim(),
        teacher_id: me.id,
        due_date: dueDateIso(),
        student_ids: selectedIds,
      });
      await goto(`/app/teacher/assignments/${created.id}`);
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Could not create assignment";
    } finally {
      submitting = false;
    }
  }
</script>

<section>
  <Breadcrumbs
    items={[
      { label: "Teacher", href: PATH_TEACHER_HOME },
      { label: "Assignments", href: PATH_TEACHER_HOME },
      { label: "New assignment" },
    ]}
  />

  <h1 class="gh-title" style="margin-top: 0; margin-bottom: 8px;">Create assignment</h1>
  <p class="gh-subtitle" style="margin-bottom: 24px;">
    Add a title, optional due date, and choose which students are enrolled.
  </p>

  {#if errorMsg}
    <div class="gh-alert gh-alert-error">{errorMsg}</div>
  {/if}

  <form
    class="gh-card"
    style="max-width: 560px;"
    on:submit|preventDefault={submit}
  >
    <div class="gh-field">
      <label class="gh-label" for="as-title">Title</label>
      <input
        id="as-title"
        class="gh-input"
        type="text"
        bind:value={title}
        required
        maxlength="300"
        autocomplete="off"
      />
    </div>

    <div class="gh-field">
      <label class="gh-label" for="as-desc">Description</label>
      <textarea
        id="as-desc"
        class="gh-input"
        rows="5"
        bind:value={description}
        placeholder="Instructions, links, or context for students."
        style="resize: vertical; min-height: 100px;"
      ></textarea>
    </div>

    <div class="gh-field">
      <label class="gh-label" for="as-due">Due date (optional)</label>
      <input id="as-due" class="gh-input" type="datetime-local" bind:value={dueLocal} />
    </div>

    <div class="gh-field">
      <span class="gh-label">Students</span>
      {#if loadingStudents}
        <p class="gh-muted" style="margin: 0;">Loading students…</p>
      {:else if students.length === 0}
        <p class="gh-muted" style="margin: 0;">No student accounts are available yet.</p>
      {:else}
        <details class="gh-student-dropdown">
          <summary>
            Select students ({selectedCount} selected)
          </summary>
          <div class="gh-student-dropdown-tools">
            <input
              class="gh-input"
              type="search"
              placeholder="Filter by name, email, or student ID…"
              bind:value={searchQuery}
              aria-label="Filter students"
            />
            <button type="button" class="gh-btn" style="padding: 6px 10px; font-size: 12px;" on:click={selectAllFiltered}>
              Select all shown
            </button>
            <button type="button" class="gh-btn" style="padding: 6px 10px; font-size: 12px;" on:click={clearFiltered}>
              Clear shown
            </button>
          </div>
          <div class="gh-checkbox-list">
            {#each filteredStudents as s (s.id)}
              <div class="gh-checkbox-row">
                <input id="st-{s.id}" type="checkbox" value={s.id} bind:group={selectedIds} />
                <label for="st-{s.id}">
                  <strong>{s.full_name}</strong>
                  <span class="gh-muted" style="display: block; font-size: 12px;">{s.email}</span>
                  {#if s.student_id_number}
                    <span class="gh-muted" style="font-size: 12px;">ID: {s.student_id_number}</span>
                  {/if}
                </label>
              </div>
            {:else}
              <p class="gh-muted" style="margin: 0;">No students match your filter.</p>
            {/each}
          </div>
        </details>
      {/if}
    </div>

    <div class="gh-form-actions">
      <button type="submit" class="gh-btn gh-btn-primary" disabled={submitting || !me}>
        {submitting ? "Creating…" : "Create assignment"}
      </button>
      <a href={PATH_TEACHER_HOME} class="gh-link-muted">Cancel</a>
    </div>
  </form>
</section>
