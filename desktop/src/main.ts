import '@fontsource-variable/inter';
import '@fontsource-variable/jetbrains-mono';
import './app.css';
import { mount } from 'svelte';
import App from './App.svelte';
import { isTauri } from './lib/api/transport';

if (isTauri) {
  // Mirror webview errors into the desktop log for diagnostics.
  import('@tauri-apps/api/core').then(({ invoke }) => {
    const send = (level: string, message: string) => invoke('frontend_log', { level, message }).catch(() => {});
    (window as any).__sarnessLog = send;
    window.addEventListener('error', (e) => send('error', `${e.message} @ ${e.filename}:${e.lineno}`));
    window.addEventListener('unhandledrejection', (e) => send('error', `unhandled rejection: ${String(e.reason?.message ?? e.reason)}`));
    send('info', `webview started (${navigator.userAgent})`);
  });
}

const app = mount(App, { target: document.getElementById('app')! });

export default app;
