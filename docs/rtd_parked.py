#!/usr/bin/env python3
"""Write the "no longer developed" pages that Read the Docs publishes.

    python docs/rtd_parked.py OUTDIR

For every page of the old documentation (each .rst or .md under
docs/source) this writes OUTDIR/<page>.html, and OUTDIR/404.html for any
other address, all with the same notice: PACKAGE is no longer developed and
cubevis replaces it.  Nothing forwards automatically; the notice links to
the cubevis documentation.  The old documentation stays in the archived
repository (and in any older version still active on Read the Docs).

Standard library only.
"""
import sys
from html import escape
from pathlib import Path

PACKAGE = "casagui"
REPLACEMENT = "Its applications, including interactive clean (<code>iclean</code>), continue in <a href=\"https://github.com/casangi/cubevis\">cubevis</a>."          # one sentence: what to use instead
CUBEVIS = "https://casangi.github.io/cubevis/"
REPO = f"https://github.com/casangi/{PACKAGE}"
SOURCE = Path(__file__).resolve().parent / "source"
SKIP = ("_static", "_templates", "extensions", "links")

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{pkg} is no longer developed</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="{cubevis}">
<style>
 body{{font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;max-width:40rem;
      margin:4rem auto;padding:0 1rem;color:#1c2733;line-height:1.55}}
 h1{{font-size:1.6rem;margin-bottom:.4rem}}
 .note{{border-left:4px solid #c27c0e;background:#fdf6e9;padding:.8rem 1rem;margin:1.2rem 0}}
 a{{color:#1f6fb2}} code{{background:#f0f2f4;padding:0 .25rem;border-radius:3px}}
 .small{{font-size:.9rem;color:#57606a}}
</style></head><body>
<h1><code>{pkg}</code> is no longer developed</h1>
<div class="note">
<p>Development of <code>{pkg}</code> has stopped and this documentation is no
longer maintained. {replacement}</p>
<p><strong><a href="{cubevis}">Go to the cubevis documentation &rarr;</a></strong></p>
</div>
<p>Install it with <code>pip install cubevis</code>
(see <a href="{cubevis}applications/installing.html">Installing</a>).</p>
<p class="small">The <code>{pkg}</code> source and its old documentation remain
available, read-only, at <a href="{repo}">{repo}</a>.</p>
</body></html>
"""


def pages():
    for path in sorted(SOURCE.rglob("*")):
        rel = path.relative_to(SOURCE)
        if path.suffix in (".md", ".rst") and rel.parts[0] not in SKIP:
            yield rel.with_suffix("").as_posix()


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    out = Path(argv[1])
    html = PAGE.format(pkg=escape(PACKAGE), replacement=REPLACEMENT,
                       cubevis=CUBEVIS, repo=REPO)
    names = sorted(set(pages()) | {"index"})
    for page in names:
        dest = out / f"{page}.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
    (out / "404.html").write_text(html, encoding="utf-8")
    print(f"{len(names)} pages and 404.html written to {out}")


if __name__ == "__main__":
    main(sys.argv)
