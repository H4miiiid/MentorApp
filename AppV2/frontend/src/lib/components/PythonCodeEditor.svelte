<script lang="ts">
  import { onMount } from "svelte";
  import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
  import { bracketMatching, indentUnit } from "@codemirror/language";
  import { python } from "@codemirror/lang-python";
  import { oneDark } from "@codemirror/theme-one-dark";
  import {
    EditorView,
    drawSelection,
    highlightActiveLine,
    keymap,
    lineNumbers,
    placeholder,
  } from "@codemirror/view";
  import { EditorState } from "@codemirror/state";

  /** Two-way bound source code. */
  export let value = "";
  export let minHeight = "220px";
  export let maxHeight = "480px";
  export let placeholderText = "# Your solution\ndef main():\n    pass";

  let host: HTMLDivElement;
  let view: EditorView | undefined;

  function extensions() {
    return [
      history(),
      drawSelection(),
      lineNumbers(),
      highlightActiveLine(),
      bracketMatching(),
      indentUnit.of("    "),
      keymap.of([...defaultKeymap, ...historyKeymap, indentWithTab]),
      python(),
      oneDark,
      placeholder(placeholderText),
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          value = update.state.doc.toString();
        }
      }),
      EditorView.theme({
        "&": { height: "100%", fontSize: "13px" },
        ".cm-scroller": {
          minHeight,
          maxHeight,
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
        },
        ".cm-content": { padding: "12px 14px" },
        ".cm-lineNumbers .cm-gutterElement": { minWidth: "2.2ch" },
      }),
    ];
  }

  onMount(() => {
    const state = EditorState.create({
      doc: value,
      extensions: extensions(),
    });
    view = new EditorView({ state, parent: host });
    return () => {
      view?.destroy();
      view = undefined;
    };
  });

  $: if (view && value !== view.state.doc.toString()) {
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: value },
    });
  }
</script>

<div class="gh-cm-wrap" bind:this={host}></div>
