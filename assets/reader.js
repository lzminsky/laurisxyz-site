/* The reader — lauris.xyz
 *
 * All six articles in one surface. Open from anywhere, move between them
 * without a reload, close and land back exactly where you were.
 *
 * Two principles:
 *
 * 1. ONE RENDERER. tools/build_writing.py is the only thing that renders an
 *    article. This file never builds prose markup from data — it fetches a
 *    static page and transports its <article> onto the screen. The reader
 *    cannot drift from the static page, because it *is* the static page.
 *
 * 2. SELF-CONTAINED. This file carries its own CSS and its own markup, and
 *    reads the six-item index from /assets/shelf.json (generated). A page
 *    adopts the reader with one script tag and nothing else, so there is no
 *    second copy of anything to drift.
 *
 * Progressive enhancement: every trigger is a real <a href>. If this file
 * fails to load, throws, or is disabled, links navigate normally and nothing
 * is lost but the overlay.
 */
(() => {
  'use strict';

  if (!window.DOMParser || !window.history?.pushState || !window.fetch) return;

  const CSS = `
html.reader-open { overflow: hidden; }
body.reader-held { position: fixed; width: 100%; }
.reader { position: fixed; inset: 0; z-index: 60; display: grid; grid-template-rows: auto minmax(0, 1fr); background: var(--paper, #ffffff); }
.reader[hidden] { display: none; }
.rd-bar { display: flex; align-items: center; gap: 20px; padding: 14px 30px 13px; border-bottom: 1px solid var(--rule, #d4ccc0); }
.rd-mark { color: var(--ink, #181713); font: 1.1rem/1 var(--type-mono, ui-monospace, monospace); text-decoration: none; }
.rd-crumb { margin: 0; font-weight: 600; color: var(--ink-muted, #65706d); font: .667rem/1.6 var(--type-mono, ui-monospace, monospace); letter-spacing: .05em; text-transform: uppercase; }
.rd-crumb b { color: var(--ink, #181713); font-weight: 400; }
.rd-hint { margin: 0 0 0 auto; font-weight: 600; color: var(--ink-muted, #65706d); font: .667rem/1.6 var(--type-mono, ui-monospace, monospace); letter-spacing: .05em; text-transform: uppercase; }
.rd-close { min-width: 44px; min-height: 44px; padding: 2px 0 4px; border: 0; border-bottom: 1px solid currentColor; background: none; color: var(--ink-muted, #65706d); cursor: pointer; font: 500 .76rem/1.4 var(--type-body, system-ui, sans-serif); letter-spacing: -.01em; transition: color 160ms; }
.rd-close:hover { color: var(--ink, #011614); }
.rd-main { display: grid; grid-template-columns: 250px minmax(0, 1fr); min-height: 0; }
.rd-rail { padding: 26px 0 26px 30px; border-right: 1px solid var(--rule, #d4ccc0); overflow-y: auto; }
.rd-rail-label { margin: 0 0 10px; font-weight: 600; color: var(--ink-muted, #65706d); font: .667rem/1.6 var(--type-mono, ui-monospace, monospace); letter-spacing: .07em; text-transform: uppercase; }
.rd-rail-item { display: grid; grid-template-columns: 26px minmax(0, 1fr); gap: 3px 10px; min-height: 44px; padding: 9px 18px 10px 0; border-bottom: 1px solid var(--rule, #d7ddda); text-decoration: none; color: inherit; }
.rd-rail-num { font-weight: 600; color: var(--ink-muted, #65706d); font: .667rem/1.7 var(--type-mono, ui-monospace, monospace); letter-spacing: .05em; }
.rd-rail-title { font-size: .86rem; line-height: 1.3; transition: color 160ms; }
.rd-rail-extent { grid-column: 2; color: var(--ink-muted, #65706d); font: .667rem/1.4 var(--type-mono, ui-monospace, monospace); font-variant-numeric: tabular-nums; letter-spacing: .04em; }
.rd-rail-item:hover .rd-rail-title { color: var(--teal, #0e6670); }
.rd-rail-item.is-here .rd-rail-num { font-weight: 600; color: var(--wine, #78384f); }
.rd-rail-item.is-here .rd-rail-title { font-weight: 600; }
.rd-stage { overflow-y: auto; overscroll-behavior: contain; }
.rd-stage:focus { outline: none; }
.rd-stage > article { width: min(1120px, calc(100% - 80px)); margin: 0 auto; padding: 44px 0 96px; }
.rd-stage .art-head { padding-top: 0; }
.rd-stage .shelf { display: none; }
.rd-err { width: min(640px, calc(100% - 60px)); margin: 80px auto; color: var(--ink-soft, #514d47); }
.rd-err a { color: inherit; }
@media (max-width: 1199px) {
  .rd-main { grid-template-columns: 1fr; }
  .rd-rail { display: none; }
  .rd-stage > article { width: calc(100% - 44px); }
}
@media (max-width: 640px) {
  .rd-bar { padding: 12px 20px 11px; gap: 12px; }
  .rd-hint { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .rd-rail-title, .rd-close { transition: none; }
}`;

  const MARKUP = `
<div class="rd-bar">
  <a class="rd-mark" href="/" aria-label="Lauris — home">┐</a>
  <p class="rd-crumb">Lauris / Writing / <b data-crumb></b></p>
  <p class="rd-hint">← → move · esc close</p>
  <button class="rd-close" type="button" data-close>Close ✕</button>
</div>
<div class="rd-main">
  <nav class="rd-rail" aria-label="All writing">
    <p class="rd-rail-label">The writing</p>
    <div data-rail></div>
  </nav>
  <div class="rd-stage" data-stage tabindex="-1"></div>
</div>`;

  let SHELF = [];
  let root, stage, rail, crumb;
  let open = false;
  let current = null;
  let homeScroll = 0;
  let opener = null;
  let homeTitle = document.title;
  const HOME = location.pathname + location.search;
  const cache = new Map();
  const inflight = new Map();
  const indexOf = (slug) => SHELF.findIndex((s) => s.slug === slug);

  /* ── build the surface once, lazily ────────────────────────────────── */

  const mount = () => {
    if (root) return;
    const style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);

    // The article's own styles. We transport its DOM, and DOM without its CSS
    // is not the article. Generated by build_writing.py, so there is exactly
    // one definition of what an article looks like. Already present (and a
    // no-op) on the article pages themselves.
    if (!document.querySelector('link[href="/assets/article.css"]')) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = '/assets/article.css';
      document.head.appendChild(link);
    }

    root = document.createElement('div');
    root.className = 'reader';
    root.id = 'reader';
    root.hidden = true;
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-label', 'Reading');
    root.innerHTML = MARKUP;
    document.body.appendChild(root);

    stage = root.querySelector('[data-stage]');
    rail = root.querySelector('[data-rail]');
    crumb = root.querySelector('[data-crumb]');

    rail.replaceChildren(...SHELF.map((s) => {
      const a = document.createElement('a');
      a.className = 'rd-rail-item';
      a.href = `/writing/${s.slug}/`;
      a.dataset.slug = s.slug;
      const num = document.createElement('span');
      num.className = 'rd-rail-num';
      num.textContent = s.num;
      const title = document.createElement('span');
      title.className = 'rd-rail-title';
      title.textContent = s.title;
      const ext = document.createElement('span');
      ext.className = 'rd-rail-extent';
      ext.textContent = `${s.words.toLocaleString()}w`;
      a.append(num, title, ext);
      return a;
    }));

    root.querySelector('[data-close]').addEventListener('click', () => close());
    stage.addEventListener('scroll', queueMeasure, { passive: true });
  };

  /* ── fetch + transport ─────────────────────────────────────────────── */

  const load = (slug) => {
    if (cache.has(slug)) return Promise.resolve(cache.get(slug));
    if (inflight.has(slug)) return inflight.get(slug);
    const p = fetch(`/writing/${slug}/`, { credentials: 'same-origin' })
      .then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.text(); })
      .then((html) => {
        const article = new DOMParser().parseFromString(html, 'text/html')
          .querySelector('article[data-slug]');
        if (!article) throw new Error('no article');
        cache.set(slug, article);
        inflight.delete(slug);
        return article;
      })
      .catch((err) => { inflight.delete(slug); throw err; });
    inflight.set(slug, p);
    return p;
  };

  const prefetch = (slug) => {
    if (slug && !cache.has(slug) && !inflight.has(slug)) load(slug).catch(() => {});
  };

  /* ── the rule: progress across the prose, not the page ─────────────── */

  let ruleEl = null, bodyEl = null, raf = 0;

  const measure = () => {
    raf = 0;
    if (!ruleEl || !bodyEl || !stage) return;
    // Full when the WRITING ends, not when you reach the bottom of the page.
    const lead = stage.clientHeight * 0.55;
    const travel = bodyEl.offsetHeight - lead;
    const p = travel > 0 ? (stage.scrollTop - bodyEl.offsetTop + lead) / travel : 1;
    ruleEl.style.setProperty('--art-progress', Math.min(1, Math.max(0, p)).toFixed(4));
  };
  const queueMeasure = () => { if (!raf) raf = requestAnimationFrame(measure); };

  /* ── show / open / close ───────────────────────────────────────────── */

  const show = (slug, push) => {
    const article = cache.get(slug);
    if (!article) return;
    stage.replaceChildren(article.cloneNode(true));
    stage.scrollTop = 0;
    current = slug;

    ruleEl = stage.querySelector('.folio-rule');
    bodyEl = stage.querySelector('.art-body');
    measure();

    rail.querySelectorAll('.rd-rail-item').forEach((a) => {
      const here = a.dataset.slug === slug;
      a.classList.toggle('is-here', here);
      here ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current');
    });

    const meta = SHELF[indexOf(slug)];
    if (meta) {
      crumb.textContent = meta.num;
      document.title = `${meta.title} — Lauris`;
    }
    const title = stage.querySelector('.art-title');
    if (title) {
      title.id = 'reader-title';
      root.setAttribute('aria-labelledby', 'reader-title');
      root.removeAttribute('aria-label');
    }
    if (push) history.pushState({ reader: slug }, '', `/writing/${slug}/`);

    const i = indexOf(slug);
    prefetch(SHELF[i - 1]?.slug);
    prefetch(SHELF[i + 1]?.slug);
    stage.focus({ preventScroll: true });
  };

  const openReader = (slug, push = true) => load(slug).then(() => {
    mount();
    if (!open) {
      homeScroll = window.scrollY;
      open = true;
      root.hidden = false;
      document.documentElement.classList.add('reader-open');
      // Hold the page still behind the surface without losing its position.
      document.body.style.top = `-${homeScroll}px`;
      document.body.classList.add('reader-held');
    }
    show(slug, push);
  });

  const close = (push = true) => {
    if (!open) return;
    open = false;
    current = null;
    root.hidden = true;
    document.documentElement.classList.remove('reader-open');
    document.body.classList.remove('reader-held');
    document.body.style.top = '';
    window.scrollTo(0, homeScroll);
    stage.replaceChildren();
    ruleEl = bodyEl = null;
    document.title = homeTitle;
    if (push) history.pushState({}, '', HOME);
    if (opener?.isConnected) opener.focus({ preventScroll: true });
    opener = null;
  };

  /* ── triggers ──────────────────────────────────────────────────────── */

  const slugFor = (a) => {
    const href = a.getAttribute('href');
    if (!href) return null;
    try {
      const u = new URL(href, location.origin);
      if (u.origin !== location.origin) return null;
      const m = u.pathname.match(/^\/writing\/([^/]+)\/?$/);
      return m && indexOf(m[1]) >= 0 ? m[1] : null;
    } catch { return null; }
  };

  document.addEventListener('click', (e) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const a = e.target.closest?.('a[href]');
    if (!a || a.target === '_blank') return;
    // Inside the reader, the article's own "Back to the archive" should leave.
    const slug = slugFor(a);
    if (!slug || slug === current) return;
    e.preventDefault();
    if (!open) opener = a;
    // Anything goes wrong: fall back to a real navigation. Never trap them.
    openReader(slug).catch(() => { location.href = a.href; });
  });

  document.addEventListener('pointerover', (e) => {
    const a = e.target instanceof Element ? e.target.closest('a[href]') : null;
    if (a) prefetch(slugFor(a));
  });
  document.addEventListener('focusin', (e) => {
    const a = e.target instanceof Element ? e.target.closest('a[href]') : null;
    if (a) prefetch(slugFor(a));
  });

  window.addEventListener('popstate', (e) => {
    const slug = e.state?.reader;
    if (slug) openReader(slug, false).catch(() => location.reload());
    else if (open) close(false);
  });
  window.addEventListener('resize', queueMeasure);

  /* ── keyboard ──────────────────────────────────────────────────────── */

  const step = (dir) => {
    const next = SHELF[indexOf(current) + dir];
    if (next) openReader(next.slug).catch(() => {});
  };

  const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';
  const trap = (e) => {
    const items = [...root.querySelectorAll(FOCUSABLE)].filter((el) => el.offsetParent !== null);
    if (!items.length) return;
    const first = items[0], last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  };

  document.addEventListener('keydown', (e) => {
    if (!open || e.metaKey || e.ctrlKey || e.altKey) return;
    const t = e.target;
    if (t instanceof HTMLElement && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
    if (e.key === 'Escape') { e.preventDefault(); close(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); step(-1); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
    else if (e.key === 'Tab') trap(e);
  });

  /* ── init ──────────────────────────────────────────────────────────── */

  // Direct loads of /writing/<slug>/ stay static, deliberately: someone
  // arriving from X wants the words, not a shell booting over them. The
  // reader only takes over once they choose to move.
  fetch('/assets/shelf.json', { credentials: 'same-origin' })
    .then((r) => r.json())
    .then((data) => {
      SHELF = data;
      history.scrollRestoration = 'manual';
      const here = location.pathname.match(/^\/writing\/([^/]+)\/?$/);
      if (here) current = indexOf(here[1]) >= 0 ? here[1] : null;
    })
    .catch(() => { SHELF = []; });
})();
