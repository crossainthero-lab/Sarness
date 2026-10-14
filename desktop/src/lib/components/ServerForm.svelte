<script lang="ts">
  import { CircleCheck, CircleX, Download, KeyRound, Radar, Server, Terminal } from '@lucide/svelte';
  import { invoke } from '@tauri-apps/api/core';
  import { connect, saveProfile, testConnection, type Profile, type TestResult } from '../stores/connection.svelte';
  import { toast, toastError } from '../stores/toast.svelte';
  import Button from '../ui/Button.svelte';
  import Field from '../ui/Field.svelte';
  import Segmented from '../ui/Segmented.svelte';
  import TextInput from '../ui/TextInput.svelte';
  import Badge from '../ui/Badge.svelte';
  import Spinner from '../ui/Spinner.svelte';
  import SystemPanel from './SystemPanel.svelte';
  import InstallWizard from './InstallWizard.svelte';

  let { profile = null, onsaved }: { profile?: Profile | null; onsaved?: (p: Profile) => void } = $props();

  let form = $state<Profile>(
    profile ? structuredClone($state.snapshot(profile)) as Profile : {
      id: '', name: 'AI Server', host: '', port: 8742, scheme: 'http', mode: 'direct',
      ssh: { user: '', host: '', port: 22, key_path: '' }, has_token: false,
    },
  );
  if (!form.ssh) form.ssh = { user: '', host: '', port: 22, key_path: '' };
  let token = $state('');
  let testing = $state(false);
  let saving = $state(false);
  let result = $state<TestResult | null>(null);
  let discovering = $state(false);
  let candidates = $state<any[] | null>(null);
  let installOpen = $state(false);

  function normalized(): Profile {
    const p = $state.snapshot(form) as Profile;
    p.host = p.host.trim().replace(/^https?:\/\//, '').replace(/\/.*$/, '');
    p.port = Number(p.port) || 8742;
    if (p.mode === 'ssh' && p.ssh) {
      p.ssh.port = Number(p.ssh.port) || 22;
      p.ssh.host = p.ssh.host.trim();
      p.ssh.user = p.ssh.user.trim();
      if (!p.host) p.host = '127.0.0.1';
    } else {
      p.ssh = null;
    }
    return p;
  }

  async function test() {
    testing = true;
    result = null;
    try {
      result = await testConnection(normalized(), token);
    } catch (e) {
      result = { ok: false, stage: 'input', message: String(e), latency_ms: null, health: null, system: null };
    } finally {
      testing = false;
    }
  }

  async function save(andConnect = true) {
    saving = true;
    try {
      const saved = await saveProfile(normalized(), token);
      form.id = saved.id;
      token = '';
      if (andConnect) await connect(saved.id);
      toast('success', andConnect ? `Connected to ${saved.name}` : 'Server saved');
      onsaved?.(saved);
    } catch (e) {
      toastError(e, 'Could not save server');
    } finally {
      saving = false;
    }
  }

  async function discover() {
    discovering = true;
    try {
      candidates = await invoke<any[]>('discover_servers');
    } catch (e) {
      toastError(e, 'Discovery failed');
    } finally {
      discovering = false;
    }
  }

  function pick(c: any) {
    form.host = c.dns_name && c.source === 'tailscale' ? c.dns_name : c.address;
    if (c.source === 'local') form.host = '127.0.0.1';
    form.name = c.source === 'local' ? 'This computer' : c.name;
    form.mode = 'direct';
    if (!form.ssh!.host) form.ssh!.host = c.dns_name ?? c.address;
  }

  function installed(res: { host: string; port: number; profile: Profile }) {
    form = res.profile;
    installOpen = false;
    token = '';
    test();
  }
</script>

<div class="form">
  <div class="discover">
    <div class="row">
      <Radar />
      <div class="col" style="gap:0;flex:1">
        <strong>Find servers</strong>
        <span class="muted small">Checks this computer and your online Tailscale devices for a Sarness Engine. No port scanning.</span>
      </div>
      <Button size="sm" onclick={discover} loading={discovering}>Scan</Button>
    </div>
    {#if candidates}
      <div class="cands">
        {#each candidates.filter((c) => c.online) as c (c.address)}
          <button class="cand" onclick={() => pick(c)}>
            <Server />
            <span class="cname truncate">{c.name}</span>
            <span class="faint truncate mono">{c.dns_name ?? c.address}</span>
            {#if c.engine}<Badge tone="ok" dot>Engine {c.engine.engine_version}</Badge>{:else}<Badge>{c.os ?? 'device'}</Badge>{/if}
          </button>
        {/each}
        {#if !candidates.some((c) => c.online)}<p class="muted small">No online devices found.</p>{/if}
      </div>
    {/if}
  </div>

  <div class="grid2">
    <Field label="Name"><TextInput bind:value={form.name} placeholder="AI Server" /></Field>
    <Field label="Connection">
      <Segmented bind:value={form.mode} full items={[{ value: 'direct', label: 'Direct (LAN · Tailscale)' }, { value: 'ssh', label: 'SSH tunnel' }]} />
    </Field>
  </div>

  {#if form.mode === 'ssh'}
    <div class="grid3">
      <Field label="SSH user"><TextInput bind:value={form.ssh!.user} placeholder="ubuntu" /></Field>
      <Field label="SSH host"><TextInput bind:value={form.ssh!.host} placeholder="ai-server or 100.x.y.z" /></Field>
      <Field label="SSH port"><TextInput bind:value={form.ssh!.port} type="number" /></Field>
    </div>
    <Field label="Private key (optional)" hint="Uses your ssh-agent and ~/.ssh/config by default. Passwords are never stored — Sarness uses key-based SSH only.">
      <TextInput bind:value={form.ssh!.key_path} placeholder="~/.ssh/id_ed25519" mono />
    </Field>
    <div class="grid2">
      <Field label="Engine address on the server" hint="Where the engine listens, as seen from the server."><TextInput bind:value={form.host} placeholder="127.0.0.1" mono /></Field>
      <Field label="Engine port"><TextInput bind:value={form.port} type="number" /></Field>
    </div>
  {:else}
    <div class="grid2 hostport">
      <Field label="Host" hint="LAN IP, Tailscale IP, MagicDNS name (e.g. ai-box.tail1234.ts.net) or 127.0.0.1.">
        <TextInput bind:value={form.host} placeholder="100.101.102.103" mono />
      </Field>
      <Field label="API port"><TextInput bind:value={form.port} type="number" /></Field>
    </div>
  {/if}

  <Field label="API token" hint={form.has_token ? 'A token is stored in your system keyring. Leave empty to keep it.' : 'Printed by “sarness-engine init” on the server. Stored in your system keyring, never in plain config.'}>
    <TextInput bind:value={token} type="password" placeholder={form.has_token ? '••••••••  (stored)' : 'sk-sarness-…'} mono>
      {#snippet icon()}<KeyRound />{/snippet}
    </TextInput>
  </Field>

  <div class="actions">
    {#if form.mode === 'ssh'}
      <Button variant="ghost" onclick={() => (installOpen = true)} disabled={!form.ssh?.user || !form.ssh?.host}><Terminal />Install engine via SSH…</Button>
    {/if}
    <div class="spacer"></div>
    <Button onclick={test} loading={testing} disabled={!form.host && form.mode === 'direct'}>Test connection</Button>
    <Button variant="primary" onclick={() => save(true)} loading={saving} disabled={(!form.host && form.mode === 'direct') || (!token && !form.has_token)}>Save & connect</Button>
  </div>

  {#if testing}
    <div class="result pending"><Spinner /> Testing connection…</div>
  {:else if result}
    <div class="result" class:ok={result.ok} class:bad={!result.ok}>
      <div class="rhead">
        {#if result.ok}<CircleCheck />{:else}<CircleX />{/if}
        <strong>{result.ok ? 'Connected' : 'Connection failed'}</strong>
        {#if result.latency_ms !== null}<span class="faint tnum">{result.latency_ms} ms</span>{/if}
        {#if result.health}<Badge>Engine {String(result.health.engine_version)} · API {String(result.health.api_version)}</Badge>{/if}
      </div>
      {#if !result.ok}<p class="msg selectable">{result.message}</p>{/if}
      {#if result.system}
        <SystemPanel system={result.system} />
        <div class="chips">
          <Badge tone="accent">{result.system.models.installed} models installed</Badge>
          <Badge>{result.system.jobs.running ?? 0} running · {result.system.jobs.queued ?? 0} queued</Badge>
          <Badge tone={result.system.health.status === 'ok' ? 'ok' : 'warn'} dot>Health: {result.system.health.status}</Badge>
        </div>
      {/if}
    </div>
  {/if}
</div>

{#if installOpen}
  <InstallWizard bind:open={installOpen} profile={normalized()} oninstalled={installed} />
{/if}

<style>
  .form { display: flex; flex-direction: column; gap: 16px; }
  .discover { padding: 12px 14px; border-radius: var(--r-lg); background: var(--bg-1); border: 1px solid var(--line-1); display: flex; flex-direction: column; gap: 10px; }
  .discover > .row :global(svg) { width: 18px; height: 18px; color: var(--lavender); }
  .small { font-size: var(--fs-sm); }
  .cands { display: flex; flex-direction: column; gap: 4px; }
  .cand { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: var(--r-md); border: 1px solid transparent; background: var(--bg-2); color: var(--text-1); cursor: pointer; text-align: left; }
  .cand:hover { border-color: var(--select-line); background: var(--select-bg); }
  .cand :global(svg) { width: 15px; height: 15px; color: var(--text-3); flex-shrink: 0; }
  .cname { font-weight: 600; color: var(--text-0); min-width: 100px; }
  .cand .mono { flex: 1; font-size: var(--fs-xs); }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .hostport { grid-template-columns: 1fr 140px; }
  .grid3 { display: grid; grid-template-columns: 1fr 1.4fr 110px; gap: 12px; }
  .actions { display: flex; gap: 8px; align-items: center; }
  .spacer { flex: 1; }
  .result { padding: 14px; border-radius: var(--r-lg); border: 1px solid var(--line-1); background: var(--bg-1); display: flex; flex-direction: column; gap: 12px; animation: rise-in var(--t-3) var(--ease-out); }
  .pending { flex-direction: row; align-items: center; gap: 10px; color: var(--text-2); }
  .ok { border-color: rgba(95, 211, 155, 0.3); }
  .bad { border-color: rgba(244, 113, 116, 0.3); }
  .rhead { display: flex; align-items: center; gap: 8px; }
  .rhead :global(svg) { width: 18px; height: 18px; }
  .ok .rhead :global(svg) { color: var(--ok); }
  .bad .rhead :global(svg) { color: var(--err); }
  .msg { color: var(--text-1); line-height: 1.5; }
  .chips { display: flex; gap: 6px; flex-wrap: wrap; }
</style>
