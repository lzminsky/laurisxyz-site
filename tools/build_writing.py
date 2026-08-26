#!/usr/bin/env python3
"""Build the /writing/ archive: index page + native article pages.

Source of truth: tools/data/articles.json (full text pulled from @lzminsky's
X Articles) plus the per-article config below (slugs, decks, figures, related
objects). Regenerate with:  python3 tools/build_writing.py

Output: writing/index.html and writing/<slug>/index.html. Static, no build
step at deploy time — the generated HTML is committed.
"""

import hashlib
import html
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tools" / "data"
OUT = ROOT / "writing"
PROSE_LOCK = DATA / "prose.lock.json"

X = "https://x.com/lzminsky"

ARTICLES = [
    {
        "num": 1,
        "slug": "a-hedge-is-not-a-product",
        "title": "A hedge is not a product",
        "deck": "A contract can be bought. A hedge has to be constructed around an exposure.",
        "kicker": "Prediction markets · corporate risk",
        "date": "14 Jul 2026",
        "iso": "2026-07-14",
        "url": "https://x.com/lzminsky/status/2076780601743487460",
        "hero": {"file": "article1_hedge_hero.jpg", "w": 2048, "h": 819,
                 "caption": "The display case: a contract sold as a product, wired to the documents of a real exposure."},
        "skip_first": True,
        "figures": [],
        "related": [
            ("Hedgebook — corporate exposures, matched to live contracts", "https://tryblanket.app/hedgebook", True),
            ("Blanket — small-business risk, mapped to Kalshi", "https://tryblanket.app", True),
        ],
    },
    {
        "num": 2,
        "slug": "credit-already-trades-event-risk",
        "title": "Credit already trades event risk",
        "deck": "Or how to scale non-sports event contract markets: what synthetic risk transfer teaches about institutional ownership.",
        "kicker": "Event markets · credit",
        "date": "09 Jul 2026",
        "iso": "2026-07-09",
        "url": "https://x.com/lzminsky/status/2075235328995033576",
        "hero": {"file": "exh_credit_hero.jpg", "w": 2048, "h": 771,
                 "caption": "How a synthetic risk transfer works: the bank keeps the loans, sells the first loss, and holds less capital."},
        "figures": [
            {"anchor": "uninformed", "occurrence": 1, "file": "article2_credit_3_liquidity.png", "w": 2048, "h": 1152,
             "caption": "Where the liquidity comes from: speculators cross-subsidising each other today; a funded note supplies the uninformed side."},
            {"anchor": "traffic", "file": "article2_credit_4_traffic.png", "w": 2048, "h": 1152,
             "caption": "The traffic runs both ways: a public price of default risk one way, hedging demand for the recession tail the other."},
            {"anchor": "ISDA committee", "file": "article2_credit_2_who_decides.png", "w": 2048, "h": 1152,
             "caption": "Who decides the event: an ISDA committee vote against an exchange rulebook with a named public source."},
        ],
        "related": [
            ("Companion note — on Bartlett &amp; O'Hara, “Adverse Selection in Prediction Markets”", "https://x.com/lzminsky/status/2075646380500987956", True),
        ],
    },
    {
        "num": 3,
        "slug": "benchmarks-and-institutional-scale",
        "title": "Benchmarks are key to scaling prediction markets institutionally",
        "deck": "Which benchmarks can actually do it, in what order — and why the benchmark slot is the one to own.",
        "kicker": "Market structure · benchmarks",
        "date": "05 May 2026",
        "iso": "2026-05-05",
        "url": "https://x.com/lzminsky/status/2051741765682508073",
        "hero": None,
        "thumb": {"file": "article3_benchmarks_5_timeline.png", "w": 2000, "h": 1360},
        "figures": [
            {"anchor": "BISTRO", "file": "article3_benchmarks_5_timeline.png", "w": 2000, "h": 1360,
             "caption": "Two parallel tracks: BISTRO to the $44bn Markit exit; Crypto Facilities to the BRR inside 6 of 11 spot ETFs."},
            {"anchor": "Crypto ran it over eight", "file": "article3_benchmarks_2_kraken.png", "w": 1538, "h": 772,
             "caption": "February 2019: Kraken acquires Crypto Facilities in a nine-figure deal — the index layer was the asset."},
            {"anchor": "captured what they captured", "file": "article3_benchmarks_3_cds_iboxx_bubbles.png", "w": 1007, "h": 728,
             "caption": "What settles against a reference: $35tn of CDS indices; the iBoxx complex across ETFs, TRS, futures, and options."},
            {"anchor": "analytical framework to understand this regime", "file": "article3_benchmarks_6_fomc_dashboard.png", "w": 728, "h": 1570, "portrait": True,
             "caption": "The SLAM Explorer on an FOMC contract: the vega wedge decomposed against execution cost."},
            {"anchor": "unbundled version", "file": "article3_benchmarks_7_figure1.png", "w": 1816, "h": 1064,
             "caption": "Payoff equivalence: as ε→0 the vertical spread converges to the event contract. The payoffs are equivalent; the costs are not."},
        ],
        "related": [
            ("SLAM research project", "https://www.slampaper.xyz", True),
        ],
    },
    {
        "num": 4,
        "slug": "seeing-like-a-market",
        "title": "Seeing Like a Market",
        "deck": "The rationale for institutional risk transfer using prediction markets: a 90-page working paper and 87 contracts across five asset classes.",
        "kicker": "Working paper · SLAM",
        "date": "07 Apr 2026",
        "iso": "2026-04-07",
        "url": "https://x.com/lzminsky/status/2041550364621820388",
        "hero": {"file": "article4_slam_hero.jpg", "w": 1878, "h": 751,
                 "caption": "The Decision Surface: 30 win · 12 at threshold · 45 loss, of 87 contracts at $3m scale."},
        "figures": [],
        "related": [
            ("SLAM research project", "https://www.slampaper.xyz", True),
        ],
    },
    {
        "num": 5,
        "slug": "philosophical-precision-is-the-new-assembly",
        "title": "In the Age of Claude, Philosophical Precision Is the New Assembly",
        "deck": "Precise conceptual vocabulary as a control language for agentic reasoning.",
        "kicker": "Essay · systems of thought",
        "date": "05 Feb 2026",
        "iso": "2026-02-05",
        "url": "https://x.com/lzminsky/status/2019496687887077595",
        "hero": {"file": "article5_claude_hero.png", "w": 600, "h": 240, "natural": True,
                 "caption": "A 1970s assembly reference sheet: the last time precision at the lowest level was the whole game."},
        "figures": [],
        "related": [
            ("Library", "/#library", False),
        ],
    },
    {
        "num": 6,
        "slug": "welcome-to-post-ct",
        "title": "Welcome to Post-CT",
        "deck": "Crypto Twitter as a market mechanism: from discovery engine and capital allocator to reputation interface.",
        "kicker": "Essay · market culture",
        "date": "27 Nov 2025",
        "iso": "2025-11-27",
        "url": "https://x.com/lzminsky/status/1994035337329274912",
        "hero": {"file": "article6_postct_hero.jpg", "w": 1065, "h": 426,
                 "caption": "The monoculture and what follows it."},
        "figures": [],
        "related": [],
    },
]

FEATURED_NOTES = [
    {
        "title": "Introducing Blanket",
        "date": "11 Aug 2026",
        "iso": "2026-08-11",
        "deck": "A public research product for discovering where listed event markets may partially fit small-business risk — and where they do not.",
        "url": "https://x.com/lzminsky/status/2087177263716450574",
        "image": {"src": "/assets/blanket.png", "w": 1200, "h": 630},
    },
    {
        "title": "Statebook",
        "date": "15 Jul 2026",
        "iso": "2026-07-15",
        "deck": "A coherence layer above isolated books, organizing contracts by the states in which they pay.",
        "url": "https://x.com/lzminsky/status/2077464459522568198",
        "image": {"src": "/assets/statebook.png", "w": 1200, "h": 630},
    },
]

NOTES = [
    ("The exchange stack is converging", "15 Jul 2026",
     "Venue labels increasingly describe the front door, not the payoff stack.",
     "https://x.com/lzminsky/status/2077174969738363261"),
    ("I was very wrong — the compute curve, corrected", "14 Jul 2026",
     "A public correction on compute markets, quoting the July 3 framework it revises.",
     "https://x.com/lzminsky/status/2077131007430725932"),
    ("On Bartlett &amp; O'Hara, “Adverse Selection in Prediction Markets”", "10 Jul 2026",
     "Reading 41.6 million Kalshi trades: what the absence of Glosten–Milgrom liquidity traders means for the book.",
     "https://x.com/lzminsky/status/2075646380500987956"),
    ("Gracián and the luck surface area", "06 Jul 2026",
     "L = D × T. The interior maximum beats either corner.",
     "https://x.com/lzminsky/status/2074166089160810967"),
    ("Compute, sliced four ways", "03 Jul 2026",
     "The level, the shape, the residual, and the jumps — and the instrument each slice gets.",
     "https://x.com/lzminsky/status/2073033302064132119"),
    ("Private credit and adverse selection", "20 Jun 2026",
     "Why local underwriting and borrower monitoring matter when high-yield private-credit platforms move into unfamiliar markets.",
     "https://x.com/lzminsky/status/2068082510911734088"),
    ("Hedgebook, version one", "30 May 2026",
     "The launch note and product demo: every company's real-world risk, mapped to live contracts.",
     "https://x.com/lzminsky/status/2060758432773280053"),
    ("Cultural Victory", "17 May 2026",
     "Perpetuals, event claims, and tokenized equity as different surfaces around previously unpriced states.",
     "https://x.com/lzminsky/status/2056040962263077346"),
    ("Institutional event-contract structuring workflow", "16 May 2026",
     "The full desk workflow, drawn: from exposure decomposition to documentation and recognition.",
     "https://x.com/lzminsky/status/2055669526939816369"),
]


def inline(text: str) -> str:
    """Escape, then apply the small amount of inline markup the corpus uses."""
    s = html.escape(text, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"(https?://[^\s<]+[^\s<.,;:)\]])", r'<a href="\1" target="_blank" rel="noopener">\1</a>', s)
    s = re.sub(r"(?<![\w/])www\.([^\s<]+[^\s<.,;:)\]])",
               r'<a href="https://www.\1" target="_blank" rel="noopener">www.\1</a>', s)
    s = re.sub(r"@([A-Za-z0-9_]{2,15})",
               r'<a href="https://x.com/\1" target="_blank" rel="noopener">@\1</a>', s)
    return s


# ── The prose guard ────────────────────────────────────────────────────────
# Lauris's published words are not ours to touch. Every build re-derives the
# reader-visible prose of each article, fingerprints it, and compares against
# tools/data/prose.lock.json. Any drift fails the build. Markup, ids, ticks,
# and figures may change freely; the words may not.
#
# To accept a genuine text change (a corrected articles.json), delete the
# lockfile and rebuild — it regenerates, and the diff is reviewable in git.

_TAG = re.compile(r"<[^>]+>")
_FIGURE = re.compile(r"<figure\b.*?</figure>", re.S)


def prose_of(body_html: str) -> str:
    """His words, with all markup removed.

    Figure captions are stripped first: those are our editorial furniture, not
    his article. They must not inflate his word count, and they must not be
    frozen by a guard whose job is to protect *his* prose.
    """
    text = _FIGURE.sub(" ", body_html)
    text = _TAG.sub(" ", text)
    text = html.unescape(text)
    text = unicodedata.normalize("NFC", text)
    return " ".join(text.split())


def check_prose(fingerprints: dict) -> None:
    if not PROSE_LOCK.exists():
        PROSE_LOCK.write_text(json.dumps(fingerprints, indent=2, sort_keys=True) + "\n")
        print(f"prose guard: wrote {PROSE_LOCK.relative_to(ROOT)} ({len(fingerprints)} articles)")
        return

    locked = json.loads(PROSE_LOCK.read_text())
    drifted = [s for s, f in fingerprints.items() if locked.get(s) and locked[s]["sha"] != f["sha"]]
    if drifted:
        lines = [f"  {s}: {locked[s]['words']} -> {fingerprints[s]['words']} words" for s in drifted]
        raise SystemExit(
            "prose guard FAILED — the article text changed:\n"
            + "\n".join(lines)
            + "\n\nHis published words must not be edited by the build. If this change is\n"
              f"intentional, delete {PROSE_LOCK.relative_to(ROOT)} and rebuild, then review the git diff."
        )
    new = [s for s in fingerprints if s not in locked]
    if new:
        locked.update({s: fingerprints[s] for s in new})
        PROSE_LOCK.write_text(json.dumps(locked, indent=2, sort_keys=True) + "\n")
        print(f"prose guard: registered {', '.join(new)}")
    print(f"prose guard: OK ({len(fingerprints)} articles unchanged)")


def render_body(art_cfg, paragraphs):
    figures = list(art_cfg.get("figures", []))
    used = set()
    out = []
    num = art_cfg["num"]
    fig_n = 0
    paras = paragraphs[1:] if art_cfg.get("skip_first") else paragraphs[:]

    # group consecutive "1. " / "2. " paragraphs into an ordered list
    i = 0
    blocks = []
    while i < len(paras):
        p = paras[i]
        if re.match(r"^1\.\s", p):
            items = []
            while i < len(paras) and re.match(r"^\d+\.\s", paras[i]):
                items.append(re.sub(r"^\d+\.\s", "", paras[i]))
                i += 1
            blocks.append(("ol", items, i))
            continue
        blocks.append(("p", p, i))
        i += 1

    for kind, p, block_i in blocks:
        # Positional anchors, never semantic. A slug scheme cannot give the
        # second "Two Forms of Order" its own link without appending -2, which
        # would be renumbering his heading. f{num}-{i} never collides and never
        # encodes a judgment about the text.
        anchor = f"f{num}-{block_i}"
        if kind == "ol":
            out.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in p) + "</ol>")
            continue
        stripped = p.strip()
        if re.fullmatch(r"\*\*.+\*\*", stripped):
            heading = stripped[2:-2]
            out.append(f'<h2 id="{anchor}">{inline(heading)}</h2>')
        elif stripped in ("Top tier", "Bottom tier", "Quick initial links"):
            out.append(f'<h3 id="{anchor}">{inline(stripped)}</h3>')
        elif "\n- " in p:
            head, *items = re.split(r"\n-\s*", p)
            if head.strip():
                out.append(f"<p>{inline(head.strip())}</p>")
            out.append("<ul>" + "".join(f"<li>{inline(x.strip())}</li>" for x in items if x.strip()) + "</ul>")
        elif stripped.startswith("*(") and stripped.endswith(")*"):
            out.append(f'<p class="foot">{inline(stripped[2:-2])}</p>')
        else:
            out.append(f"<p>{inline(p)}</p>")

        # figure placement: after the paragraph containing the anchor
        for fig in figures:
            key = (fig["anchor"], fig["file"])
            if key in used or kind != "p":
                continue
            if fig["anchor"].lower() in p.lower():
                occ = fig.get("occurrence", 1)
                fig["_seen"] = fig.get("_seen", 0) + 1
                if fig["_seen"] < occ:
                    continue
                used.add(key)
                fig_n += 1
                fig_anchor = f"f{num}-fig{fig_n}"
                cls = "art-fig art-fig--portrait" if fig.get("portrait") else "art-fig"
                out.append(
                    f'<figure class="{cls}" id="{fig_anchor}">'
                    f'<img src="/assets/writing/{fig["file"]}" '
                    f'alt="{html.escape(fig["caption"])}" width="{fig["w"]}" height="{fig["h"]}" loading="lazy">'
                    f'<figcaption>{fig["caption"]}</figcaption></figure>'
                )

    missing = [f["file"] for f in figures if (f["anchor"], f["file"]) not in used]
    if missing:
        raise SystemExit(f"[{art_cfg['slug']}] unplaced figures: {missing}")
    return "\n".join(out)


STYLE = """
        :root {
            --type-display: 'Source Serif 4', Georgia, 'Times New Roman', serif;
            --type-display-regular: 'Source Serif 4', Georgia, 'Times New Roman', serif;
            --type-body: 'Source Serif 4', Georgia, 'Times New Roman', serif;
            --type-mono: 'IBM Plex Mono', Consolas, monospace;
            --type-display-weight: 400;
            --type-display-tracking: -.02em;
            --type-label-tracking: .05em;
            --paper: #ffffff; --paper-raised: #ffffff; --ink: #1a1816; --ink-soft: #4e4744;
            --ink-muted: #77716d; --rule: #dedbd7; --teal: #0d7680; --wine: #0d7680;
            --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::selection { background: var(--ink); color: var(--paper); }
        html { background: #ffffff; font-size: 18px; }
        body {
            min-height: 100vh;
            background: var(--paper);
            color: var(--ink); font-family: var(--type-body); font-weight: 400; line-height: 1.3;
            letter-spacing: 0; -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility;
        }
        body::before {
            position: fixed; z-index: 9999; inset: 0; pointer-events: none; content: '';
            opacity: .018;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='grain'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.82' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23grain)' opacity='.72'/%3E%3C/svg%3E");
            background-size: 160px 160px; mix-blend-mode: multiply;
        }
        a { color: inherit; }
        img { display: block; max-width: 100%; height: auto; }
        .skip-link {
            position: fixed; z-index: 100; top: 12px; left: 12px; padding: 11px 14px;
            background: var(--ink); color: var(--paper); font: 500 .667rem/1 var(--type-mono);
            letter-spacing: .04em; text-decoration: none; text-transform: uppercase;
            transform: translateY(calc(-100% - 18px)); transition: transform 180ms var(--ease-out);
        }
        .skip-link:focus-visible { outline: 2px solid var(--teal); outline-offset: 3px; transform: none; }
        .container { width: min(1180px, calc(100% - 80px)); margin: 0 auto; padding: 42px 0 88px; }
        .mono { font-family: var(--type-mono); }
        .masthead { display: flex; align-items: flex-start; justify-content: space-between; gap: 32px;
            padding-bottom: 28px; border-bottom: 1px solid var(--rule); }
        .masthead-origin { display: flex; align-items: flex-start; gap: 17px; min-width: 0; }
        .mark-link { display: grid; min-width: 36px; min-height: 44px; color: var(--ink); text-decoration: none; place-content: start; }
        .mark-symbol { font: 2rem/0.8 var(--type-mono); }
        .crumb { padding-top: 6px; color: var(--ink-muted); font: 500 .667rem/1.6 var(--type-mono); letter-spacing: .05em; text-transform: uppercase; }
        .crumb a { color: var(--ink-muted); text-decoration: none; transition: color 180ms var(--ease-out); }
        .crumb a:hover, .crumb a:focus-visible { color: var(--ink); }
        .crumb span { margin: 0 7px; color: var(--rule); }
        .nav { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: flex-end; gap: 8px 24px; padding-top: 3px; }
        .nav a { display: inline-flex; align-items: flex-start; min-height: 44px; padding-top: 5px; color: var(--ink-muted);
            font: 500 12px/1.2 var(--type-mono); letter-spacing: .05em;
            text-decoration: none; text-transform: uppercase; transition: color 180ms var(--ease-out); }
        .nav a:hover { color: var(--ink); }
        .nav a.nav-x { padding-bottom: 3px; border-bottom: 1px solid currentColor; color: var(--teal); }
        .nav a.nav-x:hover { color: var(--ink); }
        .nav-menu { position: relative; display: none; }
        .nav-menu summary {
            display: inline-flex; min-width: 44px; min-height: 44px; padding: 5px 5px 0;
            align-items: flex-start; justify-content: center; color: var(--ink-muted);
            font: 500 12px/1.2 var(--type-mono); letter-spacing: .05em;
            list-style: none; cursor: pointer; text-transform: uppercase;
        }
        .nav-menu summary::-webkit-details-marker { display: none; }
        .nav-menu summary::after { margin-left: 6px; content: '+'; }
        .nav-menu[open] summary { color: var(--teal); }
        .nav-menu[open] summary::after { content: '−'; }
        .nav-menu-panel {
            position: absolute; z-index: 50; top: 46px; right: 0; width: 204px; padding: 7px;
            border: 1px solid var(--rule); background: var(--paper);
            box-shadow: 0 14px 36px rgba(1, 22, 20, .09);
        }
        .nav-menu-panel a {
            display: flex; width: 100%; min-height: 44px; padding: 11px 12px 9px;
            align-items: center; justify-content: flex-start; font-size: 12px;
        }
        .nav-menu-panel a + a { border-top: 1px solid var(--rule); }
        .nav-menu-panel .nav-menu-x { display: none; color: var(--teal); }
        a:focus-visible { outline: 2px solid var(--teal); outline-offset: 4px; }
        .text-link { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; color: var(--ink);
            font: 500 14px/1.2 var(--type-mono); letter-spacing: .05em;
            text-decoration: underline; text-decoration-color: var(--rule); text-underline-offset: 4px; text-transform: uppercase; }
        .text-link::after { content: '↗'; transition: transform 180ms var(--ease-out); }
        .text-link--in::after { content: '→'; }
        .text-link:hover::after { transform: translate(2px, -2px); }
        .text-link--in:hover::after { transform: translateX(3px); }
        .btn-x { display: inline-flex; align-items: center; gap: 9px; min-height: 44px; padding: 2px 0 5px;
            border: 0; border-bottom: 1px solid currentColor; color: var(--ink);
            font: 500 14px/1.2 var(--type-mono); letter-spacing: .05em;
            text-decoration: none; text-transform: uppercase; transition: color 180ms var(--ease-out); }
        .btn-x::after { content: '↗'; }
        .btn-x:hover { color: var(--teal); }
        .art-title, .arch-title, .arch-item-title, .shelf-title {
            font-family: var(--type-display); font-weight: var(--type-display-weight); letter-spacing: var(--type-display-tracking);
        }
        .art-deck { font-family: var(--type-display); font-weight: 400; font-style: normal; }
        @media (max-width: 960px) {
            .masthead { gap: 24px; }
            .nav { position: relative; flex-wrap: nowrap; gap: 0 14px; }
            .nav > a { min-width: 44px; padding-right: 5px; padding-left: 5px; justify-content: center; white-space: nowrap; }
            .nav > .nav-wide { display: none; }
            .nav-menu { display: block; }
        }
        @media (max-width: 640px) {
            html { font-size: 17px; }
            .container { width: calc(100% - 32px); padding: 22px 0 48px; }
            .masthead { display: flex; align-items: flex-start; gap: 16px; padding-bottom: 15px; }
            .masthead-origin { flex: 0 0 44px; }
            .mark-link { min-width: 44px; min-height: 44px; }
            .mark-symbol { font-size: 1.7rem; }
            .crumb { display: none; }
            .nav { flex: 1; flex-wrap: nowrap; justify-content: flex-end; gap: 0 10px; margin-top: 0; padding-top: 0; }
            .nav > a { min-width: 44px; min-height: 44px; padding: 5px 3px 0; font-size: 12px; white-space: nowrap; }
            .nav > .nav-x { display: none; }
            .nav-menu summary { min-width: 44px; min-height: 44px; padding-top: 5px; font-size: 12px; }
            .nav-menu-panel .nav-menu-x { display: flex; }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { transition-duration: .01ms !important; animation-duration: .01ms !important; }
        }
        @media print { body::before { display: none; } }
"""

ARTICLE_STYLE = """
        .art-head { max-width: 800px; padding: 84px 0 10px; }
        .art-kicker { color: var(--ink-muted); font: 500 .667rem/1.6 var(--type-mono); letter-spacing: .08em; text-transform: uppercase; }
        .art-title { margin-top: 16px; font-size: 48px; font-weight: 400; letter-spacing: -.02em; line-height: 1; }
        .art-deck { max-width: 680px; margin-top: 20px; color: var(--ink-soft); font-size: 24px; font-style: normal; line-height: 1.1; text-wrap: pretty; }
        .art-meta { display: flex; flex-wrap: wrap; gap: 10px 26px; align-items: baseline; margin-top: 26px;
            padding-top: 14px; border-top: 1px solid var(--ink); max-width: 680px; }
        .art-meta time { color: var(--ink-muted); font: 500 .667rem/1.6 var(--type-mono); letter-spacing: .06em; text-transform: uppercase; }
        .art-meta .text-link { color: var(--ink-muted); font-size: .72rem; }
        .art-meta .text-link:hover { color: var(--ink); }
        .art-hero { margin: 44px 0 0; }
        .art-hero img { width: 100%; border: 1px solid var(--rule); background: var(--paper-raised); }
        .art-hero--portrait img, .art-hero--natural img { width: auto; max-width: min(620px, 100%); }
        .art-hero figcaption, .art-fig figcaption { margin-top: 9px; color: var(--ink-muted);
            font: 500 .667rem/1.6 var(--type-mono); letter-spacing: .045em; text-transform: uppercase; max-width: 640px; }
        .art-body { max-width: 700px; margin-top: 54px; }
        .art-body p { margin: 0 0 19px; font-size: 1rem; color: var(--ink); font-weight: 400; line-height: 1.3; letter-spacing: -.02em; }
        .art-body p a, .art-body li a { text-decoration-color: var(--rule); text-underline-offset: 3px; }
        .art-body h2 { margin: 44px 0 16px; font-size: 24px; font-weight: 400; letter-spacing: -.02em; line-height: 1.1; }
        .art-body h3 { margin: 30px 0 12px; color: var(--ink); font: .68rem/1.4 var(--type-mono); letter-spacing: .1em; text-transform: uppercase; }
        .art-body ul, .art-body ol { margin: 0 0 19px 22px; }
        .art-body li { margin-bottom: 8px; font-size: 1rem; font-weight: 400; line-height: 1.3; letter-spacing: -.02em; }
        .art-body .foot { margin-top: 34px; padding-top: 16px; border-top: 1px solid var(--rule);
            color: var(--ink-muted); font-size: .86rem; font-style: italic; }
        .art-fig { margin: 40px 0 40px; max-width: 860px; }
        .art-fig img { width: 100%; border: 1px solid var(--rule); background: var(--paper-raised); }
        .art-fig--portrait img { width: auto; max-width: min(460px, 100%); }
        .shelf { max-width: 860px; margin-top: 76px; padding-top: 18px; border-top: 1px solid var(--ink); }
        .shelf-label { margin-bottom: 6px; color: var(--ink-muted); font: 500 .667rem/1.6 var(--type-mono); letter-spacing: .07em; text-transform: uppercase; }
        .shelf-item {
            display: block;
            padding: 11px 0 12px;
            border-bottom: 1px solid var(--rule);
            text-decoration: none;
        }
        .shelf-title { font-size: 20px; line-height: 1.1; transition: color 160ms var(--ease-out); }
        .shelf-item:hover .shelf-title { color: var(--teal); }
        .shelf-item.is-here .shelf-title { font-weight: 500; }
        .shelf-item.is-here { border-bottom-color: var(--ink); }

        .art-after { max-width: 700px; margin-top: 70px; padding-top: 22px; border-top: 1px solid var(--ink); }
        .art-after-kicker { color: var(--ink-muted); font: 500 .667rem/1.6 var(--type-mono); letter-spacing: .07em; text-transform: uppercase; }
        .art-after ul { margin-top: 12px; list-style: none; }
        .art-after li { margin-bottom: 9px; }
        .art-after a { font-size: .98rem; text-decoration-color: var(--rule); text-underline-offset: 3px; }
        .art-cta { display: flex; flex-wrap: wrap; gap: 16px 24px; align-items: center; margin-top: 34px; }
        @media (max-width: 640px) {
            .art-head { padding: 50px 0 0; }
            .art-title { margin-top: 12px; font-size: 40px; line-height: 1; }
            .art-deck { margin-top: 17px; font-size: 24px; line-height: 1.1; }
            .art-meta { gap: 7px 20px; margin-top: 22px; padding-top: 12px; }
            .art-hero { margin-top: 32px; }
            .art-body { margin-top: 38px; }
            .art-body p, .art-body li { font-size: .98rem; line-height: 1.3; }
            .art-body h2 { margin: 37px 0 13px; font-size: 24px; line-height: 1.1; }
            .art-body h3 { margin-top: 26px; }
            .art-fig { margin: 30px 0; }
            .shelf { margin-top: 54px; }
            .art-after { margin-top: 50px; }
        }
        /* ── Publication type roles ───────────────────────────────────── */
        .art-title, .arch-title {
            font-family: var(--type-display);
            font-weight: 400;
            letter-spacing: var(--type-display-tracking);
        }
        .art-title, .arch-title { line-height: 1; }
        .art-deck { font-family: var(--type-display); font-weight: 400; font-style: normal; }
        .art-body h2, .shelf-title, .arch-item-title, .arch-lead-title, .wall-title {
            font-family: var(--type-display-regular);
            font-weight: 400;
            letter-spacing: -.02em;
        }
        .arch-intro, .arch-lead-deck, .arch-item-deck, .note-deck {
            font-family: var(--type-body);
            font-weight: 400;
            letter-spacing: -.02em;
            line-height: 1.3;
        }
        .art-kicker, .art-meta time, .art-meta .text-link, .art-after-kicker,
        .shelf-label, .arch-label,
        .arch-item-open, .art-fig figcaption, .art-hero figcaption, .art-body h3,
        .crumb, .nav a, .btn-x, .note-item time {
            font-weight: 500;
        }
"""

INDEX_STYLE = """
        .arch-head { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(280px, .8fr); gap: 70px; align-items: end; padding: 94px 0 54px; }
        .arch-title { max-width: 720px; font-size: 48px; font-weight: 400; letter-spacing: -.02em; line-height: 1; }
        .arch-intro { max-width: 460px; margin: 0; color: var(--ink-soft); font-family: var(--type-body); font-size: 1rem; font-style: normal; font-weight: 400; line-height: 1.3; text-wrap: pretty; }
        .arch-section { margin-top: 44px; }
        .arch-label { color: var(--ink); font: 500 .667rem/1.4 var(--type-mono); letter-spacing: .08em; text-transform: uppercase; }
        .arch-lead { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(300px, .65fr); gap: 48px; margin-top: 18px; padding: 32px 0 44px; border-top: 1px solid var(--ink); border-bottom: 1px solid var(--rule); text-decoration: none; }
        .arch-lead-media { overflow: hidden; border: 1px solid var(--rule); }
        .arch-lead-media img { width: 100%; transition: transform 900ms var(--ease-out); }
        .arch-lead-copy { display: flex; min-width: 0; flex-direction: column; justify-content: space-between; }
        .arch-lead time, .arch-item time { color: var(--ink-muted); font: 500 .667rem/1.6 var(--type-mono); font-variant-numeric: tabular-nums; letter-spacing: .045em; text-transform: uppercase; }
        .arch-lead-title { display: block; margin-top: 12px; font-family: var(--type-display-regular); font-size: 32px; font-weight: 400; letter-spacing: -.02em; line-height: 1.1; }
        .arch-lead-deck { display: block; margin-top: 14px; color: var(--ink-soft); font-size: .94rem; font-weight: 400; line-height: 1.3; text-wrap: pretty; }
        .arch-list { border-top: 1px solid var(--ink); }
        .arch-item { display: grid; grid-template-columns: 108px minmax(0, 1fr) 210px; gap: 10px 26px; align-items: start; padding: 25px 0 27px; border-bottom: 1px solid var(--rule); text-decoration: none; }
        .arch-item time { padding-top: 4px; }
        .arch-item-title { display: block; font-family: var(--type-display-regular); font-size: 24px; font-weight: 400; letter-spacing: -.02em; line-height: 1.1; transition: color 180ms var(--ease-out); }
        .arch-item-deck { display: block; max-width: 560px; margin-top: 7px; color: var(--ink-soft); font-size: .87rem; font-weight: 400; line-height: 1.3; text-wrap: pretty; }
        .arch-item-open { display: inline-block; min-height: 44px; margin-top: 9px; color: var(--ink); font: 500 .667rem/1.4 var(--type-mono); letter-spacing: .045em; text-transform: uppercase; }
        .arch-thumb { overflow: hidden; margin: 2px 0 0; border: 1px solid var(--rule); }
        .arch-thumb img { width: 100%; aspect-ratio: 1.8 / 1; background: var(--paper-raised); object-fit: cover; transition: transform 800ms var(--ease-out); }
        .arch-lead:hover .arch-lead-media img, .arch-item:hover .arch-thumb img { transform: scale(1.025); }
        .arch-item:hover .arch-item-title { color: var(--teal); }
        .note-features { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 34px; margin-top: 16px; padding-top: 22px; border-top: 1px solid var(--ink); }
        .note-feature { min-width: 0; text-decoration: none; transition: transform 140ms var(--ease-out); }
        .note-feature:active { transform: scale(.98); }
        .note-feature-media { display: block; overflow: hidden; border: 1px solid var(--rule); }
        .note-feature-media img { width: 100%; aspect-ratio: 1.8 / 1; object-fit: cover; transition: transform 800ms var(--ease-out); }
        .note-feature-meta { display: flex; align-items: baseline; justify-content: space-between; gap: 18px; margin-top: 13px; }
        .note-feature time { color: var(--ink-muted); font: 500 .667rem/1.6 var(--type-mono); letter-spacing: .045em; text-transform: uppercase; }
        .note-feature-arrow { color: var(--ink-muted); font: .8rem/1 var(--type-mono); }
        .note-feature-title { display: block; margin-top: 9px; font-family: var(--type-display-regular); font-size: 24px; font-weight: 400; line-height: 1.1; transition: color 180ms var(--ease-out); }
        .note-feature-deck { display: block; max-width: 48ch; margin-top: 7px; color: var(--ink-soft); font-size: .84rem; line-height: 1.3; }
        @media (hover: hover) and (pointer: fine) {
            .note-feature:hover .note-feature-media img { transform: scale(1.025); }
            .note-feature:hover .note-feature-title { color: var(--teal); }
        }
        .note-list { margin-top: 31px; border-top: 1px solid var(--ink); }
        .note-item { display: grid; grid-template-columns: 108px minmax(0, 1fr) auto; gap: 8px 26px; align-items: baseline; padding: 18px 0 20px; border-bottom: 1px solid var(--rule); text-decoration: none; }
        .note-item time { color: var(--ink-muted); font: 500 .667rem/1.6 var(--type-mono); font-variant-numeric: tabular-nums; letter-spacing: .045em; text-transform: uppercase; }
        .note-title { font-size: 1rem; font-weight: 400; line-height: 1.3; transition: color 180ms var(--ease-out); }
        .note-item:hover .note-title { color: var(--teal); }
        .note-deck { display: block; max-width: 680px; margin-top: 4px; color: var(--ink-soft); font-size: .84rem; font-weight: 400; line-height: 1.3; }
        .note-arrow { color: var(--ink-muted); font: .8rem/1 var(--type-mono); }
        .motion-ready [data-animate] { opacity: 0; transform: translateY(16px); }
        .motion-ready [data-animate].is-visible { opacity: 1; transform: none; transition: opacity 700ms var(--ease-out), transform 700ms var(--ease-out); }
        @media (max-width: 800px) {
            .arch-head { grid-template-columns: 1fr; gap: 28px; padding: 72px 0 44px; }
            .arch-lead { grid-template-columns: 1fr; }
            .arch-item { grid-template-columns: 96px minmax(0, 1fr); }
            .arch-thumb { display: none; }
            .note-item { grid-template-columns: 96px minmax(0, 1fr); }
            .note-arrow { display: none; }
        }
        @media (max-width: 560px) {
            .arch-head { gap: 20px; padding: 50px 0 36px; }
            .arch-title { max-width: 5.5em; font-size: 40px; line-height: 1; }
            .arch-intro { font-size: .93rem; line-height: 1.3; }
            .arch-section { margin-top: 30px; }
            .arch-lead { gap: 25px; margin-top: 14px; padding: 24px 0 31px; }
            .arch-lead-title { font-size: 24px; }
            .arch-lead-deck { margin-top: 10px; font-size: .86rem; line-height: 1.3; }
            .arch-item, .note-item { grid-template-columns: 1fr; gap: 6px; padding: 20px 0 22px; }
            .arch-item-title { font-size: 20px; }
            .arch-item-deck, .note-deck { font-size: .81rem; }
            .note-features { grid-template-columns: 1fr; gap: 27px; padding-top: 18px; }
            .note-feature-title { font-size: 20px; }
            .note-feature-deck { font-size: .81rem; }
        }
"""


def shell(title, description, style_extra, body, canonical, article_css=False,
          share_image="https://www.lauris.xyz/assets/share.png", share_width=1200,
          share_height=630, share_alt="Lauris — research, market design, and ventures",
          og_type="website"):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <meta name="description" content="{html.escape(description)}">
    <meta name="theme-color" content="#ffffff">
    <meta property="og:title" content="{html.escape(title)}">
    <meta property="og:description" content="{html.escape(description)}">
    <meta property="og:url" content="{canonical}">
    <meta property="og:type" content="{og_type}">
    <meta property="og:site_name" content="Lauris">
    <meta property="og:image" content="{share_image}">
    <meta property="og:image:width" content="{share_width}">
    <meta property="og:image:height" content="{share_height}">
    <meta property="og:image:alt" content="{html.escape(share_alt)}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:creator" content="@lzminsky">
    <meta name="twitter:title" content="{html.escape(title)}">
    <meta name="twitter:description" content="{html.escape(description)}">
    <meta name="twitter:image" content="{share_image}">
    <meta name="twitter:image:alt" content="{html.escape(share_alt)}">
    <link rel="canonical" href="{canonical}">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="mask-icon" href="/favicon.svg" color="#1a1816">
    <link rel="manifest" href="/site.webmanifest">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Source+Serif+4:ital,opsz,wght@0,8..60,200..900;1,8..60,200..900&display=swap" rel="stylesheet">
    <style>{STYLE}</style>
    {'<link rel="stylesheet" href="/assets/article.css">' if article_css else f'<style>{style_extra}</style>'}
</head>
<body>
    <a class="skip-link" href="#main-content">Skip to content</a>
    <div class="container">
        <header class="masthead">
            <div class="masthead-origin">
                <a href="/" class="mark-link" aria-label="Lauris — home"><span class="mark-symbol">┐</span></a>
                <p class="crumb"><a href="/">Lauris</a><span>/</span><a href="/writing/">Writing</a></p>
            </div>
            <nav class="nav" aria-label="Primary navigation">
                <a href="/#work">Work</a>
                <a href="/writing/">Writing</a>
                <a class="nav-wide" href="/#library">Library</a>
                <a class="nav-x" href="{X}" target="_blank" rel="noopener">Follow on X ↗</a>
                <details class="nav-menu">
                    <summary>Menu</summary>
                    <div class="nav-menu-panel">
                        <a href="/">Home</a>
                        <a href="/#now">Now</a>
                        <a href="/#formation">Formation</a>
                        <a href="/#library">Library</a>
                        <a class="nav-menu-x" href="{X}" target="_blank" rel="noopener">Follow on X ↗</a>
                    </div>
                </details>
            </nav>
        </header>
        <main id="main-content">
{body}
        </main>
    </div>
    <script>
        (() => {{
            const navMenus = Array.from(document.querySelectorAll('.nav-menu'));
            const closeNavMenus = (except = null) => {{
                navMenus.forEach(menu => {{
                    if (menu !== except) menu.removeAttribute('open');
                }});
            }};
            navMenus.forEach(menu => {{
                menu.addEventListener('toggle', () => {{
                    if (menu.open) closeNavMenus(menu);
                }});
                menu.addEventListener('click', event => {{
                    if (event.target.closest('a')) menu.removeAttribute('open');
                }});
                menu.addEventListener('keydown', event => {{
                    if (event.key !== 'Escape') return;
                    menu.removeAttribute('open');
                    menu.querySelector('summary')?.focus();
                }});
            }});
            document.addEventListener('click', event => {{
                if (!event.target.closest('.nav-menu')) closeNavMenus();
            }});

            if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
            const items = Array.from(document.querySelectorAll('[data-animate]'));
            if (!items.length || !('IntersectionObserver' in window)) return;
            document.documentElement.classList.add('motion-ready');
            const observer = new IntersectionObserver((entries) => {{
                entries.forEach((entry) => {{
                    if (!entry.isIntersecting) return;
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target);
                }});
            }}, {{ rootMargin: '0px 0px -8% 0px', threshold: .06 }});
            items.forEach((item) => observer.observe(item));
        }})();
    </script>
</body>
</html>
"""


def shelf(current_slug: str) -> str:
    """Simple links to the other long-form pieces."""
    rows = []
    for c in ARTICLES:
        here = c["slug"] == current_slug
        cls = "shelf-item is-here" if here else "shelf-item"
        current = ' aria-current="page"' if here else ""
        slug = c["slug"]
        rows.append(
            f'<a class="{cls}" href="/writing/{slug}/"{current}>'
            f'<span class="shelf-title">{html.escape(c["title"])}</span></a>'
        )
    return (
        '<nav class="shelf" aria-label="All writing">'
        '<p class="shelf-label">More writing</p>' + "".join(rows) + "</nav>"
    )


def build_article(cfg, data, fingerprints=None):
    body_html = render_body(cfg, data["paragraphs"])

    words = len(prose_of(body_html).split())
    if fingerprints is not None:
        fingerprints[cfg["slug"]] = {
            "sha": hashlib.sha256(prose_of(body_html).encode()).hexdigest(),
            "words": words,
        }

    hero = cfg["hero"]
    hero_html = ""
    if hero:
        hero_cls = "art-hero"
        if hero.get("portrait"):
            hero_cls += " art-hero--portrait"
        if hero.get("natural"):
            hero_cls += " art-hero--natural"
        hero_html = f"""
                <figure class="{hero_cls}">
                    <img src="/assets/writing/{hero['file']}" alt="{html.escape(hero['caption'])}" width="{hero['w']}" height="{hero['h']}">
                    <figcaption>{hero['caption']}</figcaption>
                </figure>"""
    related = ""
    if cfg["related"]:
        items = "".join(
            f'<li><a href="{href}"{" target=_blank rel=noopener".replace(" ", " ") if ext else ""}>{label}{" ↗" if ext else " →"}</a></li>'.replace(
                "target=_blank rel=noopener", 'target="_blank" rel="noopener"')
            for label, href, ext in cfg["related"]
        )
        related = f"""
            <aside class="art-after">
                <p class="art-after-kicker">Related</p>
                <ul>{items}</ul>
            </aside>"""

    body = f"""
            <article data-slug="{cfg['slug']}">
                <header class="art-head">
                    <p class="art-kicker">{cfg['kicker']}</p>
                    <h1 class="art-title">{html.escape(cfg['title'])}</h1>
                    <p class="art-deck">{cfg['deck']}</p>
                    <div class="art-meta">
                        <time datetime="{cfg['iso']}">{cfg['date']}</time>
                        <a class="text-link" href="{cfg['url']}" target="_blank" rel="noopener">View original on X</a>
                    </div>
                </header>{hero_html}
                <div class="art-body">
{body_html}
                </div>
            </article>{related}
            {shelf(cfg['slug'])}
            <div class="art-cta">
                <a class="btn-x" href="{X}" target="_blank" rel="noopener">Follow on X</a>
                <a class="text-link text-link--in" href="/writing/">All writing</a>
            </div>"""

    share = cfg["hero"] or cfg.get("thumb")
    share_image = f"https://www.lauris.xyz/assets/writing/{share['file']}" if share else "https://www.lauris.xyz/assets/share.png"
    share_width = share["w"] if share else 1200
    share_height = share["h"] if share else 630
    page = shell(f"{cfg['title']} — Lauris", cfg["deck"].replace("&amp;", "&"),
                 ARTICLE_STYLE, body, f"https://lauris.xyz/writing/{cfg['slug']}/",
                 article_css=True, share_image=share_image, share_width=share_width,
                 share_height=share_height, share_alt=cfg["title"], og_type="article")
    dest = OUT / cfg["slug"] / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page)
    return dest


def build_article_css():
    """Write the shared article styles."""
    dest = ROOT / "assets" / "article.css"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("/* Generated by tools/build_writing.py — do not edit. */\n" + ARTICLE_STYLE.strip() + "\n")
    return dest

def build_index():
    lead = ARTICLES[0]
    lead_hero = lead["hero"] or lead.get("thumb")
    rows = []
    for cfg in ARTICLES[1:]:
        hero = cfg["hero"] or cfg.get("thumb")
        rows.append(f"""
                    <a class="arch-item" href="/writing/{cfg['slug']}/" data-animate>
                        <time datetime="{cfg['iso']}">{cfg['date']}</time>
                        <span class="arch-item-copy">
                            <span class="arch-item-title">{html.escape(cfg['title'])}</span>
                            <span class="arch-item-deck">{cfg['deck']}</span>
                            <span class="arch-item-open">Read →</span>
                        </span>
                        <span class="arch-thumb"><img src="/assets/writing/{hero['file']}" alt="" width="{hero['w']}" height="{hero['h']}" loading="lazy"></span>
                    </a>""")
    notes = []
    for title, date, deck, url in NOTES:
        notes.append(f"""
                    <a class="note-item" href="{url}" target="_blank" rel="noopener" data-animate>
                        <time>{date}</time>
                        <span class="note-title">{title}<span class="note-deck">{deck}</span></span>
                        <span class="note-arrow">↗</span>
                    </a>""")
    featured_notes = []
    for note in FEATURED_NOTES:
        image = note["image"]
        featured_notes.append(f"""
                    <a class="note-feature" href="{note['url']}" target="_blank" rel="noopener" data-animate>
                        <span class="note-feature-media"><img src="{image['src']}" alt="" width="{image['w']}" height="{image['h']}" loading="lazy"></span>
                        <span class="note-feature-meta"><time datetime="{note['iso']}">{note['date']}</time><span class="note-feature-arrow">↗</span></span>
                        <span class="note-feature-title">{html.escape(note['title'])}</span>
                        <span class="note-feature-deck">{note['deck']}</span>
                    </a>""")

    body = f"""
            <header class="arch-head">
                <div>
                    <h1 class="arch-title">Essays and notes.</h1>
                </div>
                <p class="arch-intro">I write about market formation, institutional risk transfer, and the financialization of new underliers. Longer articles are archived here; shorter notes remain on <a href="{X}" target="_blank" rel="noopener">X</a>.</p>
            </header>
            <section class="arch-section" aria-label="Articles">
                <p class="arch-label">Articles</p>
                <a class="arch-lead" href="/writing/{lead['slug']}/" data-animate>
                    <span class="arch-lead-media"><img src="/assets/writing/{lead_hero['file']}" alt="" width="{lead_hero['w']}" height="{lead_hero['h']}"></span>
                    <span class="arch-lead-copy">
                        <span>
                            <time datetime="{lead['iso']}">{lead['date']}</time>
                            <span class="arch-lead-title">{html.escape(lead['title'])}</span>
                            <span class="arch-lead-deck">{lead['deck']}</span>
                        </span>
                        <span class="arch-item-open">Read →</span>
                    </span>
                </a>
                <div class="arch-list">{''.join(rows)}
                </div>
            </section>
            <section class="arch-section" aria-label="Working notes">
                <p class="arch-label">Notes on X</p>
                <div class="note-features">{''.join(featured_notes)}
                </div>
                <div class="note-list">{''.join(notes)}
                </div>
            </section>"""

    page = shell("Writing — Lauris", "Essays and working notes on market formation, institutional risk transfer, and the financialization of new underliers.",
                 INDEX_STYLE, body, "https://lauris.xyz/writing/")
    dest = OUT / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page)
    return dest


def main():
    articles = json.loads((DATA / "articles.json").read_text())
    by_num = {a["num"]: a for a in articles}

    fingerprints = {}
    for cfg in ARTICLES:
        dest = build_article(cfg, by_num[cfg["num"]], fingerprints)
        print("wrote", dest.relative_to(ROOT))
    print("wrote", build_index().relative_to(ROOT))
    print("wrote", build_article_css().relative_to(ROOT))
    check_prose(fingerprints)


if __name__ == "__main__":
    main()
