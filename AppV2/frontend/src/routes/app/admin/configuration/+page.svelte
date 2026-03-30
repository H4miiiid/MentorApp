<script lang="ts">
  import { onMount } from "svelte";
  import Breadcrumbs from "$lib/components/Breadcrumbs.svelte";
  import {
    fetchAdminConfig,
    fetchGradingModels,
    fetchGradingStatus,
    createGradingModel,
    activateGradingModel,
    deleteGradingModel,
    type AdminConfigResponse,
    type GradingModelRead,
    type GradingStatusResponse,
  } from "$lib/api";
  import { PATH_ADMIN_HOME } from "$lib/paths";

  let cfg: AdminConfigResponse | null = null;
  let status: GradingStatusResponse | null = null;
  let models: GradingModelRead[] = [];
  let errorMsg = "";
  let loading = true;

  let newName = "";
  let newGguf = "";
  let newOpenai = "";
  let newCtx = 8192;
  let busy = false;

  async function load() {
    loading = true;
    errorMsg = "";
    try {
      [cfg, status, models] = await Promise.all([
        fetchAdminConfig(),
        fetchGradingStatus(),
        fetchGradingModels(),
      ]);
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Failed to load";
    } finally {
      loading = false;
    }
  }

  onMount(load);

  async function onActivate(id: string) {
    busy = true;
    errorMsg = "";
    try {
      await activateGradingModel(id);
      await load();
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Activate failed";
    } finally {
      busy = false;
    }
  }

  async function onDelete(id: string) {
    if (!confirm("Delete this grading model catalog entry?")) return;
    busy = true;
    errorMsg = "";
    try {
      await deleteGradingModel(id);
      await load();
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Delete failed";
    } finally {
      busy = false;
    }
  }

  async function onCreate(e: Event) {
    e.preventDefault();
    if (!newName.trim() || !newGguf.trim() || !newOpenai.trim()) {
      errorMsg = "Fill display name, GGUF filename, and OpenAI model name.";
      return;
    }
    busy = true;
    errorMsg = "";
    try {
      await createGradingModel({
        display_name: newName,
        gguf_filename: newGguf,
        openai_model_name: newOpenai,
        n_ctx: newCtx,
      });
      newName = "";
      newGguf = "";
      newOpenai = "";
      newCtx = 8192;
      await load();
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : "Create failed";
    } finally {
      busy = false;
    }
  }
</script>

<section>
  <Breadcrumbs
    items={[
      { label: "Admin", href: PATH_ADMIN_HOME },
      { label: "Configuration" },
    ]}
  />
  <h1 class="gh-title" style="margin-top: 0; margin-bottom: 8px;">Configuration</h1>
  <p class="gh-subtitle" style="margin-bottom: 20px;">
    Backend settings and grading model catalog. Llama must serve the GGUF file that matches your deployment;
    restart the llama container after changing files on disk.
  </p>

  {#if errorMsg}
    <div class="gh-alert gh-alert-error">{errorMsg}</div>
  {/if}
  {#if loading}
    <p class="gh-muted">Loading…</p>
  {:else if cfg}
    <div class="gh-card" style="max-width: none; margin-bottom: 20px;">
      <h2 class="gh-title" style="font-size: 18px; margin-top: 0;">Environment snapshot</h2>
      <dl class="gh-dl">
        <dt>Backend version</dt>
        <dd>{cfg.backend_version}</dd>
        <dt>Database path</dt>
        <dd><code>{cfg.database_path}</code></dd>
        <dt>Storage directory</dt>
        <dd><code>{cfg.storage_dir}</code></dd>
        <dt>Grading worker</dt>
        <dd>{cfg.grading_worker_enabled ? "enabled" : "disabled"}</dd>
        <dt>Grading backend</dt>
        <dd><code>{cfg.grading_backend}</code></dd>
        <dt>Grading poll interval (s)</dt>
        <dd>{cfg.grading_poll_interval_seconds}</dd>
        <dt>Mock grading sleep (s)</dt>
        <dd>{cfg.grading_mock_sleep_seconds}</dd>
        <dt>Grading max attempts (LangGraph)</dt>
        <dd>{cfg.grading_max_attempts}</dd>
        <dt>JWT expiry (minutes)</dt>
        <dd>{cfg.jwt_expire_minutes}</dd>
      </dl>
    </div>

    {#if status}
      <div class="gh-card" style="max-width: none; margin-bottom: 20px;">
        <h2 class="gh-title" style="font-size: 18px; margin-top: 0;">Grading / llama.cpp</h2>
        <dl class="gh-dl">
          <dt>Llama HTTP health</dt>
          <dd>
            <span
              class="gh-monitoring-pill"
              class:gh-monitoring-pill-live={status.llama_health_ok}
              class:gh-monitoring-pill-error={!status.llama_health_ok}
            >
              {status.llama_health_ok ? "reachable" : "unreachable"}
            </span>
            <code style="margin-left: 8px;">{status.llama_health_url}</code>
          </dd>
          <dt>LLAMA_SERVER_URL</dt>
          <dd><code>{status.llama_server_url}</code></dd>
          <dt>Compose GGUF hint</dt>
          <dd><code>{status.compose_gguf_hint}</code></dd>
          <dt>Active catalog model</dt>
          <dd>
            {#if status.active_model}
              <strong>{status.active_model.display_name}</strong>
              — OpenAI name <code>{status.active_model.openai_model_name}</code>,
              GGUF file <code>{status.active_model.gguf_filename}</code>
            {:else}
              <span class="gh-muted">None</span>
            {/if}
          </dd>
        </dl>
        <p class="gh-muted" style="margin-bottom: 0; font-size: 13px;">{status.note}</p>
      </div>
    {/if}

    <div class="gh-card" style="max-width: none;">
      <h2 class="gh-title" style="font-size: 18px; margin-top: 0;">Grading model catalog</h2>
      <p class="gh-muted" style="margin-top: 0;">
        The <strong>active</strong> row sets the OpenAI <code>model</code> string sent to llama-server for SFT steps.
        Keep <code>gguf_filename</code> aligned with the file on disk and the llama sidecar <code>-m</code> flag.
      </p>

      <div style="overflow-x: auto;">
        <table class="gh-table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr>
              <th style="text-align: left; padding: 8px;">Name</th>
              <th style="text-align: left; padding: 8px;">GGUF file</th>
              <th style="text-align: left; padding: 8px;">OpenAI model id</th>
              <th style="text-align: left; padding: 8px;">Ctx</th>
              <th style="text-align: left; padding: 8px;">Active</th>
              <th style="text-align: left; padding: 8px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each models as m}
              <tr>
                <td style="padding: 8px; border-top: 1px solid var(--gh-border);">{m.display_name}</td>
                <td style="padding: 8px; border-top: 1px solid var(--gh-border);"><code>{m.gguf_filename}</code></td>
                <td style="padding: 8px; border-top: 1px solid var(--gh-border);"><code>{m.openai_model_name}</code></td>
                <td style="padding: 8px; border-top: 1px solid var(--gh-border);">{m.n_ctx}</td>
                <td style="padding: 8px; border-top: 1px solid var(--gh-border);">{m.is_active ? "yes" : ""}</td>
                <td style="padding: 8px; border-top: 1px solid var(--gh-border); white-space: nowrap;">
                  {#if !m.is_active}
                    <button
                      type="button"
                      class="gh-btn gh-btn-sm gh-btn-primary"
                      disabled={busy}
                      on:click={() => onActivate(m.id)}>Activate</button
                    >
                  {/if}
                  {#if !m.is_active}
                    <button type="button" class="gh-btn gh-btn-sm" disabled={busy} on:click={() => onDelete(m.id)}
                      >Delete</button
                    >
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <form on:submit={onCreate} style="margin-top: 24px; display: grid; gap: 12px; max-width: 520px;">
        <h3 class="gh-title" style="font-size: 15px; margin: 0;">Add catalog entry</h3>
        <label>
          Display name
          <input class="gh-input" type="text" bind:value={newName} placeholder="e.g. Qwen SFT" />
        </label>
        <label>
          GGUF filename (under host/models/gguf)
          <input class="gh-input" type="text" bind:value={newGguf} placeholder="model.gguf" />
        </label>
        <label>
          OpenAI model name (sent to llama-server)
          <input class="gh-input" type="text" bind:value={newOpenai} placeholder="local-gguf" />
        </label>
        <label>
          Context size
          <input class="gh-input" type="number" bind:value={newCtx} min="256" step="256" />
        </label>
        <button type="submit" class="gh-btn gh-btn-primary" disabled={busy}>Add model</button>
      </form>
    </div>
  {/if}
</section>

<style>
  .gh-table th {
    color: var(--gh-text-muted);
    font-weight: 600;
  }
</style>
