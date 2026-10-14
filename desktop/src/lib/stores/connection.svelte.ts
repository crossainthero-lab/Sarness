// Server connection: profiles, the desktop proxy, live event stream, health.

import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { api } from '../api/client';
import { devTransport, isTauri, proxyTransport, setTransport, transport, wsUrl } from '../api/transport';
import type { EngineEvent, LiveStats, SystemInfo } from '../api/types';

export interface SshOptions {
  user: string;
  host: string;
  port: number;
  key_path?: string | null;
}

export interface Profile {
  id: string;
  name: string;
  host: string;
  port: number;
  scheme: 'http' | 'https';
  mode: 'direct' | 'ssh';
  ssh?: SshOptions | null;
  has_token: boolean;
}

export interface TestResult {
  ok: boolean;
  stage: string;
  message: string;
  latency_ms: number | null;
  health: Record<string, unknown> | null;
  system: SystemInfo | null;
}

export type ConnState = 'booting' | 'unconfigured' | 'connecting' | 'online' | 'offline';

export const conn = $state({
  state: 'booting' as ConnState,
  profiles: [] as Profile[],
  activeId: null as string | null,
  system: null as SystemInfo | null,
  stats: null as LiveStats | null,
  lastError: null as string | null,
  wsConnected: false,
  tunnel: null as string | null,
  lastEventAt: 0,
});

export const activeProfile = () => conn.profiles.find((p) => p.id === conn.activeId) ?? null;

type Handler = (e: EngineEvent) => void;
const handlers = new Map<string, Set<Handler>>();

/** Subscribe to engine events by type ("job.updated") or prefix ("job.*"). */
export function onEvent(type: string, fn: Handler): () => void {
  if (!handlers.has(type)) handlers.set(type, new Set());
  handlers.get(type)!.add(fn);
  return () => handlers.get(type)?.delete(fn);
}

function dispatch(e: EngineEvent) {
  conn.lastEventAt = Date.now();
  handlers.get(e.type)?.forEach((h) => h(e));
  const prefix = e.type.split('.')[0] + '.*';
  handlers.get(prefix)?.forEach((h) => h(e));
  handlers.get('*')?.forEach((h) => h(e));
}

// ------------------------------------------------------------- websocket
let ws: WebSocket | null = null;
let wsTimer: ReturnType<typeof setTimeout> | null = null;
let watchdog: ReturnType<typeof setInterval> | null = null;
let backoff = 1000;
let wantWs = false;

function openWs() {
  if (!wantWs || !transport().base) return;
  try {
    ws?.close();
  } catch {
    /* ignore */
  }
  const sock = new WebSocket(wsUrl('/v1/events'));
  ws = sock;
  sock.onopen = () => {
    trace('event stream connected');
    backoff = 1000;
    conn.wsConnected = true;
    conn.lastEventAt = Date.now();
    if (conn.state === 'offline') {
      conn.state = 'online';
      refreshSystem();
      dispatch({ type: 'connection.restored', data: {} });
    }
  };
  sock.onmessage = (m) => {
    try {
      const ev = JSON.parse(m.data);
      if (ev.type === 'system.stats') conn.stats = ev.data;
      dispatch(ev);
    } catch {
      /* ignore malformed */
    }
  };
  sock.onclose = () => {
    if (ws !== sock) return;
    conn.wsConnected = false;
    if (wantWs) {
      if (conn.state === 'online') conn.state = 'offline';
      scheduleWs();
    }
  };
  sock.onerror = () => sock.close();
}

function scheduleWs() {
  if (wsTimer) clearTimeout(wsTimer);
  wsTimer = setTimeout(openWs, backoff);
  backoff = Math.min(backoff * 1.7, 15000);
}

function startWs() {
  wantWs = true;
  openWs();
  if (watchdog) clearInterval(watchdog);
  // Heartbeats arrive every 15s; silence for 40s means a dead connection.
  watchdog = setInterval(() => {
    if (conn.wsConnected && Date.now() - conn.lastEventAt > 40000) {
      conn.wsConnected = false;
      ws?.close();
      conn.state = 'offline';
      scheduleWs();
    }
  }, 5000);
}

function stopWs() {
  wantWs = false;
  if (wsTimer) clearTimeout(wsTimer);
  if (watchdog) clearInterval(watchdog);
  ws?.close();
  ws = null;
  conn.wsConnected = false;
}

// ---------------------------------------------------------------- actions
function trace(msg: string) {
  (window as any).__sarnessLog?.('info', msg);
}

export async function refreshSystem() {
  try {
    conn.system = await api.get<SystemInfo>('/v1/system');
    trace(`system info loaded from ${conn.system.hardware.hostname}`);
    conn.lastError = null;
    if (conn.state !== 'online') conn.state = 'online';
  } catch (e) {
    conn.lastError = (e as Error).message;
    (window as any).__sarnessLog?.('warn', `system request failed: ${conn.lastError}`);
    if (conn.state === 'online' || conn.state === 'connecting') conn.state = 'offline';
  }
  return conn.system;
}

export async function loadProfiles() {
  if (!isTauri) return;
  const store = await invoke<{ profiles: Profile[]; active: string | null }>('list_profiles');
  conn.profiles = store.profiles;
  conn.activeId = store.active;
}

export async function initConnection() {
  if (!isTauri) {
    const dev = devTransport();
    if (!dev) {
      conn.state = 'unconfigured';
      return;
    }
    setTransport(dev);
    conn.profiles = [{ id: 'dev', name: 'Development engine', host: dev.base, port: 0, scheme: 'http', mode: 'direct', has_token: true }];
    conn.activeId = 'dev';
    conn.state = 'connecting';
    await refreshSystem();
    startWs();
    return;
  }
  await loadProfiles();
  listen<{ state: string; error?: string }>('tunnel-status', (e) => {
    conn.tunnel = e.payload.state;
    if (e.payload.state === 'up') openWs();
  });
  const info = await invoke<{ url: string; session: string; connected: boolean }>('proxy_info');
  setTransport(proxyTransport(info.url, info.session, info.connected));
  if (!conn.activeId || !conn.profiles.length) {
    conn.state = 'unconfigured';
    return;
  }
  await connect(conn.activeId);
}

export async function connect(id: string) {
  conn.state = 'connecting';
  conn.lastError = null;
  stopWs();
  if (!isTauri) return;
  try {
    const info = await invoke<{ url: string; session: string; connected: boolean }>('connect', { id });
    setTransport(proxyTransport(info.url, info.session, info.connected));
    conn.activeId = id;
    await refreshSystem();
    startWs();
    if ((conn.state as ConnState) !== 'online') conn.state = 'offline';
  } catch (e) {
    conn.lastError = String(e);
    conn.state = 'offline';
    // Keep trying in the background; the engine may simply be starting.
    startWs();
  }
}

export async function disconnect() {
  stopWs();
  if (isTauri) await invoke('disconnect');
  conn.state = conn.profiles.length ? 'offline' : 'unconfigured';
  conn.system = null;
}

export async function saveProfile(profile: Profile, token?: string) {
  const saved = await invoke<Profile>('save_profile', { profile, token: token || null });
  await loadProfiles();
  return saved;
}

export async function deleteProfile(id: string) {
  await invoke('delete_profile', { id });
  await loadProfiles();
  if (!conn.profiles.length) {
    stopWs();
    conn.state = 'unconfigured';
  }
}

export async function testConnection(profile: Profile, token?: string) {
  return invoke<TestResult>('test_connection', { profile, token: token || null });
}

export async function reconnectNow() {
  if (conn.activeId) await connect(conn.activeId);
}
