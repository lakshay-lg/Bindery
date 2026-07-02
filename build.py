#!/usr/bin/env python3
"""
bindery build script.
Reads every .md in books/, renders each into a themed book page using
template/page.html + template/style.css, and generates the bookshelf
index. All theming derives from ONE accent color in the book's front
matter, so no book ever needs custom CSS.

Usage: python build.py   ->  outputs to site/
"""
import colorsys, json, os, re, shutil, sys
import markdown
from pygments.formatters import HtmlFormatter

ROOT = os.path.dirname(os.path.abspath(__file__))
BOOKS = os.path.join(ROOT, "books")
TPL = os.path.join(ROOT, "template")
OUT = os.path.join(ROOT, "site")

# ---------- color derivation: one accent -> full palette ----------

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return "#%02X%02X%02X" % tuple(round(c * 255) for c in rgb)

def mix(c1, c2, t):
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))

def derive_palette(accent_hex, flavor):
    a = hex_to_rgb(accent_hex)
    h, l, s = colorsys.rgb_to_hls(*a)
    white, near_black = (1, 1, 1), (0.06, 0.08, 0.07)
    ink = colorsys.hls_to_rgb(h, 0.12, min(s, 0.35))
    return {
        "accent": accent_hex,
        "accent_soft": rgb_to_hex(mix(a, white, 0.88)),
        "bg": rgb_to_hex(mix(a, white, 0.965)),
        "panel": rgb_to_hex(mix(a, white, 0.92)),
        "rule": rgb_to_hex(mix(a, white, 0.80)),
        "ink": rgb_to_hex(ink),
        "muted": rgb_to_hex(mix(ink, white, 0.42)),
        "code_bg": rgb_to_hex(colorsys.hls_to_rgb(h, 0.10, min(s, 0.45))),
        "code_ink": rgb_to_hex(mix(a, white, 0.82)),
        "radius": {"sharp": "4px", "soft": "12px"}.get(flavor, "6px"),
    }

# ---------- front matter ----------

def parse_front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    meta, body = {}, text
    if m:
        body = text[m.end():]
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body

# ---------- book rendering ----------

def render_book(path, prev_next):
    text = open(path, encoding="utf-8").read()
    meta, body = parse_front_matter(text)
    slug = os.path.splitext(os.path.basename(path))[0]
    meta.setdefault("title", slug.replace("-", " ").title())
    meta.setdefault("subtitle", "")
    meta.setdefault("tag", "Field Guide")
    meta.setdefault("accent", "#2E5AAC")
    meta.setdefault("flavor", "sharp")
    meta["slug"] = slug
    pal = derive_palette(meta["accent"], meta["flavor"])

    # strip any hand-written H1/TOC block; the template rebuilds both
    body = body.lstrip("\n")
    body = re.sub(r"^# .*?\n+(\*.*?\*\n+)?(---\n+## Table of Contents.*?---\n)?",
                  "", body, count=1, flags=re.S)

    md = markdown.Markdown(
        extensions=["fenced_code", "tables", "codehilite", "toc"],
        extension_configs={"codehilite": {"guess_lang": False},
                           "toc": {"toc_depth": "2-2"}})
    html_body = md.convert(body)
    html_body = re.sub(
        r'<h2 id="([^"]+)">Chapter (\d+): (.*?)</h2>',
        r'<h2 id="\1"><span class="chnum">CHAPTER \2</span>\3</h2>',
        html_body)

    toc_links, chapters = [], 0
    for tok in md.toc_tokens:
        name = re.sub(r"^Chapter (\d+): ", "", tok["name"])
        num = re.match(r"Chapter (\d+):", tok["name"])
        n = num.group(1) if num else ""
        chapters += bool(num)
        toc_links.append(
            f'<a href="#{tok["id"]}" data-target="{tok["id"]}">'
            f'<span class="num">{n}</span>{name}</a>')
    meta["chapters"] = chapters

    theme_css = ":root{" + ";".join(f"--{k.replace('_','-')}:{v}"
                                    for k, v in pal.items()) + "}"
    prev_b, next_b = prev_next
    nav_prev = (f'<a href="{prev_b["slug"]}.html">← {prev_b["title"]}</a>'
                if prev_b else '<a href="index.html">← Bookshelf</a>')
    nav_next = (f'<a href="{next_b["slug"]}.html">{next_b["title"]} →</a>'
                if next_b else '<a href="index.html">Bookshelf →</a>')

    tpl = open(os.path.join(TPL, "page.html"), encoding="utf-8").read()
    page = (tpl.replace("{{title}}", meta["title"])
               .replace("{{subtitle}}", meta["subtitle"])
               .replace("{{tag}}", meta["tag"])
               .replace("{{theme_css}}", theme_css)
               .replace("{{toc}}", "".join(toc_links))
               .replace("{{body}}", html_body)
               .replace("{{nav_prev}}", nav_prev)
               .replace("{{nav_next}}", nav_next))
    open(os.path.join(OUT, slug + ".html"), "w", encoding="utf-8").write(page)
    return meta

# ---------- index (bookshelf) ----------

def render_index(books):
    cards = []
    for i, b in enumerate(books, 1):
        pal = derive_palette(b["accent"], b.get("flavor", "sharp"))
        cards.append(f"""
<a class="book" href="{b['slug']}.html"
   style="--c:{pal['accent']};--cs:{pal['accent_soft']};--r:{pal['radius']}">
  <div class="spine">{i:02d}</div>
  <div class="cover">
    <div class="tag">{b['tag']}</div>
    <h2>{b['title']}</h2>
    <p>{b['subtitle']}</p>
    <div class="meta">{b['chapters']} chapters</div>
  </div>
</a>""")
    tpl = open(os.path.join(TPL, "index.html"), encoding="utf-8").read()
    page = tpl.replace("{{books}}", "".join(cards)).replace(
        "{{count}}", str(len(books)))
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)

# ---------- main ----------

def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    css = open(os.path.join(TPL, "style.css"), encoding="utf-8").read()
    css += "\n" + HtmlFormatter(style="native").get_style_defs(".codehilite")
    open(os.path.join(OUT, "style.css"), "w", encoding="utf-8").write(css)

    paths = sorted(
        (os.path.join(BOOKS, f) for f in os.listdir(BOOKS) if f.endswith(".md")),
        key=lambda p: (parse_front_matter(open(p, encoding='utf-8').read())[0]
                       .get("order", "99"), p))
    metas = [parse_front_matter(open(p, encoding="utf-8").read())[0] |
             {"slug": os.path.splitext(os.path.basename(p))[0]} for p in paths]
    books = []
    for i, p in enumerate(paths):
        prev_b = metas[i - 1] if i > 0 else None
        next_b = metas[i + 1] if i < len(paths) - 1 else None
        books.append(render_book(p, (prev_b, next_b)))
    render_index(books)
    print(f"Built {len(books)} book(s) -> site/")

if __name__ == "__main__":
    sys.exit(main())
