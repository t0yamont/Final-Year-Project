"""Build the dissertation draft from the report sources using python-docx."""

import argparse
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "report"
TITLE = "Electrical Energy Deployment on a Bahrain Qualifying Lap"
CHAPTERS = (
    "01_introduction", "02_related_work", "03_data", "04_methods",
    "06_results", "07_conclusion", "08_professional_practice",
)
FIGURES = {
    "01_silverstone_dp_energy": (
        "Model-only Silverstone lap with a 56 m/s rolling boundary. The bounded planner and work-matched "
        "spread share almost identical delivered wheel work. Curves show requested and delivered power, "
        "energy recovered at the battery and stored energy by distance. Run silverstone-model-only-001."
    ),
    "01_controller_comparison": (
        "Direct training on the central Bahrain vehicle. Finish-speed error and feasible time relative "
        "to spread use both replay grids. Cumulative wheel assist and stored energy use the primary grid. "
        "Each method and actor width includes all three final checkpoints. Run bahrain-algorithm-width-001."
    ),
    "01_bahrain_wheel_assist": (
        "Modelled Bahrain deployment at central grip, with the timing line as the distance origin. "
        "Colour shows mean delivered wheel power in kW per action block. Run bahrain-deployment-zones-001."
    ),
    "03_bahrain_matched_by_distance": (
        "Cumulative wheel-work difference (kJ) and time saved (s) from the timing line (km), "
        "at both matched-wheel-work targets. Positive time means the selected allocation is ahead. "
        "Run bahrain-equal-work-001."
    ),
    "01_paired_transfer": (
        "Observed and simulated speed (km/h) and simulated minus observed time (s) versus distance "
        "(km) for the centreline and lap-13 path on driver 22’s Bahrain laps 2, 5 and 13. "
        "Run bahrain-driver-transfer-001."
    ),
    "01_bahrain_learned_transfer": (
        "Frozen learned controllers transferred to the calibrated Bahrain vehicle. "
        "Finish-speed error (m/s), feasible time saving (s), and cumulative wheel-work difference "
        "(kJ) along the lap (km) are relative to the target or selected schedule. "
        "Run bahrain-learned-transfer-001."
    ),
}
TABLES = {
    "Event role": (
        "OpenF1 2025 acquisition and first-pass screening by preassigned event role. "
        "Run openf1-dataset-003."
    ),
    "Shared range from line (m)": (
        "Repeated deployment locations across three grip settings and two grids, with minimum "
        "and maximum wheel work and separate-lap speed errors. Run bahrain-zone-support-001."
    ),
    "Primary-grid comparison": (
        "Primary-grid lap times (s) for the earlier regenerative Sakhir reference vehicle. "
        "Runs regeneration-multiseed-001 and regeneration-dp-001."
    ),
    "Event and role": (
        "Mean qualifying lap/DRS-group acceleration RMSE (m/s²) across the validation and final-test events. "
        "Runs session-mix-validation-002 and session-mix-final-001."
    ),
}
INLINE = re.compile(r"(\[([^\]]+)\]\(([^)]+)\)|\[@([\w-]+)(?:,\s*([^\]]+))?\]|\*\*([^*]+)\*\*|(?<!\*)\*([^*]+)\*|`([^`]+)`)")
LINKS = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def node(tag, **attrs):
    element = OxmlElement(tag)
    for key, val in attrs.items():
        element.set(qn("w:" + key), str(val))
    return element


def bookmark(paragraph, name, identifier):
    paragraph._p.insert(1, node("w:bookmarkStart", id=identifier, name=name))
    paragraph._p.append(node("w:bookmarkEnd", id=identifier))


def hyperlink(paragraph, label, target, *, internal=False):
    link = node("w:hyperlink", anchor=target) if internal else node("w:hyperlink")
    if not internal:
        link.set(qn("r:id"), paragraph.part.relate_to(target, RT.HYPERLINK, is_external=True))
    run = node("w:r")
    formatting = node("w:rPr")
    formatting.append(node("w:color", val="234F6F"))
    formatting.append(node("w:u", val="single"))
    run.append(formatting)
    value = node("w:t")
    value.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    value.text = label
    run.append(value)
    link.append(run)
    paragraph._p.append(link)


def bibliography():
    source = (REPORT / "references.bib").read_text(encoding="utf-8-sig")
    fields = {}
    for match in re.finditer(r"^@\w+\{([^,]+),\s*\n(.*?)^\}", source, re.M | re.S):
        fields[match[1]] = {
            key.lower(): re.sub(r"[{}]", "", value).replace("--", "–")
            for key, value in re.findall(r"^\s*(\w+)\s*=\s*\{(.*)\},?\s*$", match[2], re.M)
        }
    return fields


def configure(doc):
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.left_margin = section.right_margin = Cm(2.35)
    section.top_margin, section.bottom_margin = Cm(2.15), Cm(2.15)
    section.footer_distance = Cm(1.2)
    section.different_first_page_header_footer = True
    doc.settings.element.append(node("w:updateFields", val="true"))
    page = section.footer.paragraphs[0]
    page.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    page._p.append(node("w:fldSimple", instr="PAGE"))
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Cambria", Pt(11.5)
    normal.paragraph_format.line_spacing = 1.19
    normal.paragraph_format.space_after = Pt(6.5)
    normal.paragraph_format.widow_control = True
    for name, size in {
        "Title": 28, "Subtitle": 12, "Heading 1": 21, "Heading 2": 14,
        "Heading 3": 12, "List Number": 11.5, "List Bullet": 11.5, "Caption": 11,
    }.items():
        style = doc.styles[name]
        style.font.name, style.font.size = "Cambria", Pt(size)
        style.font.color.rgb = RGBColor.from_string("000000")
        if name.startswith("Heading"):
            style.paragraph_format.keep_with_next = True
            style.paragraph_format.space_before = Pt(15)
            style.paragraph_format.space_after = Pt(7)
    title_properties = doc.styles["Title"]._element.pPr
    border = title_properties.find(qn("w:pBdr"))
    if border is not None:
        title_properties.remove(border)
    doc.styles["Caption"].font.italic = False
    doc.styles["Caption"].font.bold = False
    doc.styles["Caption"].paragraph_format.line_spacing = 1.12
    doc.styles["Caption"].paragraph_format.space_before = Pt(6)
    doc.styles["Caption"].paragraph_format.space_after = Pt(11)
    doc.core_properties.title = TITLE
    doc.core_properties.subject = "COM3001 technical dissertation draft"
    doc.core_properties.author = ""
    doc.core_properties.keywords = "Bahrain, Formula 1, qualifying, energy deployment, simulation"


class Draft:
    def __init__(self):
        self.doc = Document()
        configure(self.doc)
        self.bib = bibliography()
        self.cited = {}
        self.inserted = set()
        self.table_count = 0
        self.equation_count = 0
        self.broken_links = set()

    def text(self, paragraph, value):
        end = 0
        for match in INLINE.finditer(value):
            paragraph.add_run(value[end:match.start()])
            _, label, target, key, locator, bold, italic, fixed = match.groups()
            if target:
                if target.startswith(("../", "./")) or "://" not in target:
                    if not (REPORT / target.split("#", 1)[0]).exists():
                        self.broken_links.add(target)
                        paragraph.add_run(label)
                        end = match.end()
                        continue
                hyperlink(paragraph, label, target)
            elif key:
                assert key in self.bib, f"Missing reference {key}"
                number = self.cited.setdefault(key, len(self.cited) + 1)
                suffix = f", {locator}" if locator else ""
                hyperlink(paragraph, f"[{number}{suffix}]", "Ref_" + key, internal=True)
            elif bold:
                paragraph.add_run(bold).bold = True
            elif italic:
                paragraph.add_run(italic).italic = True
            else:
                paragraph.add_run(fixed).font.name = "Consolas"
            end = match.end()
        paragraph.add_run(value[end:])

    def paragraph(self, value, style=None):
        paragraph = self.doc.add_paragraph(style=style)
        self.text(paragraph, value)
        return paragraph

    def caption(self, label, text):
        paragraph = self.doc.add_paragraph(style="Caption")
        paragraph.paragraph_format.keep_together = True
        paragraph.add_run(label + " ").bold = True
        paragraph.add_run(text)
        return paragraph

    def figure(self, target):
        source = REPORT / Path(target).with_suffix(".png")
        stem = source.stem
        description = FIGURES.get(stem)
        if description is None or stem in self.inserted:
            return
        self.inserted.add(stem)
        paragraph = self.doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.keep_with_next = True
        paragraph.paragraph_format.space_after = Pt(0)
        width = 14.2 if stem == "01_bahrain_wheel_assist" else 16.3
        picture = paragraph.add_run().add_picture(str(source), width=Cm(width))
        picture._inline.docPr.set("descr", description)
        self.caption(f"Figure {len(self.inserted)}.", description)

    def table(self, lines):
        rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
        labels, spec, *values = rows
        table = self.doc.add_table(rows=0, cols=len(labels))
        table.autofit = False
        widths = [10.5, 5.8] if len(labels) == 2 else [16.3 / len(labels)] * len(labels)
        if labels[0] == "Shared range from line (m)":
            widths = [3.45, 4.2, 3.0, 5.65]
        if labels[0] == "Event role":
            widths = [4.4, 2.5, 2.5, 2.6, 4.3]
        if labels[0] == "Event and role":
            widths = [4.5, 2.9, 2.65, 3.25, 3]
        for column, width in zip(table.columns, widths):
            column.width = Cm(width)
        borders = node("w:tblBorders")
        for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
            borders.append(node("w:" + side, val="single", sz=4, color="D9D9D9"))
        table._tbl.tblPr.append(borders)
        margins = node("w:tblCellMar")
        for side in ("top", "bottom", "left", "right"):
            margins.append(node("w:" + side, w=85, type="dxa"))
        table._tbl.tblPr.append(margins)
        self.table_count += 1
        for index, line in enumerate([labels, *values]):
            row = table.add_row()
            assert len(line) == len(labels), f"Malformed table row {line}"
            row._tr.get_or_add_trPr().append(node("w:cantSplit"))
            if index == 0:
                row._tr.get_or_add_trPr().append(node("w:tblHeader"))
            for cell, width, alignment, value in zip(row.cells, widths, spec, line):
                cell.width = Cm(width)
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                paragraph = cell.paragraphs[0]
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.13
                paragraph.paragraph_format.keep_with_next = True
                if alignment.endswith(":"):
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                self.text(paragraph, value)
                if index == 0:
                    for run in paragraph.runs:
                        run.bold = True
                    cell._tc.get_or_add_tcPr().append(node("w:shd", fill="E6EDF3"))
        self.caption(f"Table {self.table_count}.", TABLES.get(labels[0], " · ".join(labels) + "."))

    def equation(self, text):
        self.equation_count += 1
        paragraph = self.doc.add_paragraph()
        formatting = paragraph.paragraph_format
        formatting.left_indent = Cm(0.5)
        formatting.tab_stops.add_tab_stop(Cm(14.7), WD_TAB_ALIGNMENT.RIGHT)
        formatting.keep_together = True
        for i, line in enumerate(text.splitlines()):
            if i:
                paragraph.add_run().add_break()
            paragraph.add_run(line.strip().replace(" * ", " × ")).font.name = "Cambria Math"
            if i == 0:
                paragraph.add_run(f"\t({self.equation_count})")

    def chapter(self, source, number=None):
        counters = [0, 0]
        for block in re.split(r"\n\s*\n", source.strip()):
            if block.startswith("#"):
                level, heading = block.split(" ", 1)
                heading = re.sub(r"([A-Za-z0-9])[:?]", r"\1", heading)
                if len(level) == 1:
                    paragraph = self.doc.add_heading(f"{number}  {heading}", 1)
                    paragraph.paragraph_format.page_break_before = True
                    bookmark(paragraph, f"Chapter_{number}", number)
                else:
                    index = len(level) - 2
                    counters[index] += 1
                    if index == 0:
                        counters[1] = 0
                    section = ".".join(map(str, [number, *counters[:index + 1]]))
                    self.doc.add_heading(f"{section}  {heading}", len(level))
            elif block.startswith("```"):
                self.equation("\n".join(block.splitlines()[1:-1]))
            elif block.startswith("|"):
                self.table(block.splitlines())
            else:
                items = block.splitlines()
                if all(re.match(r"^(?:[-*]|\d+\.) ", item) for item in items):
                    for item in items:
                        marker, value = item.split(" ", 1)
                        style = "List Bullet" if marker in ("-", "*") else None
                        self.paragraph(value if style else item, style)
                else:
                    paragraph = self.paragraph(" ".join(items))
                    if block.rstrip().endswith((" was", " is", " as follows")):
                        paragraph.paragraph_format.keep_with_next = True
                for target in LINKS.findall(block):
                    self.figure(target)

    def references(self):
        paragraph = self.doc.add_heading("References", 1)
        paragraph.paragraph_format.page_break_before = True
        bookmark(paragraph, "References", 8)
        for key, number in self.cited.items():
            entry = self.bib[key]
            authors = ", ".join(
                " ".join(reversed(name.split(", ", 1))) for name in entry["author"].split(" and ")
            )
            p = self.doc.add_paragraph()
            p.paragraph_format.keep_together = True
            p.paragraph_format.line_spacing = 1.10
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.left_indent = Cm(0.9)
            p.paragraph_format.first_line_indent = Cm(-0.9)
            p.paragraph_format.tab_stops.add_tab_stop(Cm(0.9))
            p.add_run(f"[{number}]\t{authors} ({entry.get('year', 'n.d.')}). ")
            p.add_run(entry["title"] + ". ").italic = True
            venue = entry.get("journal") or entry.get("booktitle") or entry.get("howpublished")
            if not venue and entry.get("eprint"):
                venue = "arXiv:" + entry["eprint"]
            volume = entry.get("volume", "")
            if "number" in entry:
                volume += "(" + entry["number"] + ")"
            tail = ", ".join(filter(None, (venue, volume, entry.get("pages"), entry.get("publisher"))))
            if tail:
                p.add_run(tail + ". ")
            target = entry.get("url")
            if "doi" in entry:
                target = "https://doi.org/" + entry["doi"]
                hyperlink(p, target, target)
            elif target:
                hyperlink(p, "Source", target)
            bookmark(p, "Ref_" + key, 100 + number)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, nargs="?", default=REPORT / "Bahrain_deployment_draft.docx")
    args = parser.parse_args()
    draft = Draft()
    chapters = [
        re.sub(r"<!--.*?-->", "", (REPORT / (name + ".md")).read_text(encoding="utf-8-sig"), flags=re.S)
        for name in CHAPTERS
    ]
    abstract = re.search(r"^## Abstract\s*\n(.*?)(?=^##? |\Z)", chapters[0], re.M | re.S)
    assert abstract, "Missing Abstract in the introduction"
    title = draft.doc.add_paragraph(TITLE, "Title")
    title.paragraph_format.space_before = Pt(100)
    draft.doc.add_paragraph("COM3001 Professional Projects", "Subtitle")
    draft.doc.add_paragraph("Technical dissertation draft")
    p = draft.doc.add_paragraph("November 2026")
    p.paragraph_format.space_before = Pt(24)
    opening = draft.doc.add_heading("Abstract", 1)
    opening.paragraph_format.page_break_before = True
    for paragraph in re.split(r"\n\s*\n", abstract[1].strip()):
        draft.paragraph(" ".join(paragraph.splitlines()))
    chapters[0] = (chapters[0][:abstract.start()] + "\n\n" + chapters[0][abstract.end():]).strip()
    draft.doc.add_heading("Contents", 2)
    for number, chapter in enumerate([*chapters, "# References"], 1):
        name = chapter.splitlines()[0].removeprefix("# ").strip()
        p = draft.doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(16.3), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        is_chapter = number <= len(chapters)
        target = f"Chapter_{number}" if is_chapter else "References"
        hyperlink(p, f"{number}  {name}" if is_chapter else name, target, internal=True)
        p.add_run("\t")
        p._p.append(node("w:fldSimple", instr=f"PAGEREF {target} \\h"))
    for number, chapter in enumerate(chapters, 1):
        draft.chapter(chapter, number)
    draft.references()
    assert draft.inserted == set(FIGURES), f"Missing figures: {set(FIGURES) - draft.inserted}"
    draft.doc.save(args.output)
    print(f"{args.output}  |  {len(chapters)} chapters, {len(draft.cited)} references, "
          f"{len(draft.inserted)} figures, {draft.table_count} tables")
    if draft.broken_links:
        print("Project source labels without local paths:", sorted(draft.broken_links))


if __name__ == "__main__":
    main()
