"""Construye el informe final (.docx) a partir de docs/informe_final/*.md.

Uso (desde la raíz del repo, con el entorno del proyecto + python-docx):

    pip install python-docx
    python scripts/build_informe.py            # escribe docs/Informe_Grupo4_FakeNews.docx

- Las secciones están en docs/informe_final/ y se ordenan por nombre de archivo.
- Las cifras del texto se escriben como <<clave:formato>> y se reemplazan con los valores que calcula
  `valores()` directamente de results/*.csv, de modo que ningún número del informe se teclea a mano.
- Las ecuaciones ($$...$$) se dibujan como imágenes con matplotlib (mathtext).
- Los textos entre [[...]] quedan resaltados en amarillo: son pendientes que el equipo debe completar.
"""
from __future__ import annotations

import hashlib
import re
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from docx import Document  # noqa: E402
from docx.enum.section import WD_ORIENT  # noqa: E402,F401
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Emu, Inches, Pt, RGBColor  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ROOT / "docs" / "informe_final"
OUT = ROOT / "docs" / "Informe_Grupo4_FakeNews.docx"
GREEN = RGBColor(0x1F, 0x5F, 0x2E)
GRAY = RGBColor(0x55, 0x55, 0x55)
TEXT_W = 6.5  # pulgadas útiles en Letter con márgenes de 1"

sys.path.insert(0, str(ROOT / "scripts"))
from informe_valores import valores  # noqa: E402


# ----------------------------------------------------------------------------- utilidades de texto

GREEK = {
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ", r"\sigma": "σ", r"\omega": "ω", r"\Delta": "Δ",
    r"\infty": "∞", r"\langle": "⟨", r"\rangle": "⟩", r"\cdot": "·", r"\times": "×", r"\approx": "≈", r"\ge": "≥",
    r"\le": "≤", r"\to": "→", r"\sim": "∼", r"\ ": " ", r"\,": " ",
}
SUB = str.maketrans("0123456789+-=()aeoxhklmnpst", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜ")
SUP = str.maketrans("0123456789+-=()in", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁱⁿ")


def latex_inline(s: str) -> str:
    """LaTeX sencillo -> texto Unicode (para $...$ dentro de un párrafo)."""
    for k, v in GREEK.items():
        s = s.replace(k, v)
    s = re.sub(r"\\(?:text|mathrm)\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"(\1)/(\2)", s)
    s = re.sub(r"_\{([^}]*)\}", lambda m: m.group(1).translate(SUB), s)
    s = re.sub(r"_([0-9A-Za-z])", lambda m: m.group(1).translate(SUB), s)
    s = re.sub(r"\^\{([^}]*)\}", lambda m: m.group(1).translate(SUP), s)
    s = re.sub(r"\^([0-9])", lambda m: m.group(1).translate(SUP), s)
    return s.replace("{", "").replace("}", "").replace("\\", "")


def fill_values(text: str, vals: dict) -> str:
    """Reemplaza <<clave:formato>> por el valor calculado a partir de los CSV."""
    def rep(m):
        key, fmt = m.group(1), m.group(2)
        if key not in vals:
            raise KeyError(f"Valor desconocido en el informe: <<{key}>>")
        v = vals[key]
        if fmt and fmt.endswith("%"):          # ".1%" -> "6.5 %" (espacio fino a la española)
            return f"{format(100 * v, fmt[:-1] + 'f')} %"
        return format(v, fmt) if fmt else str(v)
    return re.sub(r"<<([A-Za-z0-9_]+)(?::([^>]+))?>>", rep, text)


# ----------------------------------------------------------------------------- ecuaciones

_EQ_CACHE = Path(tempfile.gettempdir()) / "informe_eq"
_EQ_CACHE.mkdir(exist_ok=True)


def render_equation(latex: str) -> Path:
    """Dibuja una ecuación (mathtext de matplotlib) y devuelve el PNG (fondo transparente)."""
    latex = re.sub(r"\\text\{", r"\\mathrm{", " ".join(latex.split()))
    key = hashlib.md5(latex.encode()).hexdigest()[:12]
    path = _EQ_CACHE / f"eq_{key}.png"
    if not path.exists():
        fig = plt.figure(figsize=(0.1, 0.1))
        fig.text(0, 0, f"${latex}$", fontsize=15)
        fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.04, transparent=True)
        plt.close(fig)
    return path


# ----------------------------------------------------------------------------- docx helpers

def set_cell_shading(cell, hex_fill: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def set_table_borders(table, color: str = "BBBBBB") -> None:
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.insert_element_before(borders, "w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook", "w:tblCaption",
                                "w:tblDescription")


def set_cell_margins(table, top=40, bottom=40, left=70, right=70) -> None:
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for k, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{k}")
        el.set(qn("w:w"), str(v))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.insert_element_before(mar, "w:tblLook", "w:tblCaption", "w:tblDescription")


def add_hyperlink(paragraph, text: str, url: str, size: float | None = None) -> None:
    part = paragraph.part
    r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                          is_external=True)
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), r_id)
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    c = OxmlElement("w:color")
    c.set(qn("w:val"), "0563C1")
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(c)
    if size:
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(int(size * 2)))
        rPr.append(sz)
    rPr.append(u)
    r.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    r.append(t)
    h.append(r)
    paragraph._p.append(h)


def add_field(paragraph, instr: str) -> None:
    for kind, txt in (("begin", None), (None, instr), ("separate", None), ("text", "1"), ("end", None)):
        r = OxmlElement("w:r")
        if kind in ("begin", "separate", "end"):
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            r.append(fc)
        elif kind is None:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = txt
            r.append(it)
        else:
            t = OxmlElement("w:t")
            t.text = txt
            r.append(t)
        paragraph._p.append(r)


INLINE = re.compile(
    r"(\[\[.+?\]\]|\*\*.+?\*\*|\*[^*\s][^*]*?\*|`[^`]+`|\[[^\]]+\]\(https?://[^)]+\)|\$[^$]+\$)"
)


def add_inline(paragraph, text: str, size: float | None = None, bold=False, italic=False, color=None) -> None:
    """Agrega texto con **negrita**, *cursiva*, `código`, enlaces, $math$ y [[pendientes]] resaltados."""
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("[[") and part.endswith("]]"):
            run = paragraph.add_run(part[2:-2])
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW
            run.bold = True
        elif part.startswith("**") and part.endswith("**"):
            add_inline(paragraph, part[2:-2], size, True, italic, color)
            continue
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
            run.font.size = Pt((size or 11) - 1)
            run.font.color.rgb = RGBColor(0x8B, 0x1A, 0x1A)
            run.bold, run.italic = bold, italic
            continue
        elif part.startswith("[") and "](" in part:
            m = re.match(r"\[([^\]]+)\]\((https?://[^)]+)\)", part)
            add_hyperlink(paragraph, m.group(1), m.group(2), size)
            continue
        elif part.startswith("$") and part.endswith("$"):
            run = paragraph.add_run(latex_inline(part[1:-1]))
            run.italic = True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            add_inline(paragraph, part[1:-1], size, bold, True, color)
            continue
        else:
            run = paragraph.add_run(part)
        if size:
            run.font.size = Pt(size)
        if bold:
            run.bold = True
        if italic:
            run.italic = True
        if color is not None:
            run.font.color.rgb = color


# ----------------------------------------------------------------------------- construcción

class Builder:
    def __init__(self) -> None:
        self.doc = Document()
        self.fig_n = 0
        self.tab_n = 0
        self.headings: list[tuple[int, str]] = []
        self._setup()

    def _setup(self) -> None:
        d = self.doc
        for zoom in d.settings.element.findall(qn("w:zoom")):
            zoom.set(qn("w:percent"), "100")
        sec = d.sections[0]
        sec.page_width, sec.page_height = Inches(8.5), Inches(11)
        for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
            setattr(sec, side, Inches(1))
        st = d.styles
        st["Normal"].font.name = "Calibri"
        st["Normal"].element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
        st["Normal"].font.size = Pt(11)
        st["Normal"].paragraph_format.space_after = Pt(6)
        st["Normal"].paragraph_format.line_spacing = 1.12
        for name, size, before, after in (("Heading 1", 18, 0, 10), ("Heading 2", 14, 14, 6), ("Heading 3", 12, 10, 4),
                                          ("Heading 4", 11, 8, 3)):
            h = st[name]
            h.font.name = "Calibri"
            h.element.rPr.rFonts.set(qn("w:asciiTheme"), "minorHAnsi") if False else None
            h.font.size = Pt(size)
            h.font.bold = True
            h.font.color.rgb = GREEN
            h.paragraph_format.space_before = Pt(before)
            h.paragraph_format.space_after = Pt(after)
            h.paragraph_format.keep_with_next = True
        st["Heading 1"].paragraph_format.page_break_before = True
        # pie de página: número de página
        p = sec.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("Grupo 4 · Propagación de Fake News · página ")
        r.font.size = Pt(9)
        r.font.color.rgb = GRAY
        add_field(p, "PAGE")

    # -- portada e índice
    def cover(self, meta: dict) -> None:
        d = self.doc
        for _ in range(3):
            d.add_paragraph()
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("Universidad del Valle de Guatemala")
        r.font.size, r.font.color.rgb = Pt(13), GRAY
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("Facultad de Ingeniería · Modelación y Simulación")
        r.font.size, r.font.color.rgb = Pt(13), GRAY
        for _ in range(3):
            d.add_paragraph()
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(meta["title"])
        r.font.size, r.bold, r.font.color.rgb = Pt(30), True, GREEN
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(meta["subtitle"])
        r.font.size, r.font.color.rgb = Pt(15), GRAY
        for _ in range(3):
            d.add_paragraph()
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("Proyecto Final · Grupo 4")
        r.bold, r.font.size = True, Pt(14)
        for name, carne in meta["authors"]:
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(2)
            p.add_run(f"{name} · {carne}").font.size = Pt(12)
        for _ in range(3):
            d.add_paragraph()
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run("Repositorio: ").bold = True
        add_hyperlink(p, meta["repo"], meta["repo"])
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run("Video: ").bold = True
        if meta.get("video"):
            add_hyperlink(p, meta["video"], meta["video"])
        else:
            r = p.add_run("ENLACE AL VIDEO: pegar aquí antes de entregar")
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
            r.bold = True
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(meta["date"])
        r.font.size, r.font.color.rgb = Pt(12), GRAY

    def index_placeholder(self):
        """Reserva la página del índice; se llena al final con los títulos recolectados."""
        d = self.doc
        d.add_page_break()          # salto explícito: la portada ocupa una página completa
        p = d.add_paragraph()
        r = p.add_run("Índice")
        r.bold, r.font.size, r.font.color.rgb = True, Pt(18), GREEN
        self._index_anchor = d.add_paragraph()

    def fill_index(self) -> None:
        anchor = self._index_anchor
        parent = anchor._p.getparent()
        pos = parent.index(anchor._p)
        entries = [(lvl, t) for lvl, t in self.headings if lvl <= 2]
        for i, (lvl, text) in enumerate(entries):
            np_ = OxmlElement("w:p")
            parent.insert(pos + 1 + i, np_)
            from docx.text.paragraph import Paragraph
            para = Paragraph(np_, anchor._parent)
            para.paragraph_format.left_indent = Inches(0.0 if lvl == 1 else 0.3)
            para.paragraph_format.space_after = Pt(2 if lvl == 2 else 4)
            r = para.add_run(text)
            r.bold = lvl == 1
            r.font.size = Pt(11 if lvl == 1 else 10)
        note = Paragraph(OxmlElement("w:p"), anchor._parent)
        parent.insert(pos + 1 + len(entries), note._p)
        r = note.add_run("Los títulos usan los estilos de encabezado de Word: para un índice con números de página, "
                         "use Referencias → Tabla de contenido.")
        r.italic, r.font.size, r.font.color.rgb = True, Pt(9), GRAY
        parent.remove(anchor._p)

    # -- bloques
    def heading(self, level: int, text: str) -> None:
        text = text.strip()
        self.headings.append((level, latex_inline(text) if "$" in text else text))
        h = self.doc.add_heading(level=level)
        add_inline(h, text)

    def paragraph(self, text: str, style: str | None = None, align=None, size=None, italic=False, indent=None):
        p = self.doc.add_paragraph(style=style)
        if align == "center":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align == "justify":
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if indent is not None:
            p.paragraph_format.left_indent = Inches(indent)
        add_inline(p, text, size=size, italic=italic)
        return p

    def bullet(self, text: str, level: int = 0) -> None:
        p = self.doc.add_paragraph(style="List Bullet")
        p.paragraph_format.left_indent = Inches(0.3 + 0.25 * level)
        p.paragraph_format.first_line_indent = Inches(-0.2)
        p.paragraph_format.space_after = Pt(2)
        add_inline(p, text)

    def numbered(self, n: str, text: str) -> None:
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.35)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.paragraph_format.space_after = Pt(2)
        p.add_run(f"{n}\t")
        p.paragraph_format.tab_stops.add_tab_stop(Inches(0.35))
        add_inline(p, text)

    def code(self, lines: list[str]) -> None:
        for ln in lines:
            p = self.doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.25)
            p.paragraph_format.space_after = Pt(0)
            pPr = p._p.get_or_add_pPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:color"), "auto")
            shd.set(qn("w:fill"), "F2F2F2")
            pPr.insert_element_before(shd, "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
                                      "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN",
                                      "w:bidi", "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind",
                                      "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
                                      "w:textDirection", "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl",
                                      "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange")
            r = p.add_run(ln if ln else " ")
            r.font.name = "Consolas"
            r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
            r.font.size = Pt(9)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def quote(self, text: str) -> None:
        p = self.paragraph(text, italic=True, indent=0.3)
        p.runs[0].font.color.rgb = GRAY if p.runs else None

    def equation(self, latex: str) -> None:
        for piece in [s for s in re.split(r"\\\\|\n\s*\n", latex) if s.strip()]:
            path = render_equation(piece)
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(4)
            pic = p.add_run().add_picture(str(path))
            max_w = Inches(TEXT_W)
            if pic.width > max_w:
                ratio = max_w / pic.width
                pic.width, pic.height = Emu(int(pic.width * ratio)), Emu(int(pic.height * ratio))
            else:  # el PNG sale a 300 dpi: se reduce a un tamaño de lectura cómodo (≈ texto de 11-12 pt)
                pic.width, pic.height = Emu(int(pic.width * 0.62)), Emu(int(pic.height * 0.62))

    def image(self, caption: str, path: str, width: float = 6.3) -> None:
        full = ROOT / path
        if not full.exists():
            raise FileNotFoundError(f"Figura inexistente: {path}")
        self.fig_n += 1
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_after = Pt(2)
        p.add_run().add_picture(str(full), width=Inches(width))
        c = self.doc.add_paragraph()
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = c.add_run(f"Figura {self.fig_n}. ")
        r.bold, r.font.size = True, Pt(9.5)
        add_inline(c, caption, size=9.5, italic=True)
        c.paragraph_format.space_after = Pt(10)

    def table(self, rows: list[list[str]], caption: str | None = None) -> None:
        header, body = rows[0], rows[1:]
        ncol = len(header)
        if caption:
            self.tab_n += 1
            c = self.doc.add_paragraph()
            c.paragraph_format.keep_with_next = True
            c.paragraph_format.space_after = Pt(3)
            r = c.add_run(f"Tabla {self.tab_n}. ")
            r.bold, r.font.size = True, Pt(9.5)
            add_inline(c, caption, size=9.5, italic=True)
        t = self.doc.add_table(rows=1 + len(body), cols=ncol)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        set_table_borders(t)
        set_cell_margins(t)
        lens = [max(len(re.sub(r"[*`\[\]]", "", str(r[j]))) for r in rows) for j in range(ncol)]
        weights = [min(max(l, 4), 38) ** 0.8 for l in lens]
        widths = [TEXT_W * w / sum(weights) for w in weights]
        fs = 9.5 if ncol <= 5 else 8.5 if ncol <= 8 else 7.5
        for i, row in enumerate([header] + body):
            for j in range(ncol):
                cell = t.cell(i, j)
                cell.width = Inches(widths[j])
                cell.text = ""
                par = cell.paragraphs[0]
                par.paragraph_format.space_after = Pt(0)
                par.paragraph_format.line_spacing = 1.0
                txt = str(row[j]) if j < len(row) else ""
                add_inline(par, txt, size=fs, bold=(i == 0))
                if i == 0:
                    set_cell_shading(cell, "DCEBDD")
                elif i % 2 == 0:
                    set_cell_shading(cell, "F7F7F7")
        sp = self.doc.add_paragraph()
        sp.paragraph_format.space_after = Pt(4)

    # -- markdown
    def markdown(self, text: str, vals: dict) -> None:
        text = re.sub(r"<!--.*?-->", "", fill_values(text, vals), flags=re.S)
        lines = text.split("\n")
        i = 0
        para: list[str] = []
        pending_caption: list[str] = []   # "Tabla: ..." espera a la tabla que sigue

        def flush():
            nonlocal para
            if para:
                self.paragraph(" ".join(s.strip() for s in para))
                para = []

        def flush_caption():
            if pending_caption:
                self.paragraph(pending_caption.pop())

        while i < len(lines):
            ln = lines[i]
            s = ln.strip()
            if s.startswith("```"):
                flush()
                j = i + 1
                block = []
                while j < len(lines) and not lines[j].strip().startswith("```"):
                    block.append(lines[j])
                    j += 1
                self.code(block)
                i = j + 1
                continue
            if s.startswith("$$"):
                flush()
                if s.endswith("$$") and len(s) > 4:
                    self.equation(s[2:-2])
                    i += 1
                    continue
                block = [s[2:]] if len(s) > 2 else []
                j = i + 1
                while j < len(lines) and "$$" not in lines[j]:
                    block.append(lines[j])
                    j += 1
                if j < len(lines):
                    block.append(lines[j].split("$$")[0])
                self.equation("\n".join(block))
                i = j + 1
                continue
            m = re.match(r"^(#{1,4})\s+(.*)$", s)
            if m:
                flush()
                flush_caption()
                self.heading(len(m.group(1)), m.group(2))
                i += 1
                continue
            m = re.match(r"^!\[(.*?)\]\((.*?)\)$", s)
            if m:
                flush()
                cap, path = m.group(1), m.group(2)
                width = 6.3
                mw = re.search(r"\|w=([0-9.]+)$", cap)
                if mw:
                    width, cap = float(mw.group(1)), cap[: mw.start()]
                self.image(cap, path, width)
                i += 1
                continue
            if s.startswith("|"):
                flush()
                block = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    block.append(lines[i].strip())
                    i += 1
                rows = [[c.strip() for c in re.split(r"(?<!\\)\|", r.strip("|"))] for r in block
                        if not re.match(r"^\|?\s*:?-{2,}", r)]
                cap = pending_caption.pop()[6:].strip() if pending_caption else None
                self.table(rows, cap)
                continue
            if s.startswith("Tabla:"):
                flush()
                flush_caption()
                pending_caption.append(s)
                i += 1
                continue
            m = re.match(r"^(\s*)[-*]\s+(.*)$", ln)
            if m and not s.startswith("**") or (m and s.startswith("- ")):
                flush()
                self.bullet(m.group(2), level=len(m.group(1)) // 2)
                i += 1
                continue
            m = re.match(r"^\s*(\d+)\.\s+(.*)$", ln)
            if m:
                flush()
                self.numbered(f"{m.group(1)}.", m.group(2))
                i += 1
                continue
            if s.startswith(">"):
                flush()
                self.quote(s.lstrip("> ").strip())
                i += 1
                continue
            if s == "\\pagebreak":
                flush()
                self.doc.add_page_break()
                i += 1
                continue
            if not s:
                flush()
                i += 1
                continue
            flush_caption()
            para.append(ln)
            i += 1
        flush()
        flush_caption()


def main() -> None:
    vals = valores()
    b = Builder()
    b.cover({
        "title": "Propagación de Fake News",
        "subtitle": "Modelo SEIR-D y simulación basada en agentes sobre redes complejas",
        "authors": [("Camila Richter", "23183"), ("Marinés García", "23391"),
                    ("Juan Francisco Martínez", "23617"), ("Ernesto Asencio", "23009")],
        "repo": "https://github.com/NESHGP04/Proyecto-final-MS",
        "date": "2 de noviembre de 2026",
    })
    b.index_placeholder()
    files = sorted(SECTIONS.glob("[0-9]*.md"))
    if not files:
        raise SystemExit(f"No hay secciones en {SECTIONS}")
    for f in files:
        b.markdown(f.read_text(encoding="utf-8"), vals)
    b.fill_index()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    b.doc.save(OUT)
    print(f"{OUT.relative_to(ROOT)}: {len(files)} secciones, {b.fig_n} figuras, {b.tab_n} tablas")


if __name__ == "__main__":
    main()
