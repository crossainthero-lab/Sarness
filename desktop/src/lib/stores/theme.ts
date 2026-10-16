export type Theme = 'light' | 'dark' | 'system';

let media: MediaQueryList | null = null;
let listener: (() => void) | null = null;

/** Apply a theme to the document; `system` follows the OS and keeps following it. */
export function applyTheme(t: Theme) {
  const root = document.documentElement;
  media ??= window.matchMedia('(prefers-color-scheme: dark)');
  if (listener) media.removeEventListener('change', listener);
  listener = null;
  if (t === 'system') {
    const apply = () => (root.dataset.theme = media!.matches ? 'dark' : 'light');
    listener = apply;
    media.addEventListener('change', apply);
    apply();
  } else {
    root.dataset.theme = t;
  }
}
