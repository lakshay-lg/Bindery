# The Bindery

A tiny static-site system that binds Markdown files into a shelf of book-styled
guides, deployed on GitHub Pages. One template, one stylesheet, zero per-book
styling. New books are just `.md` files.

**Live site:** `https://bindery.lakshay.app/`

## How it works

```
books/            one .md per book (front matter + chapters). The only thing you ever add.
template/
  page.html       the single page shell every book uses
  index.html      the bookshelf homepage shell
  style.css       the single stylesheet, themed per book via CSS variables
build.py          converts books/ -> site/, derives each book's full palette
                  from ONE accent color in its front matter, builds the shelf
.github/workflows/deploy.yml   builds and deploys on every push to main
PROMPT.md         the reusable prompt for generating a new book with any AI
```

The build derives background, panel, rules, ink, code-block colors, everything,
from the single `accent` hex in each book's front matter. Changing a book's
whole look is a one-line edit. Changing every book's layout is an edit to one
CSS file.

## Add a new book

1. Open `PROMPT.md`, fill the brackets, give it to an AI (or write by hand).
2. Save the output as `books/my-topic.md`.
3. Push. The Action rebuilds and deploys. The shelf updates itself.

Front matter reference:

```yaml
---
title: Understanding X            # book title
subtitle: A foundations guide...  # italic line under the title
tag: X Foundations                # category label (spine/eyebrow)
accent: "#8A4FBE"                 # ONE color; the entire theme derives from it
flavor: sharp                     # sharp (4px radius) | soft (12px)
order: 3                          # shelf and prev/next ordering
---
```

Chapters must be H2s formatted as `## Chapter N: Title`. Everything else is
ordinary Markdown (fenced code with language tags, tables, H3 sub-sections).

## Local preview

```bash
pip install markdown pygments
python build.py
python -m http.server -d site 8080   # open http://localhost:8080
```

## One-time deployment setup

1. Create the GitHub repo, push this folder to `main`.
2. Repo Settings → Pages → Source: **GitHub Actions**.
3. Done. Every push to `main` rebuilds and deploys.
