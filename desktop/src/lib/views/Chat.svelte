<script lang="ts">
  import { ArrowUp, Download, FileJson, FolderInput, MessageSquarePlus, MessagesSquare, Paperclip, Pin, PinOff, Power, Search, Settings2, Square, Trash2, Type, Upload, X, FileText, History, Code2 } from '@lucide/svelte';
  import { invoke } from '@tauri-apps/api/core';
  import { open as openDialog, save as saveDialog } from '@tauri-apps/plugin-dialog';
  import { tick } from 'svelte';
  import { api, qs, streamChat } from '../api/client';
  import { isTauri, mediaUrl } from '../api/transport';
  import type { Attachment, ChatEvent, ChatParams, Conversation, Message } from '../api/types';
  import { deepestLeaf, pathTo, siblings } from '../chat/tree';
  import MessageView from '../chat/MessageView.svelte';
  import { models, loadModels } from '../stores/models.svelte';
  import { prefs, persistPrefs } from '../stores/prefs.svelte';
  import { destination, projects } from '../stores/projects.svelte';
  import { toast, toastError } from '../stores/toast.svelte';
  import Button from '../ui/Button.svelte';
  import Empty from '../ui/Empty.svelte';
  import Field from '../ui/Field.svelte';
  import IconButton from '../ui/IconButton.svelte';
  import Menu, { type MenuItem } from '../ui/Menu.svelte';
  import Modal from '../ui/Modal.svelte';
  import Select from '../ui/Select.svelte';
  import Slider from '../ui/Slider.svelte';
  import Spinner from '../ui/Spinner.svelte';
  import CodePanel from '../chat/CodePanel.svelte';
  import { CODE_SYSTEM_PROMPT, extractBlocks } from '../chat/code';
  import { convRequest, paneKey } from '../stores/panes.svelte';
  import TextArea from '../ui/TextArea.svelte';
  import TextInput from '../ui/TextInput.svelte';
  import Toggle from '../ui/Toggle.svelte';
  import { confirmDialog, promptDialog } from '../ui/dialogs.svelte';
  import { ago, bytes, mib } from '../util/format';

  let { active, paneId, variant = 'chat' }: { active: boolean; paneId: string; variant?: 'chat' | 'code' } = $props();
  const isCode = variant === 'code';
  const convKey = `sarness.${paneKey(paneId, 'conv')}`;
  const modelKey = `sarness.${paneKey(paneId, 'model')}`;
  const store = {
    get(k: string) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k: string, v: string | null) { try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch { /* ignore */ } },
  };
  let pickedRef = $state<string | null>(store.get(modelKey));
  let listOpen = $state(false);
  let width = $state(900);
  const split = $derived(isCode && width >= 720);

  let list = $state<Conversation[]>([]);
  let q = $state('');
  let conv = $state<Conversation | null>(null);
  let msgs = $state<Message[]>([]);
  let input = $state('');
  let pending = $state<Attachment[]>([]);
  let streamingId = $state<string | null>(null);
  let statusText = $state('');
  let abort: AbortController | null = null;
  let scroller: HTMLDivElement | undefined = $state();
  let composerEl: HTMLTextAreaElement | null = $state(null);
  let settingsOpen = $state(false);
  let menu = $state({ open: false, x: 0, y: 0, items: [] as MenuItem[] });
  let loadedList = false;
  let uploading = $state(false);
  let stick = true;

  const modelRef = $derived(conv?.model_ref ?? pickedRef ?? prefs.lastChatModel ?? models.chatModels[0]?.ref ?? null);
  const chatModel = $derived(models.chatModels.find((m) => m.ref === modelRef));
  const path = $derived(pathTo(msgs, conv?.active_leaf_id ?? null));
  const blocks = $derived(isCode ? extractBlocks(path) : []);
  const llm = $derived(models.llm);
  const localLoaded = $derived(chatModel?.local && llm?.state === 'ready' && `local:${llm.model_id}` === modelRef);
  const pinned = $derived(list.filter((c) => c.pinned));
  const others = $derived(list.filter((c) => !c.pinned));

  $effect(() => {
    if (active && !loadedList) {
      loadedList = true;
      refreshList();
      const saved = store.get(convKey);
      if (saved) openConv(saved, true);
      if (!models.chatModels.length) loadModels().catch(() => {});
    }
  });

  let seenRequest = convRequest.n;
  $effect(() => {
    if (convRequest.n !== seenRequest) {
      seenRequest = convRequest.n;
      if (convRequest.paneId === paneId && convRequest.convId) openConv(convRequest.convId);
    }
  });

  async function refreshList() {
    try {
      list = await api.get<Conversation[]>(`/v1/chat/conversations${qs({ q, project_id: prefs.projectId })}`);
    } catch (e) {
      toastError(e, 'Could not load conversations');
    }
  }

  let searchTimer: ReturnType<typeof setTimeout>;
  $effect(() => {
    void q;
    void prefs.projectId;
    clearTimeout(searchTimer);
    if (loadedList) searchTimer = setTimeout(refreshList, 220);
  });

  async function openConv(id: string, restoring = false) {
    if (streamingId) return;
    listOpen = false;
    try {
      const c = await api.get<Conversation>(`/v1/chat/conversations/${id}`);
      msgs = c.messages ?? [];
      conv = c;
      store.set(convKey, c.id);
      stick = true;
      await tick();
      scrollBottom(true);
      composerEl?.focus();
    } catch (e) {
      if (restoring) store.set(convKey, null);
      else toastError(e);
    }
  }

  async function newChat() {
    if (streamingId) return;
    store.set(convKey, null);
    listOpen = false;
    conv = null;
    msgs = [];
    input = '';
    pending = [];
    await tick();
    composerEl?.focus();
  }

  async function ensureConv(): Promise<Conversation> {
    if (conv) return conv;
    const c = await api.post<Conversation>('/v1/chat/conversations', {
      model_ref: modelRef,
      ...(isCode ? { system_prompt: CODE_SYSTEM_PROMPT, title: 'Code session' } : {}),
      ...destination(),
    });
    conv = { ...c, messages: [] };
    store.set(convKey, c.id);
    msgs = [];
    list = [c, ...list];
    return conv;
  }

  function scrollBottom(force = false) {
    if (!scroller) return;
    if (force || stick) scroller.scrollTop = scroller.scrollHeight;
  }

  function onScroll() {
    if (!scroller) return;
    stick = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 80;
  }

  async function generate(body: Record<string, unknown>) {
    if (!modelRef) return toast('warning', 'Install or choose a chat model first');
    const c = await ensureConv();
    abort = new AbortController();
    statusText = '';
    stick = true;
    try {
      await streamChat(`/v1/chat/conversations/${c.id}/generate`, { model_ref: modelRef, ...body }, (ev: ChatEvent) => onEvent(c.id, ev), abort.signal);
    } catch (e) {
      toastError(e, 'Chat failed');
    } finally {
      streamingId = null;
      statusText = '';
      abort = null;
      refreshList();
    }
  }

  function onEvent(cid: string, ev: ChatEvent) {
    if (!conv || conv.id !== cid) return;
    if (ev.type === 'user_message') {
      msgs = [...msgs, ev.message];
      conv.active_leaf_id = ev.message.id;
    } else if (ev.type === 'assistant_start') {
      msgs = [...msgs, ev.message];
      conv.active_leaf_id = ev.message.id;
      streamingId = ev.message.id;
    } else if (ev.type === 'delta') {
      const m = msgs.find((x) => x.id === streamingId);
      if (m) {
        m.content += ev.content;
        if (ev.reasoning) m.reasoning = (m.reasoning ?? '') + ev.reasoning;
      }
      statusText = '';
      tick().then(() => scrollBottom());
    } else if (ev.type === 'status') {
      statusText = ev.text;
    } else if (ev.type === 'title') {
      conv.title = ev.title;
    } else if (ev.type === 'done') {
      msgs = msgs.map((x) => (x.id === ev.message.id ? ev.message : x));
    } else if (ev.type === 'error') {
      toast('error', 'Model error', ev.message);
    }
    tick().then(() => scrollBottom());
  }

  async function send() {
    const text = input.trim();
    if ((!text && !pending.length) || streamingId) return;
    if (pending.some((a) => a.mime.startsWith('image/')) && !chatModel?.vision) {
      return toast('warning', 'This model cannot read images', 'Choose a vision model such as Gemma 4 E4B, or remove the image.');
    }
    const parent = path.length ? path[path.length - 1].id : null;
    const atts = pending.map((a) => a.id);
    input = '';
    pending = [];
    await generate({ mode: 'send', content: text, parent_id: parent, attachments: atts, params: conv?.params ?? {} });
  }

  async function stop() {
    if (conv) api.post(`/v1/chat/conversations/${conv.id}/stop`).catch(() => {});
    abort?.abort();
  }

  async function regenerate(m: Message) {
    if (streamingId || !m.parent_id) return;
    await generate({ mode: 'regenerate', parent_id: m.parent_id, params: conv?.params ?? {} });
  }

  async function editMessage(m: Message, text: string) {
    if (streamingId || !text.trim()) return;
    await generate({ mode: 'edit', edit_of: m.id, content: text.trim(), attachments: m.attachments.map((a) => a.id), params: conv?.params ?? {} });
  }

  async function switchBranch(id: string) {
    if (!conv) return;
    const leaf = deepestLeaf(msgs, id);
    conv.active_leaf_id = leaf;
    api.patch(`/v1/chat/conversations/${conv.id}`, { active_leaf_id: leaf }).catch(() => {});
  }

  async function setModel(ref: string | null) {
    if (!ref) return;
    pickedRef = ref;
    store.set(modelKey, ref);
    prefs.lastChatModel = ref;
    persistPrefs();
    if (conv) {
      conv.model_ref = ref;
      api.patch(`/v1/chat/conversations/${conv.id}`, { model_ref: ref }).catch(() => {});
    }
  }

  async function loadModel() {
    if (!chatModel?.local) return;
    try {
      await api.post('/v1/llm/load', { model_id: chatModel.ref.slice(6), ctx: conv?.params?.ctx, gpu_layers: conv?.params?.gpu_layers });
    } catch (e) {
      toastError(e, 'Could not load model');
    }
  }

  async function unloadModel() {
    try {
      await api.post('/v1/llm/unload');
    } catch (e) {
      toastError(e);
    }
  }

  async function attach(files: FileList | File[] | null | undefined) {
    if (!files) return;
    uploading = true;
    try {
      for (const f of Array.from(files)) {
        const r = await api.upload(f, f.name);
        pending = [...pending, { id: r.id, name: f.name, mime: r.mime, size: r.size, url: r.url }];
      }
    } catch (e) {
      toastError(e, 'Attachment failed');
    } finally {
      uploading = false;
    }
  }

  function paste(e: ClipboardEvent) {
    const files = Array.from(e.clipboardData?.files ?? []);
    if (files.length) {
      e.preventDefault();
      attach(files);
    }
  }

  function convMenu(e: MouseEvent, c: Conversation) {
    e.preventDefault();
    menu = {
      open: true, x: e.clientX, y: e.clientY, items: [
        { label: 'Rename', icon: Type, run: () => rename(c) },
        { label: c.pinned ? 'Unpin' : 'Pin', icon: c.pinned ? PinOff : Pin, run: () => patchConv(c, { pinned: c.pinned ? 0 : 1 }) },
        { label: 'Move to current project', icon: FolderInput, disabled: !prefs.projectId, run: () => patchConv(c, destination()) },
        { label: 'Export JSON', icon: FileJson, run: () => exportConv(c, 'json') },
        { label: 'Export Markdown', icon: Download, run: () => exportConv(c, 'md') },
        { separator: true },
        { label: 'Delete', icon: Trash2, danger: true, run: () => removeConv(c) },
      ],
    };
  }

  async function patchConv(c: Conversation, patch: Partial<Conversation>) {
    await api.patch(`/v1/chat/conversations/${c.id}`, patch);
    if (conv?.id === c.id) Object.assign(conv, patch);
    refreshList();
  }

  async function rename(c: Conversation) {
    const t = await promptDialog('Rename conversation', c.title, { confirmLabel: 'Rename' });
    if (t) patchConv(c, { title: t });
  }

  async function removeConv(c: Conversation) {
    if (!(await confirmDialog(`Delete “${c.title}”?`, 'The conversation and all its branches are permanently deleted.', { danger: true, confirmLabel: 'Delete' }))) return;
    await api.del(`/v1/chat/conversations/${c.id}`);
    if (conv?.id === c.id) newChat();
    refreshList();
  }

  async function exportConv(c: Conversation, fmt: 'json' | 'md') {
    try {
      const data = fmt === 'md'
        ? await api.text(`/v1/chat/conversations/${c.id}/export?format=md`)
        : JSON.stringify(await api.get(`/v1/chat/conversations/${c.id}/export`), null, 2);
      const name = `${c.title.replace(/[^\w.-]+/g, '-').slice(0, 60)}.${fmt === 'md' ? 'md' : 'json'}`;
      if (isTauri) {
        const dest = await saveDialog({ defaultPath: name });
        if (!dest) return;
        await invoke('write_text_file', { dest, contents: data });
        toast('success', 'Conversation exported', dest);
      } else {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([data]));
        a.download = name;
        a.click();
      }
    } catch (e) {
      toastError(e, 'Export failed');
    }
  }

  async function importConv() {
    try {
      let text: string | null = null;
      if (isTauri) {
        const p = await openDialog({ multiple: false, filters: [{ name: 'Sarness conversation', extensions: ['json'] }] });
        if (!p) return;
        text = await invoke<string>('read_text_file', { path: p });
      } else return;
      const c = await api.post<Conversation>('/v1/chat/import', JSON.parse(text!));
      await refreshList();
      openConv(c.id);
      toast('success', 'Conversation imported');
    } catch (e) {
      toastError(e, 'Import failed');
    }
  }

  // ------------------------------------------------------------- settings
  let draftSystem = $state('');
  let draftParams = $state<ChatParams>({});
  function openSettings() {
    draftSystem = conv?.system_prompt ?? '';
    draftParams = { temperature: 0.7, top_p: 0.95, top_k: 40, min_p: 0.05, repeat_penalty: 1.05, max_tokens: 2048, ctx: chatModel?.default_ctx ?? 8192, gpu_layers: 999, ...(conv?.params ?? {}) };
    settingsOpen = true;
  }
  async function saveSettings() {
    const c = await ensureConv();
    await api.patch(`/v1/chat/conversations/${c.id}`, { system_prompt: draftSystem, params: draftParams });
    c.system_prompt = draftSystem;
    c.params = { ...draftParams };
    settingsOpen = false;
    if (localLoaded && (llm?.ctx !== draftParams.ctx || llm?.gpu_layers !== draftParams.gpu_layers)) {
      toast('info', 'Context or GPU layers changed', 'The model will reload with the new settings on the next message.');
    }
  }

  const modelOptions = $derived(models.chatModels.map((m) => ({
    value: m.ref as string | null,
    label: m.name,
    group: m.local ? 'On your server' : m.provider,
    hint: [m.vision ? 'vision' : 'text', m.vram_mb ? `~${mib(m.vram_mb)} VRAM` : null, m.size ? bytes(m.size) : null].filter(Boolean).join(' · '),
  })));
</script>

<div class="chat" bind:clientWidth={width}>
  {#if listOpen}
  <aside class="convs">
    <div class="ch">
      <Button variant="secondary" block onclick={newChat}><MessageSquarePlus />New chat</Button>
      <IconButton label="Import conversation" onclick={importConv}><Upload /></IconButton>
    </div>
    <div class="search"><TextInput bind:value={q} placeholder="Search conversations" size="sm">{#snippet icon()}<Search />{/snippet}</TextInput></div>
    <div class="clist">
      {#if pinned.length}
        <div class="sect">Pinned</div>
        {#each pinned as c (c.id)}
          <button class="citem" class:on={conv?.id === c.id} onclick={() => openConv(c.id)} oncontextmenu={(e) => convMenu(e, c)}>
            <Pin /><span class="ct truncate">{c.title}</span><span class="cd">{ago(c.updated_at)}</span>
          </button>
        {/each}
      {/if}
      {#if others.length}<div class="sect">{prefs.projectId ? projects.list.find((p) => p.id === prefs.projectId)?.name ?? 'Project' : 'Recent'}</div>{/if}
      {#each others as c (c.id)}
        <button class="citem" class:on={conv?.id === c.id} onclick={() => openConv(c.id)} oncontextmenu={(e) => convMenu(e, c)}>
          <span class="ct truncate">{c.title}</span><span class="cd">{ago(c.updated_at)}</span>
        </button>
      {/each}
      {#if !list.length}<p class="faint empty">{q ? 'No matches' : 'No conversations yet'}</p>{/if}
    </div>
  </aside>
  <button class="scrim" aria-label="Close history" onclick={() => (listOpen = false)}></button>
  {/if}

  <section class="thread" class:withcode={split}>
    <header>
      <IconButton label="Conversation history" onclick={() => (listOpen = !listOpen)}><History /></IconButton>
      <div class="title truncate">{conv?.title ?? (isCode ? 'New code session' : 'New conversation')}</div>
      <div class="spacer"></div>
      <div class="msel"><Select value={modelRef} options={modelOptions} size="sm" onchange={setModel} placeholder="Choose a model" /></div>
      {#if chatModel?.local}
        {#if llm?.state === 'loading' && `local:${llm.model_id}` === modelRef}
          <span class="mstate"><Spinner size={12} />Loading</span>
        {:else if localLoaded}
          <button class="mstate ok" onclick={unloadModel} title="Unload from GPU"><span class="dot"></span>Loaded · ctx {llm?.ctx}<Power /></button>
        {:else}
          <button class="mstate" onclick={loadModel} title="Load into GPU memory now (otherwise loads on first message)"><Power />Load</button>
        {/if}
      {/if}
      <IconButton label="Chat settings · system prompt, sampling, context" onclick={openSettings}><Settings2 /></IconButton>
    </header>

    <div class="scroll" bind:this={scroller} onscroll={onScroll}>
      <div class="inner">
        {#if !path.length}
          <Empty icon={MessagesSquare} title={models.chatModels.length ? 'Start a conversation' : 'No chat models yet'}
            body={models.chatModels.length ? `${chatModel?.name ?? 'Your model'} runs on your own server. Messages, branches and edits are saved automatically.` : 'Install a GGUF model (Qwen3 4B is a great 12 GB default) from Models to start chatting.'}>
            {#if !models.chatModels.length}<Button variant="primary" onclick={() => { prefs.view = 'models'; persistPrefs(); }}>Browse models</Button>{/if}
          </Empty>
        {/if}
        {#each path as m (m.id)}
          <MessageView {m} sibs={siblings(msgs, m)} streaming={m.id === streamingId} modelName={models.chatModels.find((x) => x.ref === m.model_ref)?.name}
            onswitch={switchBranch} onregenerate={() => regenerate(m)} onedit={(t) => editMessage(m, t)} />
        {/each}
        {#if statusText}<div class="status"><Spinner size={13} />{statusText}</div>{/if}
      </div>
    </div>

    <div class="composer-wrap">
      <div class="composer" class:drag={false} role="group"
        ondragover={(e) => e.preventDefault()} ondrop={(e) => { e.preventDefault(); attach(e.dataTransfer?.files); }}>
        {#if pending.length}
          <div class="pend">
            {#each pending as a (a.id)}
              <span class="pchip">
                {#if a.mime.startsWith('image/')}<img src={mediaUrl(a.url)} alt="" />{:else}<FileText />{/if}
                <span class="truncate">{a.name}</span>
                <button onclick={() => (pending = pending.filter((x) => x.id !== a.id))} aria-label="Remove"><X /></button>
              </span>
            {/each}
          </div>
        {/if}
        <TextArea bind:el={composerEl} bind:value={input} minRows={1} maxRows={12} placeholder={chatModel ? `Message ${chatModel.name}…` : 'Choose a model to start'}
          onkeydown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }} onpaste={paste} />
        <div class="crow">
          <label class="attach" title={chatModel?.vision ? 'Attach images or text files' : 'Attach text files (this model cannot read images)'}>
            {#if uploading}<Spinner size={14} />{:else}<Paperclip />{/if}
            <input type="file" multiple hidden accept={chatModel?.vision ? 'image/*,.txt,.md,.json,.csv' : '.txt,.md,.json,.csv'} onchange={(e) => attach((e.currentTarget as HTMLInputElement).files)} />
          </label>
          <span class="faint small">{chatModel?.vision ? 'Vision model · images supported' : 'Text model'}{conv?.params?.temperature !== undefined ? ` · temp ${conv.params.temperature}` : ''}</span>
          <div class="spacer"></div>
          {#if streamingId}
            <button class="send stop" onclick={stop} aria-label="Stop"><Square /></button>
          {:else}
            <button class="send" onclick={send} disabled={!input.trim() && !pending.length} aria-label="Send"><ArrowUp /></button>
          {/if}
        </div>
      </div>
    </div>
  </section>
  {#if split}
    <section class="codecol"><CodePanel {blocks} onattach={attach} /></section>
  {/if}
</div>

<Menu bind:open={menu.open} bind:x={menu.x} bind:y={menu.y} bind:items={menu.items} />

<Modal bind:open={settingsOpen} title="Chat settings" subtitle="Applies to this conversation" width={560}>
  <div class="settings">
    <Field label="System prompt"><TextArea bind:value={draftSystem} minRows={3} maxRows={10} placeholder="You are a helpful assistant…" /></Field>
    <Toggle checked={draftParams.thinking !== false} onchange={(v) => (draftParams.thinking = v)} label="Allow thinking" hint="Reasoning models think before answering (shown collapsed). Turn off for faster, direct replies. Ignored by models without a thinking mode." />
    <div class="g2">
      <Slider bind:value={draftParams.temperature!} min={0} max={2} step={0.05} label="Temperature" format={(v) => v.toFixed(2)} />
      <Slider bind:value={draftParams.top_p!} min={0.05} max={1} step={0.01} label="Top P" format={(v) => v.toFixed(2)} />
      <Slider bind:value={draftParams.top_k!} min={0} max={200} label="Top K" />
      <Slider bind:value={draftParams.min_p!} min={0} max={0.5} step={0.01} label="Min P" format={(v) => v.toFixed(2)} />
      <Slider bind:value={draftParams.repeat_penalty!} min={1} max={1.5} step={0.01} label="Repeat penalty" format={(v) => v.toFixed(2)} />
      <Slider bind:value={draftParams.max_tokens!} min={64} max={16384} step={64} label="Max response tokens" />
    </div>
    {#if chatModel?.local}
      <div class="g2">
        <Slider bind:value={draftParams.ctx!} min={2048} max={Math.min(chatModel.context_max ?? 32768, 131072)} step={1024} label="Context length" format={(v) => `${(v / 1024).toFixed(0)}K tokens`} />
        <Slider bind:value={draftParams.gpu_layers!} min={0} max={999} label="GPU layers" format={(v) => (v >= 999 ? 'All' : String(v))} />
      </div>
      <p class="faint small">Larger contexts use more VRAM (the KV cache). Changing context or GPU layers reloads the model.</p>
    {/if}
  </div>
  {#snippet footer()}
    <Button variant="ghost" onclick={() => (settingsOpen = false)}>Cancel</Button>
    <Button variant="primary" onclick={saveSettings}>Save</Button>
  {/snippet}
</Modal>

<style>
  .chat { position: relative; display: flex; height: 100%; min-height: 0; }
  .convs { position: absolute; z-index: 20; left: 0; top: 0; bottom: 0; width: min(300px, 86%); display: flex; flex-direction: column; background: var(--bg-1); border-right: 1px solid var(--line-1); box-shadow: var(--shadow-3); animation: rise-in var(--t-2) var(--ease); }
  .scrim { position: absolute; inset: 0; z-index: 19; border: 0; background: var(--scrim); cursor: default; }
  .codecol { flex: 0 0 46%; min-width: 300px; border-left: 1px solid var(--line-1); min-height: 0; }
  .ch { display: flex; gap: 6px; padding: 14px 12px 8px; }
  .search { padding: 0 12px 8px; }
  .clist { flex: 1; overflow-y: auto; padding: 4px 8px 12px; }
  .sect { padding: 10px 8px 4px; font-size: 10.5px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-3); }
  .citem { display: flex; align-items: center; gap: 8px; width: 100%; padding: 8px 10px; border: 0; border-radius: var(--r-md); background: none; color: var(--text-1); cursor: pointer; text-align: left; transition: background var(--t-1); }
  .citem:hover { background: rgba(var(--fg-rgb), 0.045); color: var(--text-0); }
  .citem.on { background: var(--select-bg); color: var(--text-0); }
  .citem :global(svg) { width: 12px; height: 12px; color: var(--lavender); flex-shrink: 0; }
  .ct { flex: 1; font-size: var(--fs-md); }
  .cd { font-size: 10.5px; color: var(--text-3); white-space: nowrap; }
  .empty { padding: 16px 10px; font-size: var(--fs-sm); }
  .thread { flex: 1; min-width: 0; display: flex; flex-direction: column; min-height: 0; }
  header { display: flex; align-items: center; gap: 8px; height: 44px; padding: 0 10px 0 8px; border-bottom: 1px solid var(--line-0); }
  .title { font-weight: 600; font-size: var(--fs-lg); min-width: 0; }
  .spacer { flex: 1; }
  .msel { width: min(260px, 42%); }
  .mstate { display: inline-flex; align-items: center; gap: 6px; height: 26px; padding: 0 10px; border-radius: var(--r-full); border: 1px solid var(--line-1); background: var(--bg-2); color: var(--text-2); font-size: var(--fs-xs); cursor: pointer; white-space: nowrap; }
  .mstate :global(svg) { width: 12px; height: 12px; }
  .mstate.ok { color: var(--ok); border-color: rgba(95, 211, 155, 0.25); }
  .mstate .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--ok); box-shadow: 0 0 6px var(--ok); }
  .scroll { flex: 1; overflow-y: auto; min-height: 0; }
  .inner { max-width: 860px; margin: 0 auto; padding: 20px 18px 16px; display: flex; flex-direction: column; gap: 14px; }
  .status { display: flex; gap: 8px; align-items: center; color: var(--text-2); font-size: var(--fs-sm); padding-left: 40px; }
  .composer-wrap { padding: 0 14px 14px; }
  .composer {
    max-width: 860px;
    margin: 0 auto;
    padding: 8px 8px 8px 10px;
    border-radius: 20px;
    background: var(--bg-2);
    border: 1px solid var(--line-1);
    box-shadow: var(--shadow-2);
    transition: border-color var(--t-1), box-shadow var(--t-2);
  }
  .composer:focus-within { border-color: var(--select-line); box-shadow: 0 0 0 4px rgba(var(--accent-rgb), 0.1), var(--shadow-2); }
  .composer :global(textarea) { background: transparent; border: 0; box-shadow: none !important; font-size: 14.5px; padding: 8px 6px; }
  .crow { display: flex; align-items: center; gap: 8px; padding: 0 2px; }
  .attach { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 10px; color: var(--text-2); cursor: pointer; }
  .attach:hover { background: rgba(var(--fg-rgb), 0.06); color: var(--text-0); }
  .attach :global(svg) { width: 17px; height: 17px; }
  .small { font-size: var(--fs-xs); }
  .send { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 12px; border: 0; background: var(--accent); color: var(--text-inv); cursor: pointer; transition: transform var(--t-1), opacity var(--t-1); box-shadow: var(--shadow-1); }
  .send:hover:not(:disabled) { transform: translateY(-1px); }
  .send:disabled { opacity: 0.35; cursor: default; box-shadow: none; }
  .send :global(svg) { width: 17px; height: 17px; }
  .send.stop { background: var(--bg-5); box-shadow: none; }
  .send.stop :global(svg) { width: 13px; height: 13px; fill: currentColor; }
  .pend { display: flex; flex-wrap: wrap; gap: 6px; padding: 4px 2px 6px; }
  .pchip { display: inline-flex; align-items: center; gap: 6px; max-width: 220px; padding: 4px 6px 4px 4px; border-radius: var(--r-md); background: var(--bg-4); font-size: var(--fs-xs); }
  .pchip img { width: 28px; height: 28px; object-fit: cover; border-radius: 6px; }
  .pchip :global(svg) { width: 14px; height: 14px; flex-shrink: 0; }
  .pchip button { border: 0; background: none; color: var(--text-3); cursor: pointer; display: grid; }
  .settings { display: flex; flex-direction: column; gap: 16px; }
  .g2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 18px; }
</style>
