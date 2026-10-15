import DOMPurify from 'dompurify';
import { Marked } from 'marked';
import hljs from 'highlight.js/lib/core';
import bash from 'highlight.js/lib/languages/bash';
import c from 'highlight.js/lib/languages/c';
import cpp from 'highlight.js/lib/languages/cpp';
import css from 'highlight.js/lib/languages/css';
import diff from 'highlight.js/lib/languages/diff';
import go from 'highlight.js/lib/languages/go';
import java from 'highlight.js/lib/languages/java';
import javascript from 'highlight.js/lib/languages/javascript';
import json from 'highlight.js/lib/languages/json';
import markdown from 'highlight.js/lib/languages/markdown';
import python from 'highlight.js/lib/languages/python';
import rust from 'highlight.js/lib/languages/rust';
import sql from 'highlight.js/lib/languages/sql';
import typescript from 'highlight.js/lib/languages/typescript';
import xml from 'highlight.js/lib/languages/xml';
import yaml from 'highlight.js/lib/languages/yaml';
import ini from 'highlight.js/lib/languages/ini';
import dockerfile from 'highlight.js/lib/languages/dockerfile';

const langs: Record<string, any> = { bash, c, cpp, css, diff, go, java, javascript, json, markdown, python, rust, sql, typescript, xml, yaml, ini, dockerfile };
for (const [k, v] of Object.entries(langs)) hljs.registerLanguage(k, v);
hljs.registerAliases(['sh', 'shell', 'zsh', 'console'], { languageName: 'bash' });
hljs.registerAliases(['js', 'jsx', 'mjs'], { languageName: 'javascript' });
hljs.registerAliases(['ts', 'tsx'], { languageName: 'typescript' });
hljs.registerAliases(['py'], { languageName: 'python' });
hljs.registerAliases(['rs'], { languageName: 'rust' });
hljs.registerAliases(['html', 'svelte', 'vue'], { languageName: 'xml' });
hljs.registerAliases(['yml'], { languageName: 'yaml' });
hljs.registerAliases(['toml'], { languageName: 'ini' });
hljs.registerAliases(['md'], { languageName: 'markdown' });

function escape(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

const md = new Marked({ gfm: true, breaks: false });
md.use({
  renderer: {
    code({ text, lang }) {
      const language = (lang ?? '').trim().split(/\s+/)[0].toLowerCase();
      let html: string;
      try {
        html = language && hljs.getLanguage(language) ? hljs.highlight(text, { language }).value : escape(text);
      } catch {
        html = escape(text);
      }
      const label = language || 'text';
      return `<div class="codeblock"><div class="cb-head"><span>${escape(label)}</span><button type="button" class="cb-copy">Copy</button></div><pre><code class="hljs">${html}</code></pre></div>`;
    },
    link({ href, title, text }) {
      const t = title ? ` title="${escape(title)}"` : '';
      return `<a href="${escape(href)}"${t} target="_blank" rel="noopener noreferrer">${text}</a>`;
    },
  },
});

export function renderMarkdown(src: string): string {
  const raw = md.parse(src ?? '', { async: false }) as string;
  return DOMPurify.sanitize(raw, { ADD_ATTR: ['target'], FORBID_TAGS: ['style', 'iframe', 'form', 'input'] });
}

/** Delegated click handler for code-block copy buttons. */
export function handleCodeCopy(e: MouseEvent) {
  const btn = (e.target as HTMLElement).closest('.cb-copy') as HTMLButtonElement | null;
  if (!btn) return;
  const code = btn.closest('.codeblock')?.querySelector('code')?.textContent ?? '';
  navigator.clipboard.writeText(code).then(() => {
    btn.textContent = 'Copied';
    setTimeout(() => (btn.textContent = 'Copy'), 1400);
  });
}

/** Syntax-highlight code to sanitised HTML (used by the code panel). */
export function highlightCode(code: string, lang: string): string {
  const language = lang.toLowerCase();
  try {
    if (language && hljs.getLanguage(language)) return hljs.highlight(code, { language }).value;
  } catch {
    /* fall through */
  }
  return escape(code);
}
