<script lang="ts">
  export type Crumb = { label: string; href?: string };

  /** Last item is current page (no link unless you pass href for all). */
  export let items: Crumb[];
</script>

<nav class="gh-breadcrumbs" aria-label="Breadcrumb">
  <ol class="gh-breadcrumbs-list">
    {#each items as c, i}
      <li class="gh-breadcrumbs-item">
        {#if c.href && i < items.length - 1}
          <a href={c.href}>{c.label}</a>
        {:else}
          <span class="gh-breadcrumbs-current" aria-current={i === items.length - 1 ? "page" : undefined}
            >{c.label}</span
          >
        {/if}
      </li>
    {/each}
  </ol>
</nav>
