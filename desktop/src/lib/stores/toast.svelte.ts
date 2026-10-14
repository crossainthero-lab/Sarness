export type ToastKind = 'info' | 'success' | 'warning' | 'error';

export interface Toast {
  id: number;
  kind: ToastKind;
  title: string;
  body?: string;
  action?: { label: string; run: () => void };
  timeout: number;
}

export const toasts = $state<Toast[]>([]);
let seq = 0;

export function toast(kind: ToastKind, title: string, body?: string, opts: Partial<Pick<Toast, 'action' | 'timeout'>> = {}) {
  const t: Toast = { id: ++seq, kind, title, body, timeout: opts.timeout ?? (kind === 'error' ? 7000 : 3800), action: opts.action };
  toasts.push(t);
  if (toasts.length > 5) toasts.shift();
  if (t.timeout > 0) setTimeout(() => dismiss(t.id), t.timeout);
  return t.id;
}

export function dismiss(id: number) {
  const i = toasts.findIndex((t) => t.id === id);
  if (i >= 0) toasts.splice(i, 1);
}

export function toastError(e: unknown, title = 'Something went wrong') {
  const msg = e instanceof Error ? e.message : String(e);
  toast('error', title, msg);
}
