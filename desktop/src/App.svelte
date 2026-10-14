<script lang="ts">
  import { onMount } from 'svelte';
  import Sidebar from './lib/shell/Sidebar.svelte';
  import StatusBar from './lib/shell/StatusBar.svelte';
  import Onboarding from './lib/shell/Onboarding.svelte';
  import Toaster from './lib/ui/Toaster.svelte';
  import DialogHost from './lib/ui/DialogHost.svelte';
  import Spinner from './lib/ui/Spinner.svelte';
  import Workspace from './lib/views/Workspace.svelte';
  import Images from './lib/views/Images.svelte';
  import Videos from './lib/views/Videos.svelte';
  import Chat from './lib/views/Chat.svelte';
  import Library from './lib/views/Library.svelte';
  import Models from './lib/views/Models.svelte';
  import Settings from './lib/views/Settings.svelte';
  import { conn, initConnection } from './lib/stores/connection.svelte';
  import { prefs, persistPrefs, type View } from './lib/stores/prefs.svelte';
  import { loadJobs, wireJobEvents } from './lib/stores/jobs.svelte';
  import { loadModels, wireModelEvents } from './lib/stores/models.svelte';
  import { loadProjects, wireProjectEvents } from './lib/stores/projects.svelte';

  const order: View[] = ['workspace', 'images', 'videos', 'chat', 'library', 'models', 'settings'];
  let visited = $state<Record<string, boolean>>({ [prefs.view]: true });
  let loadedFor = '';

  $effect(() => {
    visited[prefs.view] = true;
  });

  // (Re)load engine data whenever we come online with a (new) server.
  $effect(() => {
    const key = `${conn.state}:${conn.activeId}`;
    if (conn.state === 'online' && loadedFor !== key) {
      loadedFor = key;
      Promise.allSettled([loadJobs(), loadModels(), loadProjects()]);
    }
  });

  onMount(() => {
    wireJobEvents();
    wireModelEvents();
    wireProjectEvents();
    initConnection();
  });

  function keys(e: KeyboardEvent) {
    if (!(e.ctrlKey || e.metaKey)) return;
    const n = Number(e.key);
    if (n >= 1 && n <= order.length && !e.shiftKey && !e.altKey) {
      prefs.view = order[n - 1];
      persistPrefs();
      e.preventDefault();
    } else if (e.key.toLowerCase() === 'b' && !e.shiftKey) {
      prefs.sidebarCollapsed = !prefs.sidebarCollapsed;
      persistPrefs();
      e.preventDefault();
    }
  }
</script>

<svelte:window onkeydown={keys} />

{#if conn.state === 'booting'}
  <div class="boot"><Spinner size={22} /></div>
{:else if conn.state === 'unconfigured'}
  <Onboarding />
{:else}
  <div class="shell" class:collapsed={prefs.sidebarCollapsed}>
    <Sidebar />
    <main>
      {#if visited.workspace}<section class="view" class:hidden={prefs.view !== 'workspace'}><Workspace /></section>{/if}
      {#if visited.images}<section class="view" class:hidden={prefs.view !== 'images'}><Images active={prefs.view === 'images'} /></section>{/if}
      {#if visited.videos}<section class="view" class:hidden={prefs.view !== 'videos'}><Videos active={prefs.view === 'videos'} /></section>{/if}
      {#if visited.chat}<section class="view" class:hidden={prefs.view !== 'chat'}><Chat active={prefs.view === 'chat'} /></section>{/if}
      {#if visited.library}<section class="view" class:hidden={prefs.view !== 'library'}><Library active={prefs.view === 'library'} /></section>{/if}
      {#if visited.models}<section class="view" class:hidden={prefs.view !== 'models'}><Models active={prefs.view === 'models'} /></section>{/if}
      {#if visited.settings}<section class="view" class:hidden={prefs.view !== 'settings'}><Settings /></section>{/if}
    </main>
    <StatusBar />
  </div>
{/if}

<Toaster />
<DialogHost />

<style>
  .boot { height: 100%; display: grid; place-items: center; }
  .shell {
    display: grid;
    grid-template-columns: var(--sidebar-w) 1fr;
    grid-template-rows: 1fr var(--statusbar-h);
    height: 100%;
    transition: grid-template-columns var(--t-3) var(--ease);
  }
  .shell.collapsed { grid-template-columns: var(--sidebar-w-collapsed) 1fr; }
  main {
    position: relative;
    min-width: 0;
    min-height: 0;
    background: var(--bg-0);
    border-top-left-radius: var(--r-xl);
    border-left: 1px solid var(--line-0);
    border-top: 1px solid var(--line-0);
    overflow: hidden;
  }
  .view { position: absolute; inset: 0; display: flex; flex-direction: column; animation: fade-in var(--t-2) var(--ease); }
  .view.hidden { display: none; }
</style>
