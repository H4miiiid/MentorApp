<script lang="ts">
  export let diff = "";

  $: lines = (diff || "").split("\n");

  function lineClass(line: string): string {
    if (line.startsWith("@@")) return "hunk";
    if (line.startsWith("+++ ") || line.startsWith("--- ")) return "file";
    if (line.startsWith("+")) return "add";
    if (line.startsWith("-")) return "remove";
    return "context";
  }
</script>

<div class="gh-code-view-shell">
  <div class="gh-code-editor-toolbar">Unified diff</div>
  {#if !(diff || "").trim()}
    <pre class="gh-code-block gh-code-block-python">No diff available.</pre>
  {:else}
    <pre class="gh-code-block gh-diff-block">{#each lines as line}<span class={lineClass(line)}>{line}</span>
{/each}</pre>
  {/if}
</div>

<style>
  .gh-diff-block {
    line-height: 1.45;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .gh-diff-block :global(span) {
    display: block;
  }

  .file {
    color: #6e7781;
    font-weight: 600;
  }

  .hunk {
    color: #6f42c1;
    background: #f6f8fa;
  }

  .add {
    color: #1a7f37;
    background: #dafbe1;
  }

  .remove {
    color: #cf222e;
    background: #ffebe9;
  }

  .context {
    color: inherit;
  }
</style>