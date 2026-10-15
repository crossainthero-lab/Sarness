<script lang="ts">
  import { Dices, ImagePlus, Plus, Sparkles, Trash2, Wand2 } from '@lucide/svelte';
  import { tick } from 'svelte';
  import { api } from '../api/client';
  import type { Generation, Job, Workflow } from '../api/types';
  import { createHistory } from '../stores/history.svelte';
  import { activeJobs, submitJob } from '../stores/jobs.svelte';
  import { byCategory, modelById, models } from '../stores/models.svelte';
  import { persisted, prefs, persistPrefs, savePersisted } from '../stores/prefs.svelte';
  import { paneKey } from '../stores/panes.svelte';
  import { destination } from '../stores/projects.svelte';
  import { toast, toastError } from '../stores/toast.svelte';
  import StudioShell from '../studio/StudioShell.svelte';
  import ImageInput from '../studio/ImageInput.svelte';
  import MaskPainter from '../studio/MaskPainter.svelte';
  import { ASPECTS, dimsFor } from '../studio/aspect';
  import ModelSelect from '../components/ModelSelect.svelte';
  import WorkflowEditor from '../workflow/WorkflowEditor.svelte';
  import { switchToAdvanced, switchToSimple } from '../workflow/modes';
  import Button from '../ui/Button.svelte';
  import Collapsible from '../ui/Collapsible.svelte';
  import Empty from '../ui/Empty.svelte';
  import Field from '../ui/Field.svelte';
  import IconButton from '../ui/IconButton.svelte';
  import Segmented from '../ui/Segmented.svelte';
  import Select from '../ui/Select.svelte';
  import Slider from '../ui/Slider.svelte';
  import TextArea from '../ui/TextArea.svelte';
  import TextInput from '../ui/TextInput.svelte';
  import Toggle from '../ui/Toggle.svelte';

  // int32-safe: the server's AI gateway rejects seeds above 2^31-1.
  const randomSeed = () => Math.floor(Math.random() * 2 ** 31);
  let { active, paneId }: { active: boolean; paneId: string } = $props();
  const K = (n: string) => paneKey(paneId, n);
  const modeState = persisted(K('image.mode'), { mode: 'simple' as 'simple' | 'advanced' });
  $effect(() => savePersisted(K('image.mode'), $state.snapshot(modeState)));

  const p = persisted(K('image.simple'), {
    model: null as string | null,
    prompt: '',
    negative_prompt: '',
    aspect: '1:1',
    size: 'M' as 'S' | 'M' | 'L',
    quality: 'balanced' as 'fast' | 'balanced' | 'best',
    batch_size: 1,
    seed: 0,
    random_seed: true,
    steps: 30,
    guidance: 6,
    scheduler: 'default',
    denoise: 0.65,
    reference_image: null as string | null,
    mask_image: null as string | null,
    loras: [] as { id: string; strength: number }[],
    vae: null as string | null,
    memory_mode: 'auto',
    upscale_model: null as string | null,
    upscale_factor: 2,
    format: 'png',
    clip_skip: 0,
  });
  const adv = persisted(K('image.workflow'), { graph: null as Workflow | null });
  $effect(() => savePersisted(K('image.simple'), $state.snapshot(p)));
  $effect(() => savePersisted(K('image.workflow'), $state.snapshot(adv)));

  const history = createHistory('image', paneId);
  let promptEl: HTMLTextAreaElement | null = $state(null);
  let submitting = $state(false);
  let maskOpen = $state(false);

  const model = $derived(modelById(p.model));
  const caps = $derived(model?.capabilities ?? {});
  const limits = $derived(model?.limits ?? {});
  const defaults = $derived((model?.defaults ?? {}) as Record<string, any>);
  const baseArea = $derived((defaults.width ?? 1024) * (defaults.height ?? 1024));
  const sizeMul = $derived({ S: 0.75, M: 1, L: 1.25 }[p.size]);
  const dims = $derived(dimsFor(p.aspect, baseArea * sizeMul * sizeMul, 64, limits.min_side ?? 256, limits.max_side ?? 2048));
  const stepRange = $derived(limits.steps ?? [1, 100]);
  const cfgRange = $derived(limits.guidance ?? [0, 20]);
  const schedulerOptions = $derived([{ value: 'default', label: 'Model default' }, ...(caps.schedulers ?? []).map((s) => ({ value: s, label: s.replace(/_/g, ' ') }))]);
  const loraModels = $derived(byCategory('lora'));
  const queued = $derived(activeJobs('image').length);

  // Pick a model automatically and apply its defaults when it changes.
  $effect(() => {
    if (!models.loaded) return;
    const list = byCategory('image');
    if (list.length && (!p.model || !list.some((m) => m.id === p.model))) applyModel(list[0].id);
  });

  function applyModel(id: string | null) {
    p.model = id;
    const d = (modelById(id)?.defaults ?? {}) as Record<string, any>;
    if (d.steps) p.steps = d.steps;
    if (d.guidance !== undefined) p.guidance = d.guidance;
    p.scheduler = 'default';
    p.quality = 'balanced';
  }

  function setQuality(q: 'fast' | 'balanced' | 'best') {
    p.quality = q;
    const base = defaults.steps ?? 30;
    const mul = { fast: 0.6, balanced: 1, best: 1.6 }[q];
    p.steps = Math.round(Math.min(stepRange[1], Math.max(stepRange[0], base * mul)));
  }

  function simpleParams(overrides: Record<string, unknown> = {}) {
    return {
      model: p.model,
      prompt: p.prompt.trim(),
      negative_prompt: caps.negative_prompt === false ? '' : p.negative_prompt.trim(),
      width: dims[0],
      height: dims[1],
      batch_size: p.batch_size,
      steps: p.steps,
      guidance: p.guidance,
      seed: p.random_seed ? randomSeed() : p.seed,
      scheduler: p.scheduler,
      denoise: p.denoise,
      reference_image: p.reference_image,
      mask_image: p.reference_image ? p.mask_image : null,
      loras: caps.lora ? p.loras.filter((l) => l.id) : [],
      vae: p.vae,
      memory_mode: p.memory_mode,
      upscale: p.upscale_model ? { model: p.upscale_model, factor: p.upscale_factor } : null,
      format: p.format,
      clip_skip: p.clip_skip,
      ...overrides,
    };
  }

  async function run(job: Promise<Job>) {
    submitting = true;
    try {
      const j = await job;
      history.track(j.id);
    } catch (e: any) {
      toastError(e, 'Could not start generation');
    } finally {
      submitting = false;
    }
  }

  function generate() {
    if (!p.model) return toast('warning', 'Choose a model first');
    if (!p.prompt.trim()) {
      promptEl?.focus();
      return toast('warning', 'Write a prompt first');
    }
    run(submitJob({ kind: 'image', simple: simpleParams(), ...destination() }));
  }

  function rerun(g: Generation, exact: boolean) {
    run(api.post<Job>(`/v1/generations/${g.id}/rerun`, { new_seed: !exact }).then((j) => j));
  }

  function vary(g: Generation, strength: number) {
    const base = (g.simple ?? {}) as Record<string, any>;
    const simple = {
      ...simpleParams(),
      ...base,
      model: base.model ?? g.model_id ?? p.model,
      prompt: g.prompt ?? p.prompt,
      reference_image: g.file_id,
      mask_image: null,
      denoise: strength,
      seed: -1,
      batch_size: 1,
      width: g.width,
      height: g.height,
      upscale: null,
    };
    run(submitJob({ kind: 'image', simple, ...destination(), title: `Variation of “${(g.prompt ?? '').slice(0, 60)}”` }));
  }

  async function edit(g: Generation) {
    const s = g.simple as Record<string, any> | null;
    if (s) {
      if (s.model) p.model = s.model;
      p.prompt = s.prompt ?? '';
      p.negative_prompt = s.negative_prompt ?? '';
      p.steps = s.steps ?? p.steps;
      p.guidance = s.guidance ?? p.guidance;
      p.scheduler = s.scheduler ?? 'default';
      p.loras = s.loras ?? [];
      p.vae = s.vae ?? null;
      p.reference_image = s.reference_image ?? null;
      p.mask_image = s.mask_image ?? null;
      if (s.denoise) p.denoise = s.denoise;
      if (typeof s.seed === 'number') { p.seed = s.seed; }
      const match = ASPECTS.find((a) => Math.abs(a.w / a.h - (s.width ?? 1) / (s.height ?? 1)) < 0.03);
      if (match) p.aspect = match.value;
    } else {
      const full = await api.get<Generation>(`/v1/generations/${g.id}`);
      if (full.workflow) {
        adv.graph = full.workflow;
        setMode('advanced', true);
        toast('info', 'Opened the generation’s workflow in Advanced mode');
        return;
      }
    }
    await tick();
    promptEl?.focus();
  }

  function newGeneration() {
    p.prompt = '';
    p.reference_image = null;
    p.mask_image = null;
    p.random_seed = true;
    history.state.index = 0;
    promptEl?.focus();
  }

  async function setMode(m: 'simple' | 'advanced', keepGraph = false) {
    if (m === modeState.mode) return;
    if (m === 'advanced') {
      if (!keepGraph) adv.graph = await switchToAdvanced('image', adv.graph, simpleParams({ seed: p.random_seed ? -1 : p.seed }));
    } else {
      const s = await switchToSimple(adv.graph);
      if (s === false) return;
      if (s) applySimple(s);
    }
    modeState.mode = m;
    persistPrefs();
  }

  function applySimple(s: Record<string, any>) {
    p.model = s.model ?? p.model;
    p.prompt = s.prompt ?? '';
    p.negative_prompt = s.negative_prompt ?? '';
    p.steps = s.steps;
    p.guidance = s.guidance;
    p.scheduler = s.scheduler ?? 'default';
    p.batch_size = s.batch_size ?? 1;
    p.random_seed = s.seed < 0;
    if (s.seed >= 0) p.seed = s.seed;
    p.loras = s.loras ?? [];
    p.vae = s.vae ?? null;
    p.memory_mode = s.memory_mode ?? 'auto';
    p.reference_image = s.reference_image ?? null;
    p.mask_image = s.mask_image ?? null;
    p.denoise = s.denoise ?? p.denoise;
    p.format = s.format ?? 'png';
    p.upscale_model = s.upscale?.model ?? null;
    p.upscale_factor = s.upscale?.factor ?? 2;
    const match = ASPECTS.find((a) => Math.abs(a.w / a.h - s.width / s.height) < 0.03);
    if (match) p.aspect = match.value;
  }

  async function runWorkflow(graph: Workflow) {
    try {
      const j = await submitJob({ kind: 'image', workflow: graph, ...destination() });
      history.track(j.id);
      return j;
    } catch (e) {
      toastError(e, 'Workflow could not start');
      throw e;
    }
  }

  function keydown(e: KeyboardEvent) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      generate();
    }
  }
</script>

<StudioShell {paneId} kind="image" title="Images" mode={modeState.mode} {history} {active}
  onmode={(m) => setMode(m)} onnew={newGeneration} onrerun={rerun} onvary={caps.modes?.includes('img2img') !== false ? vary : undefined} onedit={edit}>
  {#snippet controls()}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div class="ctl" onkeydown={keydown} role="group">
      <div class="composer">
        <TextArea bind:el={promptEl} bind:value={p.prompt} minRows={5} maxRows={16} placeholder="Describe the image you want to create…" />
        <div class="chint faint">Ctrl + Enter to generate</div>
      </div>

      <Field label="Model">
        <ModelSelect bind:value={p.model} category="image" onchange={(v) => applyModel(v)} />
      </Field>

      <Field label="Aspect ratio">
        <div class="aspects">
          {#each ASPECTS as a (a.value)}
            <button class="asp" class:on={p.aspect === a.value} onclick={() => (p.aspect = a.value)} title={a.value}>
              <span class="shape" style="aspect-ratio:{a.w}/{a.h}"></span>
              <span>{a.value}</span>
            </button>
          {/each}
        </div>
      </Field>

      <div class="two">
        <Field label="Size" aside={undefined}>
          <Segmented bind:value={p.size} full items={[{ value: 'S', label: 'S' }, { value: 'M', label: 'M' }, { value: 'L', label: 'L' }]} />
        </Field>
        <Field label="Quality">
          <Segmented value={p.quality} full onchange={setQuality} items={[{ value: 'fast', label: 'Fast' }, { value: 'balanced', label: 'Std' }, { value: 'best', label: 'Best' }]} />
        </Field>
      </div>
      <div class="dims faint tnum">{dims[0]} × {dims[1]} px · {p.steps} steps{p.batch_size > 1 ? ` · ${p.batch_size} images` : ''}</div>

      {#if caps.modes?.includes('img2img') !== false}
        <Field label="Reference image" hint={p.reference_image ? (p.mask_image ? 'Inpainting: only the masked area is regenerated.' : 'Image-to-image: lower strength keeps more of the reference.') : 'Optional. Paint a mask on it to inpaint.'}>
          <ImageInput bind:fileId={p.reference_image} onpaint={caps.modes?.includes('inpaint') !== false ? () => (maskOpen = true) : undefined} painted={!!p.mask_image} />
        </Field>
        {#if p.reference_image && caps.denoise !== false}
          <Slider bind:value={p.denoise} min={0.05} max={1} step={0.01} label="Strength" format={(v) => v.toFixed(2)} />
        {/if}
      {/if}

      <Button variant="primary" size="lg" block onclick={generate} loading={submitting} disabled={!p.model}>
        <Sparkles />Generate{queued ? ` · ${queued} in queue` : ''}
      </Button>

      <Collapsible title="Advanced settings">
        {#if caps.negative_prompt !== false}
          <Field label="Negative prompt"><TextArea bind:value={p.negative_prompt} minRows={2} maxRows={6} placeholder="What to avoid…" /></Field>
        {/if}
        <Field label="Seed">
          <div class="row">
            <TextInput bind:value={p.seed} type="number" disabled={p.random_seed} mono size="sm" />
            <IconButton label="Random seed now" onclick={() => { p.seed = randomSeed(); p.random_seed = false; }}><Dices /></IconButton>
          </div>
        </Field>
        <Toggle bind:checked={p.random_seed} label="New random seed each run" />
        {#if caps.steps !== false}<Slider bind:value={p.steps} min={stepRange[0]} max={stepRange[1]} label="Steps" />{/if}
        {#if caps.guidance !== false}<Slider bind:value={p.guidance} min={cfgRange[0]} max={cfgRange[1]} step={0.1} label="Guidance (CFG)" format={(v) => v.toFixed(1)} />{/if}
        <Slider bind:value={p.batch_size} min={1} max={4} label="Batch size" />
        {#if caps.schedulers?.length}
          <Field label="Scheduler"><Select bind:value={p.scheduler} options={schedulerOptions} size="sm" /></Field>
        {/if}
        {#if caps.lora}
          <Field label="LoRAs" hint={loraModels.length ? '' : 'Install LoRAs from Models → Catalog or Hugging Face.'}>
            <div class="loras">
              {#each p.loras as l, i (i)}
                <div class="lora">
                  <div class="lsel"><ModelSelect bind:value={l.id} category="lora" size="sm" /></div>
                  <IconButton label="Remove LoRA" size="sm" onclick={() => p.loras.splice(i, 1)}><Trash2 /></IconButton>
                  <div class="lw"><Slider bind:value={l.strength} min={-2} max={2} step={0.05} label="Strength" format={(v) => v.toFixed(2)} /></div>
                </div>
              {/each}
              <Button size="sm" variant="ghost" disabled={!loraModels.length} onclick={() => p.loras.push({ id: loraModels[0]?.id, strength: 1 })}><Plus />Add LoRA</Button>
            </div>
          </Field>
        {/if}
        {#if !caps.remote}
        <Field label="VAE"><ModelSelect bind:value={p.vae} category="vae" allowNone noneLabel="Model default" size="sm" /></Field>
        <Field label="Upscale result" hint="Runs a super-resolution model after generation.">
          <ModelSelect bind:value={p.upscale_model} category="upscaler" allowNone noneLabel="Off" size="sm" />
        </Field>
        {#if p.upscale_model}
          <Slider bind:value={p.upscale_factor} min={1} max={4} step={0.5} label="Upscale factor" format={(v) => `${v}×`} />
        {/if}
        <Field label="Memory mode" hint="Auto keeps the model on the GPU when it fits, otherwise offloads to system RAM.">
          <Select bind:value={p.memory_mode} size="sm" options={[{ value: 'auto', label: 'Auto' }, { value: 'gpu', label: 'GPU (fastest)' }, { value: 'offload', label: 'Offload (lower VRAM)' }, { value: 'sequential', label: 'Sequential (minimum VRAM)' }]} />
        </Field>
        <div class="two">
          <Field label="Format"><Select bind:value={p.format} size="sm" options={[{ value: 'png', label: 'PNG (with metadata)' }, { value: 'webp', label: 'WebP' }, { value: 'jpeg', label: 'JPEG' }]} /></Field>
          <Field label="CLIP skip"><Select bind:value={p.clip_skip} size="sm" options={[0, 1, 2].map((v) => ({ value: v, label: v ? String(v) : 'Off' }))} /></Field>
        </div>
        {:else}
          <p class="faint small">Runs on the server's AI gateway: memory mode, VAE, upscaling and output format are managed there. Output is PNG.</p>
        {/if}
      </Collapsible>
    </div>
  {/snippet}

  {#snippet empty()}
    <Empty icon={ImagePlus} title="Create your first image" body={byCategory('image').length ? 'Describe what you want on the left and press Generate. Every result is saved to your library with its full settings.' : 'Install an image model (SDXL Turbo is a fast, 12 GB-friendly start) to begin.'}>
      {#if !byCategory('image').length}<Button variant="primary" onclick={() => { prefs.view = 'models'; persistPrefs(); }}><Wand2 />Browse models</Button>{/if}
    </Empty>
  {/snippet}

  {#snippet advanced()}
    <WorkflowEditor kind="image" bind:graph={adv.graph} {active}
      onrun={runWorkflow}
      onrebuild={async () => { adv.graph = await switchToAdvanced('image', null, simpleParams()); }} />
  {/snippet}
</StudioShell>

{#if maskOpen && p.reference_image}
  <MaskPainter bind:open={maskOpen} imageId={p.reference_image} bind:maskId={p.mask_image} />
{/if}

<style>
  .ctl { display: flex; flex-direction: column; gap: 16px; padding: 18px 18px 28px; }
  .composer { position: relative; }
  .composer :global(textarea) { font-size: var(--fs-lg); line-height: 1.55; padding: 12px 14px 26px; border-radius: var(--r-lg); background: var(--bg-2); }
  .chint { position: absolute; right: 12px; bottom: 8px; font-size: var(--fs-xs); pointer-events: none; }
  .aspects { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
  .asp {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 5px;
    padding: 8px 4px 6px;
    border-radius: var(--r-md);
    border: 1px solid var(--line-1);
    background: var(--bg-2);
    color: var(--text-2);
    font-size: var(--fs-xs);
    cursor: pointer;
    transition: border-color var(--t-1), background var(--t-1), color var(--t-1);
  }
  .asp:hover { border-color: var(--line-2); color: var(--text-0); }
  .asp.on { border-color: var(--select-line); background: var(--select-bg); color: var(--lavender); }
  .shape { width: auto; height: 20px; max-width: 34px; border-radius: 3px; border: 1.5px solid currentColor; opacity: 0.85; }
  .two { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .dims { font-size: var(--fs-xs); margin-top: -8px; }
  .loras { display: flex; flex-direction: column; gap: 10px; }
  .lora { display: grid; grid-template-columns: 1fr auto; gap: 6px; align-items: center; padding: 8px; border-radius: var(--r-md); background: var(--bg-2); border: 1px solid var(--line-0); }
  .lw { grid-column: 1 / -1; }
</style>
