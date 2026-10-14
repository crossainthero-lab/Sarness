// Promise-based confirm / prompt dialogs rendered by <DialogHost/>.
export interface DialogState {
  kind: 'confirm' | 'prompt';
  title: string;
  body?: string;
  confirmLabel?: string;
  danger?: boolean;
  value?: string;
  placeholder?: string;
  resolve: (v: any) => void;
}

export const dialog = $state<{ current: DialogState | null }>({ current: null });

export function confirmDialog(title: string, body?: string, opts: { confirmLabel?: string; danger?: boolean } = {}): Promise<boolean> {
  return new Promise((resolve) => {
    dialog.current = { kind: 'confirm', title, body, ...opts, resolve };
  });
}

export function promptDialog(title: string, value = '', opts: { body?: string; confirmLabel?: string; placeholder?: string } = {}): Promise<string | null> {
  return new Promise((resolve) => {
    dialog.current = { kind: 'prompt', title, value, ...opts, resolve };
  });
}
