<script lang="ts">
  import { Boxes, ChevronsUpDown, Clapperboard, FolderPlus, Image, LayoutDashboard, Library, MessagesSquare, PanelLeftClose, PanelLeftOpen, Plus, Settings } from '@lucide/svelte';
  import logo from '../assets/logo.svg';
  import { prefs, persistPrefs, type View } from '../stores/prefs.svelte';
  import { activeJobs } from '../stores/jobs.svelte';
  import { createProject, currentFolder, currentProject, folderTree, projects, selectProject } from '../stores/projects.svelte';
  import { tooltip } from '../ui/tooltip';
  import { promptDialog } from '../ui/dialogs.svelte';
  import { toastError } from '../stores/toast.svelte';
  import Menu, { type MenuItem } from '../ui/Menu.svelte';

  const nav: { id: View; label: string; icon: any; key: string }[] = [
    { id: 'workspace', label: 'Workspace', icon: LayoutDashboard, key: '1' },
    { id: 'images', label: 'Images', icon: Image, key: '2' },
    { id: 'videos', label: 'Videos', icon: Clapperboard, key: '3' },
    { id: 'chat', label: 'Chat', icon: MessagesSquare, key: '4' },
    { id: 'library', label: 'Library', icon: Library, key: '5' },
    { id: 'models', label: 'Models', icon: Boxes, key: '6' },
  ];

  const imgActive = $derived(activeJobs('image').length);
  const vidActive = $derived(activeJobs('video').length);
  const collapsed = $derived(prefs.sidebarCollapsed);

  function go(v: View) {
    prefs.view = v;
    persistPrefs();
  }

  let menu = $state({ open: false, x: 0, y: 0, items: [] as MenuItem[] });
  function openProjects(e: MouseEvent) {
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const items: MenuItem[] = [
      { label: 'All work (no project)', run: () => selectProject(null) },
      { separator: true },
    ];
    for (const p of projects.list) {
      items.push({ label: p.name, run: () => selectProject(p.id) });
      for (const f of flatten(folderTree(p))) {
        items.push({ label: `${'   '.repeat(f.depth + 1)}${f.name}`, run: () => selectProject(p.id, f.id) });
      }
    }
    items.push({ separator: true }, { label: 'New project…', icon: FolderPlus, run: newProject });
    menu = { open: true, x: r.left + 6, y: r.bottom + 4, items };
  }
  function flatten(nodes: any[]): any[] {
    return nodes.flatMap((n) => [n, ...flatten(n.children)]);
  }
  async function newProject() {
    const name = await promptDialog('New project', '', { placeholder: 'Project name', confirmLabel: 'Create' });
    if (!name) return;
    try {
      const p = await createProject(name);
      selectProject(p.id);
    } catch (e) {
      toastError(e, 'Could not create project');
    }
  }
  const projectLabel = $derived(currentProject()?.name ?? 'All work');
  const folderLabel = $derived(currentFolder()?.name ?? null);
</script>

<aside class="sidebar" class:collapsed>
  <div class="brand">
    <img src={logo} alt="" width="28" height="28" />
    {#if !collapsed}<span class="word">Sarness</span>{/if}
  </div>

  <button class="project" onclick={openProjects} use:tooltip={collapsed ? `Project: ${projectLabel}` : null}>
    <span class="dot" style:background={currentProject() ? 'var(--accent-hi)' : 'var(--text-3)'}></span>
    {#if !collapsed}
      <span class="ptext">
        <span class="pname truncate">{projectLabel}</span>
        {#if folderLabel}<span class="pfolder truncate">{folderLabel}</span>{/if}
      </span>
      <ChevronsUpDown />
    {/if}
  </button>

  <nav>
    {#each nav as item (item.id)}
      {@const count = item.id === 'images' ? imgActive : item.id === 'videos' ? vidActive : 0}
      <button class="item" class:active={prefs.view === item.id} onclick={() => go(item.id)} use:tooltip={collapsed ? `${item.label}  ·  Ctrl+${item.key}` : null}>
        <item.icon />
        {#if !collapsed}<span class="label">{item.label}</span>{/if}
        {#if count}<span class="count" class:mini={collapsed}>{collapsed ? '' : count}</span>{/if}
      </button>
    {/each}
  </nav>

  <div class="spacer"></div>

  <div class="bottom">
    <button class="item" class:active={prefs.view === 'settings'} onclick={() => go('settings')} use:tooltip={collapsed ? 'Settings  ·  Ctrl+7' : null}>
      <Settings />
      {#if !collapsed}<span class="label">Settings</span>{/if}
    </button>
    <button class="item subtle" onclick={() => { prefs.sidebarCollapsed = !collapsed; persistPrefs(); }} use:tooltip={collapsed ? 'Expand sidebar  ·  Ctrl+B' : null}>
      {#if collapsed}<PanelLeftOpen />{:else}<PanelLeftClose /><span class="label">Collapse</span>{/if}
    </button>
  </div>
</aside>

<Menu bind:open={menu.open} bind:x={menu.x} bind:y={menu.y} bind:items={menu.items} />

<style>
  .sidebar {
    grid-row: 1 / span 2;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px 10px 10px;
    background: var(--bg-1);
    min-width: 0;
    overflow: hidden;
  }
  .brand { display: flex; align-items: center; gap: 10px; padding: 4px 6px 10px; height: 44px; }
  .brand img { flex-shrink: 0; filter: drop-shadow(0 4px 12px rgba(124, 58, 237, 0.35)); }
  .word { font-weight: 650; font-size: 16px; letter-spacing: -0.02em; background: linear-gradient(180deg, #fff, #cfc6f6); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .project {
    display: flex;
    align-items: center;
    gap: 9px;
    margin-bottom: 8px;
    padding: 8px 9px;
    border-radius: var(--r-md);
    border: 1px solid var(--line-1);
    background: var(--bg-2);
    color: var(--text-1);
    cursor: pointer;
    text-align: left;
    min-height: 40px;
    transition: border-color var(--t-1), background var(--t-1);
  }
  .project:hover { border-color: var(--line-2); background: var(--bg-3); }
  .project :global(svg) { width: 14px; height: 14px; color: var(--text-3); flex-shrink: 0; }
  .dot { width: 8px; height: 8px; border-radius: 3px; flex-shrink: 0; margin-left: 2px; }
  .ptext { display: flex; flex-direction: column; flex: 1; min-width: 0; line-height: 1.25; }
  .pname { font-weight: 600; font-size: var(--fs-md); color: var(--text-0); }
  .pfolder { font-size: var(--fs-xs); color: var(--text-3); }
  nav, .bottom { display: flex; flex-direction: column; gap: 2px; }
  .item {
    position: relative;
    display: flex;
    align-items: center;
    gap: 11px;
    height: 36px;
    padding: 0 10px;
    border: 0;
    border-radius: var(--r-md);
    background: transparent;
    color: var(--text-2);
    font-weight: 550;
    cursor: pointer;
    white-space: nowrap;
    transition: background var(--t-1) var(--ease), color var(--t-1) var(--ease);
  }
  .item :global(svg) { width: 18px; height: 18px; flex-shrink: 0; transition: transform var(--t-2) var(--ease); }
  .item:hover { background: rgba(255, 255, 255, 0.045); color: var(--text-0); }
  .item.active { background: var(--select-bg); color: var(--text-0); }
  .item.active :global(svg) { color: var(--lavender); }
  .item.active::before {
    content: '';
    position: absolute;
    left: -10px;
    top: 9px;
    bottom: 9px;
    width: 3px;
    border-radius: 0 3px 3px 0;
    background: var(--accent-hi);
    box-shadow: 0 0 12px rgba(167, 139, 250, 0.7);
  }
  .label { flex: 1; text-align: left; }
  .count {
    min-width: 20px;
    height: 18px;
    padding: 0 6px;
    border-radius: 9px;
    background: var(--accent);
    color: white;
    font-size: 11px;
    font-weight: 700;
    display: grid;
    place-items: center;
    animation: pulse-ring 1.8s infinite;
  }
  .count.mini { position: absolute; top: 7px; right: 7px; min-width: 8px; width: 8px; height: 8px; padding: 0; }
  .subtle { color: var(--text-3); }
  .spacer { flex: 1; }
  .collapsed .item { justify-content: center; padding: 0; }
  .collapsed .project { justify-content: center; padding: 8px 0; }
  .collapsed .brand { justify-content: center; padding: 4px 0 10px; }
</style>
