#!/usr/bin/env python3
"""Compose approved legal content with the actual Xeni_brows static-site shell.

The source ZIP contains the Astro-built header, footer, fonts, responsive CSS,
and interactive mobile menu. Do not use the standalone legal HTML's custom shell.
"""
from pathlib import Path
import re

SITE = Path("_site")
STAGED = Path("legal-pages")
ROUTES = ("information", "offer", "privacy")
MAIN_RE = re.compile(r"<main\b[^>]*>[\s\S]*?</main>")
NAV_RE = re.compile(r'<nav\b[^>]*aria-label="Дополнительная навигация"[^>]*>[\s\S]*?</nav>')
FOOTER_RE = re.compile(r"<footer\b[^>]*>[\s\S]*?</footer>")
FOOTER_LINKS = (
    '<a href="/care/">Уход</a>'
    '<a href="/contacts/">Контакты</a>'
    '<a href="/information/">Правовые документы</a>'
)
FOOTER_NAV = '<nav aria-label="Дополнительная навигация">' + FOOTER_LINKS + '</nav>'


def require(value, reason):
    if not value:
        raise RuntimeError(reason)
    return value


def normalize_footer(match):
    original = match.group(0)
    updated, count = NAV_RE.subn(lambda _: FOOTER_NAV, original, count=1)
    require(count == 1, "Footer navigation missing from site shell")
    return updated


# The care page is built from the shared SiteLayout. It has the authentic
# hamburger button, responsive navigation, compiled JS and font imports.
template_path = SITE / "care" / "index.html"
template = require(template_path.read_text(encoding="utf-8"), str(template_path))
template_main = require(MAIN_RE.search(template), "Main missing from Astro care template")
template_open = require(
    re.match(r"<main\b[^>]*>", template_main.group(0)),
    "Main opening tag missing",
).group(0)
require('class="menu-toggle"' in template, "Astro mobile menu missing")
require('id="navigation"' in template, "Astro navigation missing")
require(re.search(r'<header\b[^>]*class="[^"]*header', template),
        "Astro header missing")
# The template's active 'Уход' selection must not appear on legal pages.
template = template.replace('aria-current="page"', "")

# The base HTML is authoritative: use only the unique main content from
# staged legal files, preserving every paragraph in both approved documents.
for route in ROUTES:
    staged_html = (STAGED / route / "index.html").read_text(encoding="utf-8")
    staged_main = require(MAIN_RE.search(staged_html), f"Missing main: {route}")
    staged_open = require(
        re.match(r"<main\b[^>]*>", staged_main.group(0)),
        f"Missing main opening tag: {route}",
    )
    main_inner = staged_main.group(0)[staged_open.end():-len("</main>")]
    require(main_inner.strip(), f"Empty legal content: {route}")
    built_main = template_open + main_inner + "</main>"

    html = MAIN_RE.sub(lambda _: built_main, template, count=1)
    title = require(
        re.search(r"<title>([\s\S]*?)</title>", staged_html),
        f"Missing title: {route}",
    ).group(1)
    html, count = re.subn(r"<title>[\s\S]*?</title>",
                          lambda _: "<title>" + title + "</title>", html, count=1)
    require(count == 1, f"Missing template title: {route}")
    require("</head>" in html, "Missing closing head")
    html = html.replace("</head>", '<link rel="stylesheet" href="/legal-pages/legal.css?v=3"></head>', 1)

    # Replace care page's meta description with a legal-document description.
    description = {
        "information": "Правовые документы студии Xeni_brows: публичная оферта и политика обработки персональных данных.",
        "offer": "Публичная оферта на оказание услуг Xeni_brows.",
        "privacy": "Политика обработки персональных данных Xeni_brows.",
    }[route]
    html = re.sub(
        r'<meta\s+name="description"\s+content="[^"]*"\s*/?>',
        lambda _: f'<meta name="description" content="{description}">',
        html,
        count=1,
    )
    output = SITE / route / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")

(SITE / "legal-pages").mkdir(parents=True, exist_ok=True)
(SITE / "legal-pages" / "legal.css").write_bytes((STAGED / "legal.css").read_bytes())
(SITE / "legal-pages" / "mobile-nav.css").write_bytes((STAGED / "mobile-nav.css").read_bytes())

# Normalize only the footer navigation on all pages in the ZIP, preserving
# existing headers, original functionality, document bodies and layouts.
for path in SITE.rglob("*.html"):
    html = path.read_text(encoding="utf-8")
    if '</head>' in html and '/legal-pages/mobile-nav.css' not in html:
        html = html.replace('</head>', '<link rel="stylesheet" href="/legal-pages/mobile-nav.css?v=1"></head>', 1)
    if FOOTER_RE.search(html):
        html = FOOTER_RE.sub(normalize_footer, html)
    path.write_text(html, encoding="utf-8")

# Fail deployment if a client-facing page would have the wrong mobile header,
# missing document, inconsistent footer, or duplicated navigation.
routes_to_audit = ("", "care", "services", "portfolio", "training",
                   "about", "contacts", "information", "offer", "privacy")
for route in routes_to_audit:
    path = SITE / route / "index.html" if route else SITE / "index.html"
    if not path.exists() and route not in ROUTES:
        continue
    html = require(path.read_text(encoding="utf-8"), f"Missing page: {path}")
    require('class="menu-toggle"' in html, f"Mobile hamburger absent: {path}")
    require('id="navigation"' in html, f"Navigation absent: {path}")
    require(len(FOOTER_RE.findall(html)) == 1, f"Unexpected footer count: {path}")
    footer = FOOTER_RE.search(html).group(0)
    require(FOOTER_NAV in footer, f"Footer mismatch: {path}")
    require(len(re.findall(r'<header\b', html)) == 1, f"Header mismatch: {path}")
    print(f"OK: /{route}/ shared header, mobile menu and three-link footer")

print("Approved legal pages use the original site's responsive shell.")
