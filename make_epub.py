r"""
Pre-process LaTeX source for Pandoc EPUB conversion.

Produces _epub_input.tex by:
- Extracting the document body (strips preamble)
- Removing the titlepage environment (EPUB metadata comes from --metadata flags)
- Inlining \include{} files
- Replacing \sectionline / \sectionlinetwo with \hrulefill (renders as <hr> in EPUB)
"""

import re
import subprocess
import zipfile
from pathlib import Path

BASE = Path(__file__).parent
ORNAMENT = '\n\\hrulefill\n'
EPUB_OUT = BASE / 'trades_unions_and_strikes.epub'
TITLE_PAGE_ENTRY = 'EPUB/text/title_page.xhtml'

CUSTOM_TITLE_PAGE = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB">
<head>
  <meta charset="utf-8" />
  <title>Trades&#x2019; Unions and Strikes: Their Philosophy and Intention</title>
  <link rel="stylesheet" type="text/css" href="../styles/stylesheet1.css" />
</head>
<body epub:type="frontmatter">
<section epub:type="titlepage" class="titlepage tp-page">
  <p class="tp-title">TRADES&#x2019; UNIONS AND STRIKES</p>
  <p class="tp-subtitle">Their Philosophy and Intention</p>
  <hr class="tp-rule"/>
  <p class="tp-by">BY</p>
  <p class="tp-author">T. J. Dunning</p>
  <p class="tp-role">Secretary to the London Consolidated Society of Bookbinders</p>
  <hr class="tp-rule"/>
  <p class="tp-epigraph">&#x201C;United to support, but not combined to injure.&#x201D;</p>
  <hr class="tp-rule"/>
  <p class="tp-publisher">LONDON</p>
  <p class="tp-publisher-detail">Published by the Author, and sold by M. Harley,<br/>No. 5, Raquet Court, Fleet Street. E.C.</p>
  <p class="tp-year">1860.</p>
  <p class="tp-price"><em>Price One Shilling.</em></p>
</section>
</body>
</html>
"""


def read(name):
    return (BASE / name).read_text(encoding='utf-8')


def extract_body(tex):
    m = re.search(r'\\begin\{document\}(.*?)\\end\{document\}', tex, re.DOTALL)
    if not m:
        raise ValueError(r'\begin{document} not found')
    return m.group(1)


def strip_titlepage(tex):
    return re.sub(r'\\begin\{titlepage\}.*?\\end\{titlepage\}', '', tex, flags=re.DOTALL)


def strip_toc_commands(tex):
    tex = re.sub(r'[ \t]*\\tableofcontents[ \t]*\n?', '', tex)
    tex = re.sub(r'[ \t]*\\clearpage[ \t]*\n?', '', tex)
    return tex


def inline_includes(tex):
    def sub(m):
        return read(m.group(1) + '.tex')
    return re.sub(r'\\include\{(\w+)\}', sub, tex)


ROMAN = ['I', 'II', 'III', 'IV', 'V']


def number_chapters(tex):
    counter = iter(ROMAN)
    def repl(m):
        title = m.group(1).lstrip('-').lstrip()
        return f'\\chapter{{{next(counter)}. {title}}}'
    return re.sub(r'\\chapter\{(---[^}]*)\}', repl, tex)


def fix_enumerate_labels(tex):
    old = (
        '    \\begin{enumerate}[label=\\Roman*., leftmargin=2.9cm]\n'
        '        \\item---Wages, and what determines their value.\n'
        '        \\item---Trade Societies, for the protection of wages.\n'
        '        \\item---The means used by them for that purpose.\n'
        '    \\end{enumerate}'
    )
    new = (
        '    \\begin{enumerate}\n'
        '        \\item[I.]---Wages, and what determines their value.\n'
        '        \\item[II.]---Trade Societies, for the protection of wages.\n'
        '        \\item[III.]---The means used by them for that purpose.\n'
        '    \\end{enumerate}'
    )
    return tex.replace(old, new)


def fix_advertisement(tex):
    tex = re.sub(r'[ \t]*\\thispagestyle\{[^}]*\}[ \t]*\n?', '', tex)
    tex = re.sub(r'[ \t]*\\addcontentsline\{[^}]*\}\{[^}]*\}\{[^}]*\}[ \t]*\n?', '', tex)
    tex = re.sub(r'\\scalebox\{[^}]*\}\{\\ding\{[^}]*\}\}', lambda m: '☞', tex)
    return tex


def replace_ornaments(tex):
    repl = lambda m: ORNAMENT
    tex = re.sub(r'\\sectionlinetwo\{[^}]*\}\{[^}]*\}', repl, tex)
    tex = re.sub(r'\\sectionline(?!two)\b', repl, tex)
    return tex


def run_pandoc():
    cmd = [
        'pandoc', str(BASE / '_epub_input.tex'),
        '--from', 'latex', '--to', 'epub3',
        '--output', str(EPUB_OUT),
        "--metadata=title:Trades' Unions and Strikes: Their Philosophy and Intention",
        '--metadata=author:T. J. Dunning',
        '--metadata=date:1860',
        '--metadata=lang:en-GB',
        '--css', str(BASE / 'epub.css'),
        '--epub-chapter-level=1',
        '--toc', '--toc-depth=2',
    ]
    subprocess.run(cmd, check=True)
    print(f'Pandoc generated {EPUB_OUT}')


def patch_epub_title_page():
    tmp = EPUB_OUT.with_suffix('.tmp')
    with zipfile.ZipFile(EPUB_OUT, 'r') as zin:
        with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = (CUSTOM_TITLE_PAGE.encode('utf-8')
                        if item.filename == TITLE_PAGE_ENTRY
                        else zin.read(item.filename))
                zout.writestr(item, data)
    tmp.replace(EPUB_OUT)
    print(f'Patched title page in {EPUB_OUT}')


def main():
    main_tex = read('trades_unions_and_strikes.tex')

    body = extract_body(main_tex)
    body = strip_titlepage(body)
    body = strip_toc_commands(body)
    body = inline_includes(body)
    body = fix_advertisement(body)
    body = number_chapters(body)
    body = fix_enumerate_labels(body)
    body = replace_ornaments(body)

    out = BASE / '_epub_input.tex'
    out.write_text(body.strip() + '\n', encoding='utf-8')
    print(f'Written {out}')
    run_pandoc()
    patch_epub_title_page()


if __name__ == '__main__':
    main()
