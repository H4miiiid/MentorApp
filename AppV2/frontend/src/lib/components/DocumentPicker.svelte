<script lang="ts">
  import type { DocumentRead } from "$lib/api";
  import { formatBytes } from "$lib/format";

  export let documents: DocumentRead[] = [];
  export let selectedIds: string[] = [];
  export let idPrefix: string = "doc";
  export let summaryLabel: string = "Select documents";
  export let emptyLabel: string = "Your document library is empty.";
  export let placeholder: string = "Filter by title, description, or file type…";
  /** Start with the panel open. Defaults to false so the picker is compact. */
  export let open: boolean = false;

  let query = "";

  $: filtered = documents.filter((d) => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    const hay = [d.title, d.description, d.file_type, d.file_path]
      .filter(Boolean)
      .map((s) => s.toLowerCase());
    return hay.some((s) => s.includes(q));
  });

  $: selectedCount = selectedIds.length;

  function selectAllFiltered() {
    const next = new Set(selectedIds);
    for (const d of filtered) next.add(d.id);
    selectedIds = [...next];
  }

  function clearFiltered() {
    const remove = new Set(filtered.map((d) => d.id));
    selectedIds = selectedIds.filter((id) => !remove.has(id));
  }
</script>

{#if documents.length === 0}
  <p class="gh-muted" style="margin: 0;">{emptyLabel}</p>
{:else}
  <details class="gh-student-dropdown" {open}>
    <summary>
      {summaryLabel} ({selectedCount} selected)
    </summary>
    <div class="gh-student-dropdown-tools">
      <input
        class="gh-input"
        type="search"
        {placeholder}
        bind:value={query}
        aria-label="Filter documents"
      />
      <button
        type="button"
        class="gh-btn"
        style="padding: 6px 10px; font-size: 12px;"
        on:click={selectAllFiltered}
      >
        Select all shown
      </button>
      <button
        type="button"
        class="gh-btn"
        style="padding: 6px 10px; font-size: 12px;"
        on:click={clearFiltered}
      >
        Clear shown
      </button>
    </div>
    <div class="gh-checkbox-list">
      {#each filtered as d (d.id)}
        <div class="gh-checkbox-row">
          <input
            id="{idPrefix}-{d.id}"
            type="checkbox"
            value={d.id}
            bind:group={selectedIds}
          />
          <label for="{idPrefix}-{d.id}">
            <strong>{d.title}</strong>
            <span class="gh-muted" style="display: block; font-size: 12px;">
              {formatBytes(d.file_size_bytes)} · {d.file_type || "file"}
            </span>
            {#if d.description}
              <span class="gh-muted" style="display: block; font-size: 12px;">
                {d.description}
              </span>
            {/if}
          </label>
        </div>
      {:else}
        <p class="gh-muted" style="margin: 0;">No documents match your filter.</p>
      {/each}
    </div>
  </details>
{/if}
