<script lang="ts">
  import type { SubmissionStatus } from "$lib/api";

  export let status: SubmissionStatus;
</script>

<span class="gh-status gh-status-{status}">{status}</span>
