// Lightweight tooltip action: one shared element, positioned above/below the target.
let el: HTMLDivElement | null = null;
let showTimer: ReturnType<typeof setTimeout> | null = null;

function ensure() {
  if (el) return el;
  el = document.createElement('div');
  el.className = 'sarness-tooltip';
  el.setAttribute('role', 'tooltip');
  document.body.appendChild(el);
  return el;
}

function show(target: HTMLElement, text: string) {
  const t = ensure();
  t.textContent = text;
  t.style.opacity = '0';
  t.style.display = 'block';
  const r = target.getBoundingClientRect();
  const tr = t.getBoundingClientRect();
  let top = r.top - tr.height - 8;
  if (top < 6) top = r.bottom + 8;
  let left = r.left + r.width / 2 - tr.width / 2;
  left = Math.max(6, Math.min(left, window.innerWidth - tr.width - 6));
  t.style.transform = `translate(${Math.round(left)}px, ${Math.round(top)}px)`;
  requestAnimationFrame(() => (t.style.opacity = '1'));
}

function hide() {
  if (showTimer) clearTimeout(showTimer);
  if (el) {
    el.style.opacity = '0';
    el.style.display = 'none';
  }
}

export function tooltip(node: HTMLElement, text: string | null) {
  let current = text;
  const enter = () => {
    if (!current) return;
    if (showTimer) clearTimeout(showTimer);
    showTimer = setTimeout(() => show(node, current!), 380);
  };
  node.addEventListener('mouseenter', enter);
  node.addEventListener('mouseleave', hide);
  node.addEventListener('mousedown', hide);
  return {
    update(t: string | null) {
      current = t;
    },
    destroy() {
      node.removeEventListener('mouseenter', enter);
      node.removeEventListener('mouseleave', hide);
      node.removeEventListener('mousedown', hide);
      hide();
    },
  };
}
