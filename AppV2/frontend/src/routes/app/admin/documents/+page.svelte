<script lang="ts">
  import { onMount } from "svelte";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import {
    deleteDocument,
    downloadDocumentFile,
    fetchDocuments,
    type DocumentRead,
  } from "$lib/api";
  import { formatBytes, formatDateTime } from "$lib/format";
  import { PATH_ADMIN_HOME } from "$lib/paths";

  let rows: DocumentRead[] = [];
  let errorMsg = "";
  let loading = true;
  let busyId: string | null = null;

  async function refresh() {
    loading = true;
    errorMsg = "";
    try {
      rows = await fetchDocuments();
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Failed to load documents";
    } finally {
      loading = false;
    }
  }

  onMount(refresh);

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

  async function onDelete(d: DocumentRead) {
    if (!confirm(`Delete “${d.title}”? This cannot be undone.`)) return;
    busyId = d.id;
    errorMsg = "";
    try {
      await deleteDocument(d.id);
      await refresh();
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Delete failed";
    } finally {
      busyId = null;
    }
  }
</script>

<section>
  <Breadcrumbs
    items={[
      { label: "Admin", href: PATH_ADMIN_HOME },
      { label: "Documents" },
    ]}
  />
  <h1 class="gh-title" style="margin-top: 0; margin-bottom: 8px;">Documents</h1>
  <p class="gh-subtitle" style="margin-bottom: 20px;">
    All uploaded documents (admin view). Download uses your session; delete removes the record.
  </p>

  {#if errorMsg}
    <div class="gh-alert gh-alert-error">{errorMsg}</div>
  {/if}

  {#if loading}
    <p class="gh-muted">Loading…</p>
  {:else if rows.length === 0}
    <div class="gh-card" style="max-width: none;">
      <p class="gh-muted" style="margin: 0;">No documents.</p>
    </div>
  {:else}
    <div class="gh-table-wrap">
      <table class="gh-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Type</th>
            <th>Size</th>
            <th>Stored path</th>
            <th>Assignment</th>
            <th>Uploaded</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {#each rows as d (d.id)}
            <tr>
              <td><strong>{d.title}</strong></td>
              <td class="gh-muted">{d.file_type || "—"}</td>
              <td class="gh-muted">{formatBytes(d.file_size_bytes)}</td>
              <td class="gh-muted" style="max-width: 200px; font-size: 12px;">{d.file_path}</td>
              <td class="gh-muted">{d.assignment_id ?? "—"}</td>
              <td class="gh-muted">{formatDateTime(d.created_at)}</td>
              <td style="text-align: right; white-space: nowrap;">
                <button
                  type="button"
                  class="gh-btn"
                  style="padding: 4px 10px; font-size: 12px;"
                  disabled={busyId === d.id}
                  on:click={() => onDownload(d)}>Download</button
                >
                <button
                  type="button"
                  class="gh-btn"
                  style="padding: 4px 10px; font-size: 12px;"
                  disabled={busyId === d.id}
                  on:click={() => onDelete(d)}>Delete</button
                >
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>
