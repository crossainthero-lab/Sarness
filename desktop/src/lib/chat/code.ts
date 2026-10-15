// Code-block extraction and line diffing for the coding workflow. Pure
// functions, no UI: unit-tested in code.test.ts.

export interface CodeBlock {
  key: string; // stable id: messageId:index
  messageId: string;
  lang: string;
  filename: string | null;
  code: string;
}

const FENCE = /^```([^\n`]*)\n([\s\S]*?)^```[ \t]*$/gm;

function nameFrom(info: string, code: string): { lang: string; filename: string | null } {
  const tokens = info.trim().split(/\s+/).filter(Boolean);
  const lang = (tokens[0] ?? '').toLowerCase();
  let filename: string | null = null;
  for (const t of tokens.slice(lang ? 1 : 0)) {
    const m = t.match(/^(?:title|file|filename|path)=["']?([^"']+)["']?$/i);
    const cand = m ? m[1] : t;
    if (/[./]/.test(cand) && !/^https?:/.test(cand)) {
      filename = cand;
      break;
    }
  }
  if (!filename && lang && /[./]/.test(lang) && /\.\w+$/.test(lang)) {
    filename = tokens[0];
  }
  if (!filename) {
    const first = code.split('\n', 1)[0] ?? '';
    const m = first.match(/^(?:\/\/|#|--|\/\*|<!--)\s*(?:file(?:name)?|path):?\s*([^\s*]+)/i);
    if (m) filename = m[1];
  }
  return { lang: filename && /[./]/.test(lang) ? (filename.split('.').pop() ?? '') : lang, filename };
}

export function extractBlocks(messages: { id: string; role: string; content: string }[]): CodeBlock[] {
  const out: CodeBlock[] = [];
  for (const m of messages) {
    if (m.role !== 'assistant' || !m.content) continue;
    let i = 0;
    for (const match of m.content.matchAll(FENCE)) {
      const { lang, filename } = nameFrom(match[1], match[2]);
      out.push({ key: `${m.id}:${i++}`, messageId: m.id, lang, filename, code: match[2].replace(/\n$/, '') });
    }
  }
  return out;
}

export interface DiffLine {
  kind: 'same' | 'add' | 'del';
  text: string;
}

/** Myers-lite LCS line diff, capped so huge files stay responsive. */
export function lineDiff(a: string, b: string, cap = 2000): DiffLine[] {
  const x = a.split('\n');
  const y = b.split('\n');
  if (x.length > cap || y.length > cap) {
    return [...x.map((t) => ({ kind: 'del' as const, text: t })), ...y.map((t) => ({ kind: 'add' as const, text: t }))];
  }
  const n = x.length;
  const m = y.length;
  const dp: Uint32Array[] = Array.from({ length: n + 1 }, () => new Uint32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = x[i] === y[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const out: DiffLine[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (x[i] === y[j]) {
      out.push({ kind: 'same', text: x[i] });
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      out.push({ kind: 'del', text: x[i++] });
    } else {
      out.push({ kind: 'add', text: y[j++] });
    }
  }
  while (i < n) out.push({ kind: 'del', text: x[i++] });
  while (j < m) out.push({ kind: 'add', text: y[j++] });
  return out;
}

export function previousVersion(blocks: CodeBlock[], index: number): CodeBlock | null {
  const cur = blocks[index];
  if (!cur) return null;
  for (let i = index - 1; i >= 0; i--) {
    const b = blocks[i];
    if (cur.filename ? b.filename === cur.filename : b.lang === cur.lang && !b.filename) return b;
  }
  return null;
}

const TEXT_EXT = /\.(txt|md|json|ya?ml|toml|ini|cfg|csv|py|js|jsx|mjs|ts|tsx|svelte|vue|html|css|scss|rs|go|java|c|h|cpp|hpp|cs|rb|php|sh|bash|sql|xml|lock|env|dockerfile|makefile|gradle|kt|swift)$/i;
export function isTextFile(name: string): boolean {
  return TEXT_EXT.test(name) || /(^|\/)(Dockerfile|Makefile|README)$/.test(name);
}

export const CODE_SYSTEM_PROMPT =
  'You are Sarness Code, a careful senior software engineer. Answer with correct, minimal, idiomatic code. ' +
  'When you produce a file, put it in a fenced block whose info string is the language followed by the file path, ' +
  'for example ```ts src/app.ts. When revising a file, return the complete updated file rather than a fragment, ' +
  'then list the changes briefly. You cannot execute code or access the user\'s filesystem; only the files they ' +
  'attach are visible to you. Say so plainly if you are unsure instead of guessing.';
