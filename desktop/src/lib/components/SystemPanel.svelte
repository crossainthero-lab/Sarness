<script lang="ts">
  import { CircleAlert, Cpu, HardDrive, MemoryStick, MonitorCog, Zap } from '@lucide/svelte';
  import type { LiveStats, SystemInfo } from '../api/types';
  import Badge from '../ui/Badge.svelte';
  import Progress from '../ui/Progress.svelte';
  import { duration, mib } from '../util/format';

  let { system, stats = null, compact = false }: { system: SystemInfo; stats?: LiveStats | null; compact?: boolean } = $props();
  const g = $derived(system.hardware.gpus[0]);
  const live = $derived(stats?.gpus?.[0]);
  const vramUsed = $derived(live?.vram_used_mb ?? g?.vram_used_mb ?? 0);
  const vramTotal = $derived(live?.vram_total_mb ?? g?.vram_total_mb ?? 0);
  const ramUsed = $derived(stats?.ram_used_mb ?? system.hardware.memory.used_mb);
  const ramTotal = $derived(stats?.ram_total_mb ?? system.hardware.memory.total_mb);
  const st = $derived(system.hardware.storage);
  const rt = $derived(system.runtime);
</script>

<div class="sys" class:compact>
  <div class="tile gpu">
    <div class="th"><Zap /><span>GPU</span>{#if live}<span class="faint tnum">{live.utilization_pct}%{live.temperature_c ? ` · ${live.temperature_c}°C` : ''}</span>{/if}</div>
    {#if g}
      <div class="big truncate">{g.name}</div>
      <Progress value={vramTotal ? vramUsed / vramTotal : 0} tone={vramUsed / vramTotal > 0.9 ? 'warn' : 'accent'} />
      <div class="sub tnum">VRAM {mib(vramUsed)} used · {mib(vramTotal - vramUsed)} free · {mib(vramTotal)} total</div>
    {:else}
      <div class="big">No NVIDIA GPU detected</div>
      <div class="sub">Generation would run on the CPU.</div>
    {/if}
  </div>
  <div class="tile">
    <div class="th"><MemoryStick /><span>Memory</span></div>
    <div class="big tnum">{mib(ramTotal)}</div>
    <Progress value={ramUsed / ramTotal} tone="accent" />
    <div class="sub tnum">{mib(ramUsed)} used · {mib(ramTotal - ramUsed)} available</div>
  </div>
  <div class="tile">
    <div class="th"><Cpu /><span>CPU</span>{#if stats}<span class="faint tnum">{Math.round(stats.cpu_pct)}%</span>{/if}</div>
    <div class="big truncate" title={system.hardware.cpu.name}>{system.hardware.cpu.name.replace(/\(R\)|\(TM\)/g, '')}</div>
    <div class="sub">{system.hardware.cpu.cores_physical} cores · {system.hardware.cpu.cores_logical} threads</div>
  </div>
  <div class="tile">
    <div class="th"><HardDrive /><span>Storage</span></div>
    <div class="big tnum">{st.free_gb} GB free</div>
    <Progress value={st.used_gb / st.total_gb} tone={st.free_gb < 20 ? 'warn' : 'accent'} />
    <div class="sub tnum truncate" title={st.path}>{st.total_gb} GB volume · {st.path}</div>
  </div>
  {#if !compact}
    <div class="tile wide">
      <div class="th"><MonitorCog /><span>Runtime</span></div>
      <div class="chips">
        <Badge tone={g ? 'ok' : 'warn'} dot>CUDA driver {rt.cuda_driver ?? 'n/a'}</Badge>
        <Badge tone={rt.torch ? 'ok' : 'err'} dot>PyTorch {rt.torch ?? 'missing'}</Badge>
        <Badge tone={rt.diffusers ? 'ok' : 'err'} dot>Diffusers {rt.diffusers ?? 'missing'}</Badge>
        <Badge tone={rt.llama_cpp ? 'ok' : 'warn'} dot>llama.cpp {rt.llama_cpp ?? 'not installed'}</Badge>
        <Badge tone={rt.worker.alive ? 'accent' : 'neutral'} dot>GPU worker {rt.worker.alive ? (rt.worker.busy ? 'busy' : 'idle') : 'sleeping'}</Badge>
        <Badge>{system.hardware.distro}</Badge>
        <Badge>{system.hardware.hostname} · up {duration(system.engine.uptime_s)}</Badge>
      </div>
      {#if system.health.issues.length}
        <ul class="issues">
          {#each system.health.issues as i (i)}<li><CircleAlert />{i}</li>{/each}
        </ul>
      {/if}
    </div>
  {/if}
</div>

<style>
  .sys { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
  .tile {
    display: flex;
    flex-direction: column;
    gap: 7px;
    padding: 14px;
    border-radius: var(--r-lg);
    background: linear-gradient(180deg, var(--bg-3), var(--bg-2));
    border: 1px solid var(--line-1);
    min-width: 0;
  }
  .gpu { background: radial-gradient(120% 140% at 0% 0%, rgba(139, 92, 246, 0.16), transparent 60%), linear-gradient(180deg, var(--bg-3), var(--bg-2)); }
  .wide { grid-column: 1 / -1; }
  .th { display: flex; align-items: center; gap: 7px; font-size: var(--fs-xs); font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-3); }
  .th :global(svg) { width: 13px; height: 13px; color: var(--lavender); }
  .th .faint { margin-left: auto; text-transform: none; letter-spacing: 0; }
  .big { font-size: var(--fs-lg); font-weight: 600; color: var(--text-0); }
  .sub { font-size: var(--fs-xs); color: var(--text-2); }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .issues { list-style: none; margin: 4px 0 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .issues li { display: flex; gap: 7px; align-items: center; color: var(--warn); font-size: var(--fs-sm); }
  .issues :global(svg) { width: 14px; height: 14px; flex-shrink: 0; }
  .compact .tile { padding: 12px; }
</style>
