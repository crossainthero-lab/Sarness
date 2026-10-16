<script lang="ts">
  import { Clapperboard, Dices, Info, Sparkles, Wand2 } from '@lucide/svelte';
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
  import { duration } from '../util/format';

  import { randomSeed, seedFor } from '../util/seed';
  let { active, paneId }: { active: boolean; paneId: string } = $props();
  const K = (n: string) => paneKey(paneId, n);
  const modeState = persisted(K('video.mode'), { mode: 'simple' as 'simple' | 'advanced' });
  $effect(() => savePersisted(K('video.mode'), $state.snapshot(modeState)));

  const p = persisted(K('video.simple'), {
    model: null as string | null,
    mode: 't2v' as 't2v' | 'i2v',
    prompt: '',
    negative_prompt: null as string | null,
    resolution: '',
    frames: 33,
    fps: 16,
    steps: 30,
    guidance: 5,
    seed: 0,
    random_seed: true,
    flow_shift: 3,
    start_image: null as string | null,
    end_image: null as string | null,
    memory_mode: 'auto',
    format: 'mp4',
  });
  const adv = persisted(K('video.workflow'), { graph: null as Workflow | null });
  $effect(() => savePersisted(K('video.simple'), $state.snapshot(p)));
  $effect(() => savePersisted(K('video.workflow'), $state.snapshot(adv)));

  const history = createHistory('video', paneId);
  let promptEl: HTMLTextAreaElement | null = $state(null);
  let submitting = $state(false);

  const model = $derived(modelById(p.model));
  const caps = $derived(model?.capabilities ?? {});
  const limits = $derived(model?.limits ?? {});
  const defaults = $derived((model?.defaults ?? {}) as Record<string, any>);
  const canI2V = $derived(!!caps.modes?.includes('i2v'));
  const resolutions = $derived((limits.resolutions ?? [[defaults.width ?? 832, defaults.height ?? 480]]).map(([w, h]) => ({ value: `${w}x${h}`, label: `${w} × ${h}`, hint: w > h ? 'Landscape' : w < h ? 'Portrait' : 'Square' })));
  const [w, h] = $derived((p.resolution || `${defaults.width ?? 832}x${defaults.height ?? 480}`).split('x').map(Number));
  const frameRange = $derived(limits.frames ?? [5, 81]);
  const frameStep = $derived(limits.frame_step ?? 4);
  const fpsRange = $derived(limits.fps ?? [8, 30]);
  const seconds = $derived(p.frames / p.fps);
  const queued = $derived(activeJobs('video').length);

  // Honest time estimate from this server's own completed runs with the same model.
  const secPerStep = $derived.by(() => {
    const runs = history.state.items.filter((g) => g.model_id === p.model && (g.metadata as any)?.elapsed_s && (g.metadata as any)?.steps);
    if (!runs.length) return null;
    const r = runs.slice(0, 5).map((g) => {
      const m = g.metadata as any;
      const px = (g.width ?? 1) * (g.height ?? 1) * (g.frames ?? 1);
      return m.elapsed_s / m.steps / px;
    });
    return r.reduce((a, b) => a + b, 0) / r.length;
  });
  const estimate = $derived(secPerStep ? secPerStep * p.steps * w * h * p.frames : null);

  $effect(() => {
    if (!models.loaded) return;
    const list = byCategory('video');
    if (list.length && (!p.model || !list.some((m) => m.id === p.model))) applyModel(list[0].id);
  });
  $effect(() => {
    if (!canI2V && p.mode === 'i2v') p.mode = 't2v';
  });

  function applyModel(id: string | null) {
    p.model = id;
    const d = (modelById(id)?.defaults ?? {}) as Record<string, any>;
    if (d.steps) p.steps = d.steps;
    if (d.guidance) p.guidance = d.guidance;
    if (d.frames) p.frames = d.frames;
    if (d.fps) p.fps = d.fps;
    if (d.flow_shift) p.flow_shift = d.flow_shift;
    p.resolution = d.width ? `${d.width}x${d.height}` : '';
  }

  function simpleParams(overrides: Record<string, unknown> = {}) {
    return {
      model: p.model,
      prompt: p.prompt.trim(),
      negative_prompt: p.negative_prompt?.trim() || null,
      width: w,
      height: h,
      frames: p.frames,
      fps: p.fps,
      steps: p.steps,
      guidance: p.guidance,
      seed: seedFor(p.random_seed, p.seed),
      flow_shift: p.flow_shift,
      start_image: p.mode === 'i2v' ? p.start_image : null,
      end_image: p.mode === 'i2v' && caps.end_frame ? p.end_image : null,
      memory_mode: p.memory_mode,
      format: p.format,
      ...overrides,
    };
  }

  async function run(job: Promise<Job>) {
    submitting = true;
    try {
      const j = await job;
      history.track(j.id);
    } catch (e) {
      toastError(e, 'Could not start video generation');
    } finally {
      submitting = false;
    }
  }

  function generate() {
    if (!p.model) return toast('warning', 'Choose a video model first');
    if (!p.prompt.trim()) {
      promptEl?.focus();
      return toast('warning', 'Write a prompt first');
    }
    if (p.mode === 'i2v' && !p.start_image) return toast('warning', 'Add a start frame for image-to-video');
    run(submitJob({ kind: 'video', simple: simpleParams(), ...destination() }));
  }

  function rerun(g: Generation, exact: boolean) {
    const simple = g.simple as Record<string, unknown> | null;
    if (!exact && simple) run(submitJob({ kind: 'video', simple: { ...simple, seed: randomSeed() }, ...destination() }));
    else run(api.post<Job>(`/v1/generations/${g.id}/rerun`, { new_seed: !exact }));
  }

  async function edit(g: Generation) {
    const s = g.simple as Record<string, any> | null;
    if (s) {
      p.model = s.model ?? p.model;
      p.prompt = s.prompt ?? '';
      p.negative_prompt = s.negative_prompt ?? null;
      p.frames = s.frames ?? p.frames;
      p.fps = s.fps ?? p.fps;
      p.steps = s.steps ?? p.steps;
      p.guidance = s.guidance ?? p.guidance;
      p.resolution = `${s.width}x${s.height}`;
      p.start_image = s.start_image ?? null;
      p.end_image = s.end_image ?? null;
      p.mode = s.start_image ? 'i2v' : 't2v';
    } else {
      const full = await api.get<Generation>(`/v1/generations/${g.id}`);
      if (full.workflow) {
        adv.graph = full.workflow;
        modeState.mode = 'advanced';
        persistPrefs();
        return;
      }
    }
    await tick();
    promptEl?.focus();
  }

  async function setMode(m: 'simple' | 'advanced') {
    if (m === modeState.mode) return;
    if (m === 'advanced') {
      adv.graph = await switchToAdvanced('video', adv.graph, simpleParams());
    } else {
      const s = await switchToSimple(adv.graph);
      if (s === false) return;
      if (s) {
        const x = s as Record<string, any>;
        p.model = x.model;
        p.prompt = x.prompt ?? '';
        p.negative_prompt = x.negative_prompt ?? null;
        p.resolution = `${x.width}x${x.height}`;
        p.frames = x.frames;
        p.fps = x.fps;
        p.steps = x.steps;
        p.guidance = x.guidance;
        p.random_seed = x.seed < 0;
        if (x.seed >= 0) p.seed = x.seed;
        p.flow_shift = x.flow_shift;
        p.start_image = x.start_image ?? null;
        p.end_image = x.end_image ?? null;
        p.mode = x.start_image ? 'i2v' : 't2v';
      }
    }
    modeState.mode = m;
    persistPrefs();
  }
</script>

<StudioShell {paneId} kind="video" title="Videos" mode={modeState.mode} {history} {active}
  onmode={setMode} onnew={() => { p.prompt = ''; p.start_image = null; p.end_image = null; history.state.index = 0; promptEl?.focus(); }}
  onrerun={rerun} onedit={edit}>
  {#snippet controls()}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div class="ctl" role="group" onkeydown={(e) => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); generate(); } }}>
      <Field label="Model"><ModelSelect bind:value={p.model} category="video" onchange={applyModel} /></Field>
      {#if model?.notes}<p class="note"><Info />{model.notes}</p>{/if}

      <Segmented bind:value={p.mode} full items={[
        { value: 't2v', label: 'Text → Video' },
        { value: 'i2v', label: 'Image → Video', disabled: !canI2V, title: canI2V ? undefined : 'This model does not support image-to-video' },
      ]} />

      <div class="composer">
        <TextArea bind:el={promptEl} bind:value={p.prompt} minRows={5} maxRows={14} placeholder="Describe the scene, subject and camera motion…" />
      </div>

      {#if p.mode === 'i2v'}
        <div class="frames" class:two={caps.end_frame}>
          <Field label="Start frame"><ImageInput bind:fileId={p.start_image} label="Start frame" /></Field>
          {#if caps.end_frame}<Field label="End frame"><ImageInput bind:fileId={p.end_image} label="End frame" /></Field>{/if}
        </div>
      {/if}

      <Field label="Resolution"><Select bind:value={p.resolution} options={resolutions} /></Field>
      <Slider bind:value={p.frames} min={frameRange[0]} max={frameRange[1]} step={frameStep} label="Length" format={(v) => `${v} frames · ${(v / p.fps).toFixed(1)} s`} />
      {#if fpsRange[0] !== fpsRange[1]}<Slider bind:value={p.fps} min={fpsRange[0]} max={fpsRange[1]} label="Frame rate" unit=" fps" />{/if}

      <div class="est">
        <span>{seconds.toFixed(1)} s clip · {w}×{h}</span>
        <span class="faint">{estimate ? `≈ ${duration(estimate)} on this server` : 'Time estimate appears after the first run'}</span>
      </div>

      <Button variant="primary" size="lg" block onclick={generate} loading={submitting} disabled={!p.model}>
        <Sparkles />Generate video{queued ? ` · ${queued} in queue` : ''}
      </Button>

      <Collapsible title="Advanced settings">
        {#if caps.negative_prompt !== false}
          <Field label="Negative prompt" hint="Leave empty to use the model's recommended negative prompt.">
            <TextArea value={p.negative_prompt ?? ''} oninput={(e) => (p.negative_prompt = (e.currentTarget as HTMLTextAreaElement).value || null)} minRows={2} maxRows={6} />
          </Field>
        {/if}
        <Field label="Seed">
          <div class="row">
            <TextInput bind:value={p.seed} type="number" disabled={p.random_seed} mono size="sm" />
            <IconButton label="Random seed now" onclick={() => { p.seed = randomSeed(); p.random_seed = false; }}><Dices /></IconButton>
          </div>
        </Field>
        <Toggle bind:checked={p.random_seed} label="New random seed each run" />
        <Slider bind:value={p.steps} min={limits.steps?.[0] ?? 4} max={limits.steps?.[1] ?? 60} label="Steps" />
        {#if caps.guidance !== false}<Slider bind:value={p.guidance} min={limits.guidance?.[0] ?? 1} max={limits.guidance?.[1] ?? 10} step={0.1} label="Guidance" format={(v) => v.toFixed(1)} />{/if}
        {#if caps.flow_shift !== false}<Slider bind:value={p.flow_shift} min={0.5} max={12} step={0.1} label="Flow shift" format={(v) => v.toFixed(1)} />{/if}
        {#if caps.remote}
          <p class="faint small">Runs on the server's AI gateway: memory placement is managed there. Output is MP4 at 24 fps.</p>
        {:else}
        <Field label="Memory mode" hint="Split keeps the video transformer on the GPU and streams the large text encoder from system RAM.">
          <Select bind:value={p.memory_mode} size="sm" options={[{ value: 'auto', label: 'Auto' }, { value: 'gpu', label: 'GPU (needs ~16 GB+)' }, { value: 'split', label: 'Split' }, { value: 'offload', label: 'Offload' }, { value: 'sequential', label: 'Sequential (slowest)' }]} />
        </Field>
        <Field label="Format"><Select bind:value={p.format} size="sm" options={[{ value: 'mp4', label: 'MP4 (H.264)' }, { value: 'webm', label: 'WebM (VP9)' }, { value: 'gif', label: 'GIF' }]} /></Field>
        {/if}
        {#if !caps.motion?.length}<p class="faint small">This model has no dedicated motion controls; describe camera and subject motion in the prompt.</p>{/if}
      </Collapsible>
    </div>
  {/snippet}

  {#snippet empty()}
    <Empty icon={Clapperboard} title="Generate a video" body={byCategory('video').length ? 'Describe a short scene. Videos take a few minutes on a 12 GB GPU — you can keep working while they render.' : 'Install a video model first. Wan 2.1 1.3B is the realistic choice for 12 GB GPUs.'}>
      {#if !byCategory('video').length}<Button variant="primary" onclick={() => { prefs.view = 'models'; persistPrefs(); }}><Wand2 />Browse models</Button>{/if}
    </Empty>
  {/snippet}

  {#snippet advanced()}
    <WorkflowEditor kind="video" bind:graph={adv.graph} {active}
      onrun={async (g) => { const j = await submitJob({ kind: 'video', workflow: g, ...destination() }); history.track(j.id); return j; }}
      onrebuild={async () => { adv.graph = await switchToAdvanced('video', null, simpleParams()); }} />
  {/snippet}
</StudioShell>

<style>
  .ctl { display: flex; flex-direction: column; gap: 16px; padding: 18px 18px 28px; }
  .composer :global(textarea) { font-size: var(--fs-lg); line-height: 1.55; padding: 12px 14px; border-radius: var(--r-lg); background: var(--bg-2); }
  .frames { display: grid; gap: 10px; }
  .frames.two { grid-template-columns: 1fr 1fr; }
  .note { display: flex; gap: 8px; font-size: var(--fs-xs); color: var(--text-2); line-height: 1.5; padding: 8px 10px; border-radius: var(--r-md); background: var(--info-bg); margin-top: -6px; }
  .note :global(svg) { width: 14px; height: 14px; color: var(--info); flex-shrink: 0; margin-top: 1px; }
  .est { display: flex; justify-content: space-between; gap: 8px; font-size: var(--fs-xs); color: var(--text-1); padding: 8px 10px; border-radius: var(--r-md); background: var(--bg-2); flex-wrap: wrap; }
  .small { font-size: var(--fs-xs); }
</style>
