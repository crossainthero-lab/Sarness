<script lang="ts">
  import { Handle, Position, type NodeProps } from '@xyflow/svelte';
  import { CircleAlert, CircleCheck, Zap, ChevronDown, Cpu } from '@lucide/svelte';
  import { editor } from './context';
  import { inputSockets } from './graph';
  import ParamWidget from './ParamWidget.svelte';
  import Spinner from '../ui/Spinner.svelte';

  let { id, data, selected }: NodeProps = $props();
  const ed = editor();
  const spec = $derived(ed.specs.get(data.nodeType as string));
  const params = $derived((data.params ?? {}) as Record<string, unknown>);
  const st = $derived(ed.state(id));
  const prog = $derived(ed.progress(id));
  const preview = $derived(ed.preview(id));
  const output = $derived(ed.output(id));
  const issue = $derived(ed.issue(id));
  let showAdvanced = $state(false);

  const sockets = $derived(spec ? inputSockets(spec) : []);
  const mainParams = $derived(spec?.params.filter((p) => !p.advanced) ?? []);
  const advParams = $derived(spec?.params.filter((p) => p.advanced) ?? []);
  const catColor = $derived(
    ({ Loaders: '#d4d4d4', Sampling: '#a3a3a3', Prompt: '#fbbf24', Latent: '#fb923c', VAE: '#f87171', Image: '#60a5fa', Transform: '#60a5fa', Mask: '#94a3b8', Video: '#38bdf8', Upscale: '#2dd4bf', Output: '#5fd39b', Conditioning: '#a3a3a3', Control: '#737373', Schedulers: '#34d399' } as Record<string, string>)[spec?.category ?? ''] ?? '#8b8a96',
  );
</script>

<div class="node {st?.status ?? ''}" class:selected class:issue={!!issue || st?.status === 'error'} style="--cat:{catColor}">
  <header ondblclick={() => ed.rename(id)} role="presentation">
    <span class="cat"></span>
    <span class="title truncate">{(data.label as string) || spec?.title || data.nodeType}</span>
    {#if spec?.gpu}<span class="gpu" title="Runs on the GPU"><Cpu /></span>{/if}
    {#if st?.status === 'running'}<Spinner size={13} />
    {:else if st?.status === 'done'}<span class="ok" title={st.elapsed_s !== undefined ? `${st.elapsed_s}s` : ''}><CircleCheck /></span>
    {:else if st?.status === 'cached'}<span class="cached" title="Reused cached result"><Zap /></span>
    {:else if st?.status === 'error'}<span class="bad"><CircleAlert /></span>{/if}
  </header>

  {#if !spec}
    <div class="body"><p class="unknown">Unknown node type “{data.nodeType}”. It may come from a newer engine.</p></div>
  {:else}
    <div class="io">
      <div class="ins">
        {#each sockets as s (s.name)}
          {#if !s.param || ed.connected(id, s.name)}
            <div class="sock in">
              <Handle type="target" position={Position.Left} id={s.name} style="background:{ed.socketColor(s.type)}" class="hdl" />
              <span class="sl" class:opt={s.optional}>{s.label}</span>
              <span class="st">{s.type}</span>
            </div>
          {/if}
        {/each}
      </div>
      <div class="outs">
        {#each spec.outputs as o (o.name)}
          <div class="sock out">
            <span class="st">{o.type}</span>
            <span class="sl">{o.label}</span>
            <Handle type="source" position={Position.Right} id={o.name} style="background:{ed.socketColor(o.type)}" class="hdl" />
          </div>
        {/each}
      </div>
    </div>

    {#if mainParams.length || advParams.length}
      <div class="params">
        {#each mainParams as p (p.name)}
          <div class="prow">
            {#if p.socket && !ed.connected(id, p.name)}
              <Handle type="target" position={Position.Left} id={p.name} style="background:{ed.socketColor(p.socket_type ?? 'STRING')}" class="hdl ph" />
            {/if}
            <ParamWidget spec={p} value={params[p.name]} disabled={ed.connected(id, p.name)} onchange={(v) => ed.setParam(id, p.name, v)} />
          </div>
        {/each}
        {#if advParams.length}
          <button class="more nodrag" type="button" onclick={() => (showAdvanced = !showAdvanced)}>
            <ChevronDown style={showAdvanced ? 'transform:rotate(180deg)' : ''} />{showAdvanced ? 'Less' : `${advParams.length} more`}
          </button>
          {#if showAdvanced}
            {#each advParams as p (p.name)}
              <div class="prow">
                {#if p.socket && !ed.connected(id, p.name)}<Handle type="target" position={Position.Left} id={p.name} style="background:{ed.socketColor(p.socket_type ?? 'STRING')}" class="hdl ph" />{/if}
                <ParamWidget spec={p} value={params[p.name]} disabled={ed.connected(id, p.name)} onchange={(v) => ed.setParam(id, p.name, v)} />
              </div>
            {/each}
          {/if}
        {/if}
      </div>
    {/if}
  {/if}

  {#if prog && st?.status === 'running'}
    <div class="prog"><span style="transform:scaleX({prog.value})"></span></div>
    {#if prog.text}<div class="ptxt">{prog.text}</div>{/if}
  {/if}
  {#if preview}<img class="preview" src={preview} alt="Live preview" />{/if}
  {#if output}<img class="preview" src={output} alt="Output" />{/if}
  {#if st?.status === 'error' || issue}
    <div class="err selectable nodrag">{st?.message ?? issue}</div>
  {/if}
</div>

<style>
  .node {
    width: 280px;
    border-radius: 12px;
    background: linear-gradient(180deg, rgba(30, 29, 37, 0.97), rgba(21, 21, 26, 0.97));
    border: 1px solid var(--line-1);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
    font-size: 12px;
    color: var(--text-1);
    transition: border-color var(--t-1), box-shadow var(--t-2), opacity var(--t-2);
  }
  .node.selected { border-color: var(--select-line); box-shadow: 0 0 0 1px var(--select-line), 0 14px 40px rgba(0, 0, 0, 0.55); }
  .node.running { border-color: var(--accent-hi); box-shadow: 0 0 0 1px rgba(var(--accent-rgb), 0.6), 0 0 28px rgba(var(--accent-rgb), 0.35); }
  .node.issue { border-color: rgba(244, 113, 116, 0.7); }
  .node.skipped { opacity: 0.45; }
  header {
    display: flex;
    align-items: center;
    gap: 7px;
    height: 32px;
    padding: 0 10px;
    border-bottom: 1px solid var(--line-0);
    background: linear-gradient(90deg, color-mix(in srgb, var(--cat) 14%, transparent), transparent 70%);
    border-radius: 12px 12px 0 0;
  }
  .cat { width: 7px; height: 7px; border-radius: 2px; background: var(--cat); box-shadow: 0 0 8px var(--cat); flex-shrink: 0; }
  .title { flex: 1; font-weight: 600; color: var(--text-0); font-size: 12.5px; }
  .gpu, .ok, .cached, .bad { display: grid; place-items: center; }
  header :global(svg) { width: 13px; height: 13px; }
  .gpu { color: var(--text-3); }
  .ok { color: var(--ok); }
  .cached { color: var(--warn); }
  .bad { color: var(--err); }
  .io { display: flex; justify-content: space-between; gap: 8px; padding: 6px 0; }
  .ins, .outs { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .outs { align-items: flex-end; }
  .sock { position: relative; display: flex; align-items: center; gap: 6px; height: 22px; padding: 0 12px; }
  .sl { color: var(--text-1); white-space: nowrap; }
  .sl.opt { color: var(--text-2); }
  .st { font-size: 9px; letter-spacing: 0.04em; color: var(--text-3); font-family: var(--font-mono); }
  .params { display: flex; flex-direction: column; gap: 6px; padding: 8px 12px 10px; border-top: 1px solid var(--line-0); }
  .prow { position: relative; }
  .more { display: flex; align-items: center; gap: 4px; align-self: flex-start; border: 0; background: none; color: var(--text-3); font-size: 11px; cursor: pointer; padding: 2px 0; }
  .more :global(svg) { width: 12px; height: 12px; transition: transform var(--t-2); }
  .more:hover { color: var(--text-0); }
  :global(.hdl) {
    width: 11px !important;
    height: 11px !important;
    border: 2px solid #121216 !important;
    transition: transform var(--t-1) var(--ease);
  }
  :global(.hdl:hover) { transform: translate(var(--hx, 0), -50%) scale(1.35) !important; }
  .in :global(.hdl) { left: -6px !important; --hx: -50%; }
  .out :global(.hdl) { right: -6px !important; --hx: 50%; }
  .prow :global(.ph) { left: -18px !important; top: 12px !important; --hx: -50%; }
  .prog { height: 3px; margin: 0 12px 6px; border-radius: 3px; background: rgba(var(--fg-rgb), 0.07); overflow: hidden; }
  .prog span { display: block; height: 100%; background: linear-gradient(90deg, var(--accent-lo), var(--accent-hi)); transform-origin: left; transition: transform 200ms var(--ease-out); }
  .ptxt { padding: 0 12px 8px; font-size: 11px; color: var(--text-2); }
  .preview { display: block; width: calc(100% - 20px); margin: 0 10px 10px; border-radius: 8px; }
  .err { margin: 0 10px 10px; padding: 7px 9px; border-radius: 8px; background: var(--err-bg); color: var(--err); font-size: 11px; line-height: 1.45; cursor: text; }
  .unknown { padding: 10px 12px; color: var(--warn); }
</style>
