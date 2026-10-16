<script lang="ts">
  import { invoke } from '@tauri-apps/api/core';
  import { save as saveDialog } from '@tauri-apps/plugin-dialog';
  import { Check, Copy, Download, FolderOpen, Paperclip } from '@lucide/svelte';
  import { isTauri } from '../api/transport';
  import { toast, toastError } from '../stores/toast.svelte';
  import Button from '../ui/Button.svelte';
  import Segmented from '../ui/Segmented.svelte';
  import { highlightCode } from './markdown';
  import { isTextFile, lineDiff, previousVersion, type CodeBlock } from './code';

  let { blocks, onattach }: { blocks: CodeBlock[]; onattach: (files: File[]) => Promise<void> | void } = $props();

  let tab = $state<'code' | 'diff' | 'files'>('code');
  let picked = $state<string | null>(null);
  let copied = $state(false);
  let files = $state<{ file: File; path: string; on: boolean }[]>([]);
  let attaching = $state(false);

  const index = $derived.by(() => {
    const i = blocks.findIndex((b) => b.key === picked);
    return i >= 0 ? i : blocks.length - 1;
  });
  const cur = $derived(blocks[index] ?? null);
  const prev = $derived(previousVersion(blocks, index));
  const diff = $derived(cur && prev ? lineDiff(prev.code, cur.code) : []);
  const html = $derived(cur ? highlightCode(cur.code, cur.lang) : '');
  const label = (b: CodeBlock, i: number) => `${b.filename ?? `snippet ${i + 1}`} · ${b.lang || 'text'}`;

  function copy() {
    if (!cur) return;
    navigator.clipboard.writeText(cur.code);
    copied = true;
    setTimeout(() => (copied = false), 1300);
  }

  async function exportCode() {
    if (!cur) return;
    const name = cur.filename?.split('/').pop() ?? `snippet.${cur.lang || 'txt'}`;
    try {
      if (isTauri) {
        const dest = await saveDialog({ defaultPath: name });
        if (!dest) return;
        await invoke('write_text_file', { dest, contents: cur.code });
        toast('success', 'Saved', dest);
      } else {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([cur.code]));
        a.download = name;
        a.click();
      }
    } catch (e) {
      toastError(e, 'Export failed');
    }
  }

  function folder(e: Event) {
    const list = Array.from((e.currentTarget as HTMLInputElement).files ?? []);
    files = list
      .filter((f) => isTextFile(f.name) && f.size <= 256 * 1024)
      .filter((f) => !/(^|\/)(node_modules|\.git|target|dist|build|__pycache__)\//.test((f as any).webkitRelativePath ?? ''))
      .slice(0, 400)
      .map((file) => ({ file, path: (file as any).webkitRelativePath || file.name, on: false }))
      .sort((a, b) => a.path.localeCompare(b.path));
    if (list.length && !files.length) toast('info', 'No supported text files found in that folder');
  }

  async function attachSelected() {
    const chosen = files.filter((f) => f.on).map((f) => f.file);
    if (!chosen.length) return;
    attaching = true;
    try {
      await onattach(chosen);
      files = files.map((f) => ({ ...f, on: false }));
    } finally {
      attaching = false;
    }
  }
  const nOn = $derived(files.filter((f) => f.on).length);
</script>

<div class="panel">
  <div class="bar">
    <Segmented value={tab} onchange={(v) => (tab = v)} items={[{ value: 'code', label: 'Code' }, { value: 'diff', label: 'Changes' }, { value: 'files', label: 'Files' }]} />
  </div>

  {#if tab !== 'files'}
    {#if !cur}
      <div class="empty">
        <p>Code from the conversation appears here.</p>
        <p class="faint">Ask for a function, a file or a revision. Each fenced block becomes a file you can copy, export or compare.</p>
      </div>
    {:else}
      <div class="sel">
        <select aria-label="Code block" value={cur.key} onchange={(e) => (picked = (e.currentTarget as HTMLSelectElement).value)}>
          {#each blocks as b, i (b.key)}<option value={b.key}>{label(b, i)}</option>{/each}
        </select>
        <Button size="sm" variant="ghost" onclick={copy}>{#if copied}<Check />Copied{:else}<Copy />Copy{/if}</Button>
        <Button size="sm" variant="ghost" onclick={exportCode}><Download />Export</Button>
      </div>
      {#if tab === 'code'}
        <pre class="code selectable"><code class="hljs">{@html html}</code></pre>
      {:else if !prev}
        <div class="empty"><p>No earlier version of this file to compare.</p><p class="faint">Revise the code in chat and the changes appear here.</p></div>
      {:else}
        <div class="diff selectable" role="table" aria-label="Changes since the previous version">
          {#each diff as l, i (i)}
            <div class="dl {l.kind}"><span class="sign">{l.kind === 'add' ? '+' : l.kind === 'del' ? '−' : ' '}</span><span class="tx">{l.text}</span></div>
          {/each}
        </div>
      {/if}
    {/if}
  {:else}
    <div class="files">
      <label class="pick">
        <FolderOpen />Choose a project folder
        <input type="file" hidden multiple webkitdirectory onchange={folder} />
      </label>
      <p class="faint note">Files are read in this window and only uploaded to your server when you attach them. Sarness cannot browse your disk on its own, and the model cannot run code.</p>
      {#if files.length}
        <div class="flist">
          {#each files as f (f.path)}
            <label class="frow"><input type="checkbox" bind:checked={f.on} /><span class="truncate">{f.path}</span></label>
          {/each}
        </div>
        <Button variant="primary" size="sm" disabled={!nOn} loading={attaching} onclick={attachSelected}><Paperclip />Attach {nOn || ''} file{nOn === 1 ? '' : 's'} to message</Button>
      {/if}
    </div>
  {/if}
</div>

<style>
  .panel { display: flex; flex-direction: column; height: 100%; min-height: 0; background: var(--bg-1); }
  .bar { padding: 8px 10px; border-bottom: 1px solid var(--line-0); }
  .sel { display: flex; align-items: center; gap: 4px; padding: 6px 8px; border-bottom: 1px solid var(--line-0); }
  select { flex: 1; min-width: 0; height: 28px; border-radius: var(--r-sm); border: 1px solid var(--line-1); background: var(--bg-0); color: var(--text-0); padding: 0 6px; }
  .code { flex: 1; margin: 0; overflow: auto; padding: 12px 14px; font-size: 12.5px; line-height: 1.55; background: var(--bg-0); }
  .code code { background: none; padding: 0; white-space: pre; }
  .diff { flex: 1; overflow: auto; font-family: var(--font-mono); font-size: 12.5px; background: var(--bg-0); padding: 6px 0; }
  .dl { display: flex; padding: 0 12px; white-space: pre; min-width: max-content; }
  .dl .sign { width: 18px; flex-shrink: 0; color: var(--text-3); }
  .dl.add { background: var(--ok-bg); }
  .dl.del { background: var(--err-bg); }
  .empty { padding: 28px 20px; display: flex; flex-direction: column; gap: 8px; color: var(--text-1); font-size: var(--fs-sm); }
  .files { padding: 12px; display: flex; flex-direction: column; gap: 10px; min-height: 0; flex: 1; }
  .pick { display: inline-flex; align-items: center; gap: 8px; padding: 9px 12px; border: 1px dashed var(--line-2); border-radius: var(--r-md); cursor: pointer; color: var(--text-1); font-weight: 550; }
  .pick:hover { border-color: var(--accent); color: var(--text-0); }
  .pick :global(svg) { width: 15px; height: 15px; }
  .note { font-size: var(--fs-xs); }
  .flist { flex: 1; overflow: auto; border: 1px solid var(--line-0); border-radius: var(--r-md); background: var(--bg-0); }
  .frow { display: flex; align-items: center; gap: 8px; padding: 4px 10px; font-size: var(--fs-sm); cursor: pointer; }
  .frow:hover { background: var(--accent-ghost); }
</style>
