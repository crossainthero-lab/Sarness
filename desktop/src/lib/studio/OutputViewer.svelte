<script lang="ts">
  import { ChevronLeft, ChevronRight, Maximize2, X, Sparkles } from '@lucide/svelte';
  import { mediaUrl } from '../api/transport';
  import type { Generation, Job } from '../api/types';
  import { jobs } from '../stores/jobs.svelte';
  import Progress from '../ui/Progress.svelte';
  import IconButton from '../ui/IconButton.svelte';
  import Spinner from '../ui/Spinner.svelte';
  import { duration } from '../util/format';

  interface Props {
    current: Generation | null;
    running: Job | null;
    queued: number;
    kind: 'image' | 'video';
    canPrev: boolean;
    canNext: boolean;
    onprev: () => void;
    onnext: () => void;
    empty?: import('svelte').Snippet;
  }
  let { current, running, queued, kind, canPrev, canNext, onprev, onnext, empty }: Props = $props();
  let lightbox = $state(false);
  let loaded = $state(false);

  $effect(() => {
    void current?.id;
    loaded = false;
  });

  const preview = $derived(running ? jobs.previews[running.id] : null);
  const live = $derived(running ? jobs.progress[running.id] : null);
  const elapsed = $derived(running?.started_at ? Date.now() / 1000 - running.started_at : null);
</script>

<svelte:window onkeydown={(e) => {
  if ((e.target as HTMLElement)?.closest('input, textarea, [contenteditable]')) return;
  if (e.key === 'Escape' && lightbox) lightbox = false;
}} />

<div class="viewer">
  <div class="stage">
    {#if running && (preview || !current)}
      <div class="pending">
        {#if preview}
          <img class="preview" src={preview} alt="Live preview" />
        {:else}
          <div class="placeholder"><Spinner size={26} /></div>
        {/if}
      </div>
    {:else if current}
      {#key current.id}
        {#if current.type === 'video'}
          <!-- svelte-ignore a11y_media_has_caption -->
          <video class="media" src={mediaUrl(current.url)} poster={mediaUrl(current.thumb_url)} controls loop autoplay muted playsinline onloadeddata={() => (loaded = true)}></video>
        {:else}
          <button class="imgbtn" onclick={() => (lightbox = true)} aria-label="View full size">
            <img class="media" class:loaded src={mediaUrl(current.url)} alt={current.prompt ?? ''} onload={() => (loaded = true)} />
          </button>
        {/if}
      {/key}
    {:else}
      {@render empty?.()}
    {/if}

    {#if current && !running}
      <div class="nav left"><IconButton label="Previous (older)  ←" size="lg" disabled={!canPrev} onclick={onprev}><ChevronLeft /></IconButton></div>
      <div class="nav right"><IconButton label="Next (newer)  →" size="lg" disabled={!canNext} onclick={onnext}><ChevronRight /></IconButton></div>
      {#if kind === 'image'}<div class="corner"><IconButton label="Full size" onclick={() => (lightbox = true)}><Maximize2 /></IconButton></div>{/if}
    {/if}
  </div>

  {#if running || queued}
    <div class="jobbar glass">
      {#if running}
        <Sparkles />
        <div class="jb">
          <div class="row" style="gap:8px">
            <span class="jt">{running.status === 'queued' ? (running.waiting_reason ?? 'Queued') : (live?.text ?? running.progress_text ?? 'Working…')}</span>
            <span class="spacer"></span>
            {#if elapsed !== null && running.status === 'running'}<span class="faint tnum">{duration(elapsed)}</span>{/if}
            <span class="tnum muted">{Math.round((live?.progress ?? running.progress ?? 0) * 100)}%</span>
          </div>
          <Progress value={running.status === 'queued' ? null : (live?.progress ?? running.progress ?? 0)} />
        </div>
      {/if}
      {#if queued}<span class="q">{queued} queued</span>{/if}
    </div>
  {/if}
</div>

{#if lightbox && current && current.type === 'image'}
  <div class="lightbox" role="presentation" onclick={() => (lightbox = false)}>
    <img src={mediaUrl(current.url)} alt={current.prompt ?? ''} />
    <div class="lbx"><IconButton label="Close" size="lg" onclick={() => (lightbox = false)}><X /></IconButton></div>
    <div class="lbinfo">{current.width}×{current.height} · seed {current.seed}</div>
  </div>
{/if}

<style>
  .viewer { position: relative; flex: 1; min-height: 0; display: flex; flex-direction: column; }
  .stage {
    position: relative;
    flex: 1;
    min-height: 0;
    display: grid;
    place-items: center;
    padding: 20px 64px;
    background:
      radial-gradient(60% 50% at 50% 45%, rgba(var(--accent-rgb), 0.06), transparent 70%),
      repeating-conic-gradient(rgba(var(--fg-rgb), 0.012) 0% 25%, transparent 0% 50%) 50% / 24px 24px;
  }
  .media, .preview {
    max-width: 100%;
    max-height: 100%;
    border-radius: var(--r-lg);
    box-shadow: 0 30px 80px rgba(0, 0, 0, 0.55), 0 0 0 1px var(--line-1);
    object-fit: contain;
    display: block;
  }
  img.media { opacity: 0; transform: scale(0.992); transition: opacity var(--t-3) var(--ease), transform var(--t-3) var(--ease-out); }
  img.media.loaded { opacity: 1; transform: none; }
  video.media { background: #000; animation: fade-in var(--t-3) var(--ease); }
  .imgbtn { all: unset; cursor: zoom-in; max-width: 100%; max-height: 100%; display: grid; place-items: center; height: 100%; }
  .imgbtn img { max-height: calc(100vh - 260px); }
  .pending { position: relative; display: grid; place-items: center; max-width: 100%; max-height: 100%; }
  .preview { filter: saturate(1.05); image-rendering: auto; width: min(70vh, 100%); animation: fade-in var(--t-2); }
  .placeholder { width: 280px; height: 280px; border-radius: var(--r-xl); display: grid; place-items: center; background: var(--bg-2); border: 1px dashed var(--line-2); }
  .nav { position: absolute; top: 50%; transform: translateY(-50%); opacity: 0; transition: opacity var(--t-2) var(--ease); }
  .stage:hover .nav, .stage:hover .corner { opacity: 1; }
  .left { left: 14px; }
  .right { right: 14px; }
  .corner { position: absolute; top: 14px; right: 14px; opacity: 0; transition: opacity var(--t-2); }
  .nav :global(button), .corner :global(button) { background: rgba(10, 10, 14, 0.6); backdrop-filter: blur(10px); border: 1px solid var(--line-1); }
  .jobbar {
    position: absolute;
    left: 50%;
    bottom: 14px;
    transform: translateX(-50%);
    width: min(560px, calc(100% - 40px));
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    border-radius: var(--r-lg);
    background: var(--glass-strong);
    box-shadow: var(--shadow-3);
    animation: rise-in var(--t-3) var(--ease-out);
  }
  .jobbar > :global(svg) { width: 17px; height: 17px; color: var(--lavender); flex-shrink: 0; }
  .jb { flex: 1; display: flex; flex-direction: column; gap: 7px; min-width: 0; }
  .jt { font-size: var(--fs-sm); color: var(--text-1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .q { font-size: var(--fs-xs); color: var(--text-2); white-space: nowrap; padding-left: 10px; border-left: 1px solid var(--line-1); }
  .spacer { flex: 1; }
  .lightbox {
    position: fixed;
    inset: 0;
    z-index: 9000;
    display: grid;
    place-items: center;
    padding: 28px;
    background: rgba(3, 3, 5, 0.94);
    animation: fade-in var(--t-2) var(--ease);
    cursor: zoom-out;
  }
  .lightbox img { max-width: 100%; max-height: 100%; object-fit: contain; border-radius: var(--r-md); animation: pop-in var(--t-3) var(--ease-out); }
  .lbx { position: absolute; top: 16px; right: 16px; }
  .lbinfo { position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%); color: var(--text-2); font-size: var(--fs-sm); }
</style>
