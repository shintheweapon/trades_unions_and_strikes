r"""
Pre-process LaTeX source for Pandoc EPUB conversion.

Produces _epub_input.tex by:
- Extracting the document body (strips preamble)
- Removing the titlepage environment (EPUB metadata comes from --metadata flags)
- Inlining \include{} files
- Replacing \sectionline / \sectionlinetwo with \hrulefill (renders as <hr> in EPUB)
"""

import re
from pathlib import Path

BASE = Path(__file__).parent
ORNAMENT = '\n\\hrulefill\n'


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


def replace_ornaments(tex):
    repl = lambda m: ORNAMENT
    tex = re.sub(r'\\sectionlinetwo\{[^}]*\}\{[^}]*\}', repl, tex)
    tex = re.sub(r'\\sectionline(?!two)\b', repl, tex)
    return tex


def main():
    main_tex = read('trades_unions_and_strikes.tex')

    body = extract_body(main_tex)
    body = strip_titlepage(body)
    body = strip_toc_commands(body)
    body = inline_includes(body)
    body = replace_ornaments(body)

    out = BASE / '_epub_input.tex'
    out.write_text(body.strip() + '\n', encoding='utf-8')
    print(f'Written {out}')


if __name__ == '__main__':
    main()
