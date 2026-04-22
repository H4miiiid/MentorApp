<script lang="ts">
  import { onMount } from "svelte";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import { PATH_TEACHER_HOME } from "$lib/paths";
  import {
    deleteDocument,
    downloadDocumentFile,
    fetchDocuments,
    unarchiveDocument,
    updateDocumentMeta,
    uploadDocument,
    type DocumentRead,
  } from "$lib/api";
  import { formatBytes, formatDateTime } from "$lib/format";

  let rows: DocumentRead[] = [];
  let errorMsg = "";
  let loading = true;
  let busyId: string | null = null;
  let includeArchived = false;

  let uploadFile: FileList | null = null;
  let uploadTitle = "";
  let uploadDescription = "";
  let uploadError = "";
  let uploading = false;

  let editingId: string | null = null;
  let editTitle = "";
  let editDescription = "";
  let editError = "";
  let editSaving = false;

  async function refresh() {
    loading = true;
    errorMsg = "";
    try {
      rows = await fetchDocuments({ includeArchived });
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Failed to load documents";
    } finally {
      loading = false;
    }
  }

  onMount(refresh);

  $: if (includeArchived !== undefined) {
    // re-fetch whenever the toggle flips; ignored on first mount since refresh() is already running
    void refresh();
  }

  function basename(path: string): string {
    const parts = path.replace(/\\/g, "/").split("/");
    return parts[parts.length - 1] || path;
  }

  async function onDownload(d: DocumentRead) {
    busyId = d.id;
    errorMsg = "";
    try {
      await downloadDocumentFile(d.id, basename(d.file_path) || d.title);
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Download failed";
    } finally {
      busyId = null;
    }
  }

  async function onArchive(d: DocumentRead) {
    if (!confirm(`Archive "${d.title}"? It will stay attached to any existing assignment but disappear from pickers.`)) return;
    busyId = d.id;
    errorMsg = "";
    try {
      await deleteDocument(d.id);
      await refresh();
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Archive failed";
    } finally {
      busyId = null;
    }
  }

  async function onUnarchive(d: DocumentRead) {
    busyId = d.id;
    errorMsg = "";
    try {
      await unarchiveDocument(d.id);
      await refresh();
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Restore failed";
    } finally {
      busyId = null;
    }
  }

  async function onUpload() {
    uploadError = "";
    const file = uploadFile?.[0];
    if (!file) {
      uploadError = "Choose a file to upload.";
      return;
    }
    uploading = true;
    try {
      await uploadDocument(file, {
        title: uploadTitle.trim() || file.name,
        description: uploadDescription.trim(),
      });
      uploadFile = null;
      uploadTitle = "";
      uploadDescription = "";
      // Reset the native file input (Svelte bind does not reset FileList by default).
      const input = document.getElementById("teacher-doc-upload-input") as HTMLInputElement | null;
      if (input) input.value = "";
      await refresh();
    } catch (e) {
      uploadError = e instanceof Error ? e.message : "Upload failed";
    } finally {
      uploading = false;
    }
  }

  function startEdit(d: DocumentRead) {
    editingId = d.id;
    editTitle = d.title;
    editDescription = d.description ?? "";
    editError = "";
  }

  function cancelEdit() {
    editingId = null;
    editTitle = "";
    editDescription = "";
    editError = "";
  }

  async function saveEdit() {
    if (!editingId) return;
    editError = "";
    editSaving = true;
    try {
      await updateDocumentMeta(editingId, {
        title: editTitle.trim(),
        description: editDescription,
      });
      editingId = null;
      await refresh();
    } catch (e) {
      editError = e instanceof Error ? e.message : "Save failed";
    } finally {
      editSaving = false;
    }
  }
</script>

<section>
  <Breadcrumbs
    items={[
      { label: "Teacher", href: PATH_TEACHER_HOME },
      { label: "Documents" },
    ]}
  />
  <h1 class="gh-title" style="margin-top: 0; margin-bottom: 8px;">Documents</h1>
  <p class="gh-subtitle" style="margin-bottom: 20px;">
    Your library of reference files and datasets. Attach them to assignments from the assignment page;
    students see the list on their submission page and any attached files appear inside the grading
    sandbox at <code>$ASSIGNMENT_DATA_DIR</code>.
  </p>

  <div class="gh-card" style="max-width: none; margin-bottom: 24px;">
    <h2 class="gh-title" style="font-size: 15px; margin-bottom: 12px;">Upload a document</h2>
    {#if uploadError}
      <div class="gh-alert gh-alert-error" style="margin-bottom: 12px;">{uploadError}</div>
    {/if}
    <div class="gh-field">
      <label class="gh-label" for="teacher-doc-upload-input">File</label>
      <input
        id="teacher-doc-upload-input"
        type="file"
        bind:files={uploadFile}
        class="gh-input"
      />
      <p class="gh-muted" style="margin: 6px 0 0; font-size: 12px;">
        Allowed formats depend on server configuration. Per-file size limit is configured via
        <code>APPV2_DOCUMENT_MAX_UPLOAD_MB</code>.
      </p>
    </div>
    <div class="gh-field">
      <label class="gh-label" for="teacher-doc-title">Title (optional)</label>
      <input
        id="teacher-doc-title"
        type="text"
        class="gh-input"
        bind:value={uploadTitle}
        placeholder="Defaults to the filename"
        maxlength="300"
      />
    </div>
    <div class="gh-field">
      <label class="gh-label" for="teacher-doc-desc">Description (optional)</label>
      <textarea
        id="teacher-doc-desc"
        class="gh-input"
        bind:value={uploadDescription}
        rows="2"
        placeholder="What is this file for? Students will see this."
      ></textarea>
    </div>
    <div class="gh-form-actions" style="margin: 8px 0 0;">
      <button
        type="button"
        class="gh-btn gh-btn-primary"
        disabled={uploading || !uploadFile || uploadFile.length === 0}
        on:click={onUpload}
      >
        {uploading ? "Uploading…" : "Upload"}
      </button>
    </div>
  </div>

  {#if errorMsg}
    <div class="gh-alert gh-alert-error">{errorMsg}</div>
  {/if}

  <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 10px;">
    <h2 class="gh-title" style="font-size: 15px; margin: 0;">Your library</h2>
    <label class="gh-muted" style="font-size: 13px; display: inline-flex; align-items: center; gap: 6px;">
      <input type="checkbox" bind:checked={includeArchived} />
      Show archived
    </label>
  </div>

  {#if loading}
    <p class="gh-muted">Loading…</p>
  {:else if rows.length === 0}
    <div class="gh-card" style="max-width: none;">
      <p class="gh-muted" style="margin: 0;">
        {includeArchived ? "No documents (archived or active)." : "No active documents. Upload one above."}
      </p>
    </div>
  {:else}
    <div class="gh-table-wrap">
      <table class="gh-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Type</th>
            <th>Size</th>
            <th>Filename</th>
            <th>Status</th>
            <th>Uploaded</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {#each rows as d (d.id)}
            {@const archived = !!d.archived_at}
            <tr>
              {#if editingId === d.id}
                <td colspan="7">
                  {#if editError}
                    <div class="gh-alert gh-alert-error" style="margin-bottom: 8px;">{editError}</div>
                  {/if}
                  <div class="gh-field" style="margin-bottom: 8px;">
                    <label class="gh-label" for="edit-title-{d.id}">Title</label>
                    <input
                      id="edit-title-{d.id}"
                      type="text"
                      class="gh-input"
                      bind:value={editTitle}
                      maxlength="300"
                    />
                  </div>
                  <div class="gh-field" style="margin-bottom: 8px;">
                    <label class="gh-label" for="edit-desc-{d.id}">Description</label>
                    <textarea
                      id="edit-desc-{d.id}"
                      class="gh-input"
                      bind:value={editDescription}
                      rows="2"
                    ></textarea>
                  </div>
                  <div class="gh-form-actions" style="margin: 0;">
                    <button
                      type="button"
                      class="gh-btn gh-btn-primary"
                      disabled={editSaving || !editTitle.trim()}
                      on:click={saveEdit}
                    >
                      {editSaving ? "Saving…" : "Save"}
                    </button>
                    <button type="button" class="gh-btn" disabled={editSaving} on:click={cancelEdit}>
                      Cancel
                    </button>
                  </div>
                </td>
              {:else}
                <td>
                  <strong>{d.title}</strong>
                  {#if d.description}
                    <div class="gh-muted" style="font-size: 12px; margin-top: 4px;">{d.description}</div>
                  {/if}
                </td>
                <td class="gh-muted">{d.file_type || "—"}</td>
                <td class="gh-muted">{formatBytes(d.file_size_bytes)}</td>
                <td class="gh-muted" style="max-width: 220px; overflow: hidden; text-overflow: ellipsis;">
                  {basename(d.file_path)}
                </td>
                <td>
                  {#if archived}
                    <span class="gh-muted" style="font-size: 12px;">Archived · {formatDateTime(d.archived_at)}</span>
                  {:else}
                    <span style="color: var(--gh-success, #3fb950); font-size: 12px;">Active</span>
                  {/if}
                </td>
                <td class="gh-muted">{formatDateTime(d.created_at)}</td>
                <td style="text-align: right; white-space: nowrap;">
                  <button
                    type="button"
                    class="gh-btn"
                    style="padding: 4px 10px; font-size: 12px; margin-right: 4px;"
                    disabled={busyId === d.id}
                    on:click={() => onDownload(d)}>Download</button
                  >
                  {#if !archived}
                    <button
                      type="button"
                      class="gh-btn"
                      style="padding: 4px 10px; font-size: 12px; margin-right: 4px;"
                      disabled={busyId === d.id || editingId !== null}
                      on:click={() => startEdit(d)}>Edit</button
                    >
                    <button
                      type="button"
                      class="gh-btn"
                      style="padding: 4px 10px; font-size: 12px; color: var(--gh-danger); border-color: rgba(248,81,73,0.35);"
                      disabled={busyId === d.id}
                      on:click={() => onArchive(d)}>Archive</button
                    >
                  {:else}
                    <button
                      type="button"
                      class="gh-btn"
                      style="padding: 4px 10px; font-size: 12px;"
                      disabled={busyId === d.id}
                      on:click={() => onUnarchive(d)}>Restore</button
                    >
                  {/if}
                </td>
              {/if}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>
