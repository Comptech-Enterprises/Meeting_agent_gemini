"""Generate the official EHA (Employee Happiness Awards) Insights & Analysis Report with fpdf2.

Structured into 6 fixed sections:
1. Company Information
2. Executive Overview
3. Employee Initiatives & Practices (Pillar-wise analysis)
4. Key Findings & Impact (Measurable outcomes table, survey results, targets)
5. Feedback & Next Steps (Jury observations vs. AI-generated strategic recommendations)
6. Conclusion
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from fpdf import FPDF
from fpdf.fonts import FontFace

import config

log = logging.getLogger(__name__)

# Official EHA Palette
CHARCOAL = (30, 41, 59)     # #1E293B
OFFWHITE = (248, 250, 252)  # #F8FAFC
AMBER = (217, 119, 6)       # #D97706 warm gold/amber
AMBER_BG = (254, 243, 199)  # #FEF3C7 subtle amber fill
TEAL = (13, 148, 136)       # #0D9488
TEAL_BG = (204, 251, 241)   # #CCFBF1
MUTED = (100, 116, 139)     # #64748B
LINE = (226, 232, 240)      # #E2E8F0
SLATE_LIGHT = (203, 213, 225)
SLATE_HEADER = (241, 245, 249)

_LATIN1_MAP = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u00a0": " ", "\u20b9": "Rs.",
})


def clean_company(name: str) -> str:
    """Strip an 'Implied:' prefix and fall back to a generic title."""
    name = re.sub(r"^\s*implied\s*:\s*", "", name or "", flags=re.IGNORECASE).strip()
    if not name or name.lower().startswith("not mentioned"):
        return "Employee Happiness Awards Report"
    return name


class ReportPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(format="A4")
        self.family = "Helvetica"
        self.unicode = False
        self._setup_fonts()
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)
        self.alias_nb_pages()

    def _setup_fonts(self) -> None:
        """Bundled Noto -> Windows Arial -> core Helvetica (Latin-1 sanitised)."""
        candidates = [
            (config.FONTS_DIR / "NotoSans-Regular.ttf", config.FONTS_DIR / "NotoSans-Bold.ttf",
             [(config.FONTS_DIR / "NotoSansDevanagari-Regular.ttf",
               config.FONTS_DIR / "NotoSansDevanagari-Bold.ttf")]),
            (Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\arialbd.ttf"),
             [(Path(r"C:\Windows\Fonts\ARIALUNI.ttf"), None)]),
        ]
        for regular, bold, fallbacks in candidates:
            if not regular.exists():
                continue
            try:
                self.add_font("Main", "", str(regular))
                self.add_font("Main", "B", str(bold if bold and bold.exists() else regular))
                names = []
                for i, (fb_reg, fb_bold) in enumerate(fallbacks):
                    if fb_reg.exists():
                        name = f"Fallback{i}"
                        self.add_font(name, "", str(fb_reg))
                        self.add_font(name, "B", str(fb_bold if fb_bold and fb_bold.exists() else fb_reg))
                        names.append(name)
                if names:
                    self.set_fallback_fonts(names, exact_match=False)
                self.family, self.unicode = "Main", True
                try:
                    self.set_text_shaping(True)
                except Exception as exc:
                    log.warning("Text shaping unavailable (%s).", exc)
                return
            except Exception as exc:
                log.warning("Failed to load font %s: %s", regular, exc)
        log.warning("No Unicode font found; using Helvetica.")

    def t(self, text: Any) -> str:
        text = str(text or "").replace("\r\n", "\n").replace("\t", "    ")
        if self.unicode:
            return text
        return text.translate(_LATIN1_MAP).encode("latin-1", "replace").decode("latin-1")

    def font(self, style: str = "", size: float = 10.5) -> None:
        style_norm = (style or "").upper().strip()
        # Fall back to regular if italic is not registered for the font family
        font_key = f"{self.family.lower()}{style_norm.lower()}"
        if font_key not in self.fonts:
            if "B" in style_norm and f"{self.family.lower()}b" in self.fonts:
                style_norm = "B"
            else:
                style_norm = ""
        self.set_font(self.family, style_norm, size)

    def footer(self) -> None:
        self.set_draw_color(*LINE)
        self.line(20, self.h - 16, self.w - 20, self.h - 16)
        self.set_y(-13)
        self.font("", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, self.t("Employee Happiness Awards  |  Confidential"), align="L")
        self.set_x(20)
        self.cell(0, 6, self.t(f"Page {self.page_no()} of {{nb}}"), align="R")


def _title_block(pdf: ReportPDF, company: str, logo_path: Path | None = None) -> None:
    pdf.set_fill_color(*CHARCOAL)
    pdf.rect(0, 0, pdf.w, 46, style="F")
    pdf.set_fill_color(*AMBER)
    pdf.rect(0, 46, pdf.w, 1.6, style="F")

    # Logo resolution: passed path -> config -> static/eha_logo.png -> logo.png
    logo = logo_path
    if not logo:
        for candidate in [
            config.EHA_LOGO_PATH,
            config.STATIC_DIR / "eha_logo.png",
            config.STATIC_DIR / "logo.png",
            config.BASE_DIR / "logo.png",
            config.STATIC_DIR / "customer_logo.png",
        ]:
            if candidate.is_file():
                logo = candidate
                break

    has_logo = False
    if logo and logo.is_file():
        try:
            pdf.image(str(logo), x=pdf.w - 55, y=9, w=35)
            has_logo = True
        except Exception as exc:
            log.warning("Could not render logo %s: %s", logo, exc)

    if not has_logo:
        # Render a clean, crisp EHA emblem badge in top right
        bx = pdf.w - 55
        by = 10
        pdf.set_draw_color(*AMBER)
        pdf.set_line_width(0.8)
        pdf.set_fill_color(*CHARCOAL)
        pdf.rect(bx, by, 35, 26, style="DF")
        pdf.set_line_width(0.2)
        pdf.set_xy(bx, by + 4)
        pdf.font("B", 13)
        pdf.set_text_color(*AMBER)
        pdf.cell(35, 6, pdf.t("EHA"), align="C")
        pdf.set_xy(bx, by + 12)
        pdf.font("", 6.5)
        pdf.set_text_color(*OFFWHITE)
        pdf.cell(35, 4, pdf.t("AWARDS 2026"), align="C")

    # Header category & company title
    pdf.set_xy(20, 11)
    pdf.font("B", 8.5)
    pdf.set_text_color(*AMBER)
    pdf.cell(0, 5, pdf.t("EHA | INSIGHTS & ANALYSIS REPORT"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(20)
    pdf.set_text_color(*OFFWHITE)
    title_w = pdf.w - 80
    pdf.font("B", 20 if len(company) <= 30 else 16)
    pdf.multi_cell(title_w, 8.5, pdf.t(company), align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(54)


def _details_block(pdf: ReportPDF, details: list[tuple[str, str]]) -> None:
    """Render Section 1: Company Information."""
    w = pdf.w - 40
    col_w = w / 2
    top = pdf.get_y()
    row_h = 13.5
    num_rows = (len(details) + 1) // 2
    total_h = row_h * num_rows + 4

    pdf.set_fill_color(*OFFWHITE)
    pdf.set_draw_color(*LINE)
    pdf.rect(20, top, w, total_h, style="DF")

    for i, (label, value) in enumerate(details):
        x = 24 + (i % 2) * col_w
        y = top + 3 + (i // 2) * row_h
        pdf.set_xy(x, y)
        pdf.font("", 7.5)
        pdf.set_text_color(*MUTED)
        pdf.cell(col_w - 8, 4, pdf.t(label.upper()))

        pdf.set_xy(x, y + 4.2)
        pdf.font("B", 9.5)
        pdf.set_text_color(*CHARCOAL)
        pdf.cell(col_w - 8, 5, pdf.t(value[:55]))

    pdf.set_y(top + total_h + 8)


def _section_heading(pdf: ReportPDF, number: str, title: str) -> None:
    if pdf.get_y() > pdf.h - 45:
        pdf.add_page()
    pdf.font("B", 12.5)
    pdf.set_text_color(*CHARCOAL)
    pdf.cell(0, 7, pdf.t(f"{number}. {title}"), new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y() + 0.5
    pdf.set_fill_color(*AMBER)
    pdf.rect(20, y, 16, 1.2, style="F")
    pdf.set_y(y + 5)


def _render_executive_overview(pdf: ReportPDF, overview: str) -> None:
    if not overview:
        return
    _section_heading(pdf, "2", "Executive Overview")
    w = pdf.w - 40
    pdf.font("", 10)
    pdf.set_text_color(*CHARCOAL)
    paragraphs = [p.strip() for p in overview.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [overview.strip()]
    for p in paragraphs:
        pdf.multi_cell(w, 5.8, pdf.t(p), align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
    pdf.ln(4)


def _render_pillars(pdf: ReportPDF, pillars: list[dict], category: str | None = None) -> None:
    if not pillars:
        return
    _section_heading(pdf, "3", "Employee Initiatives & Practices")
    w = pdf.w - 40

    # Brief intro guideline
    pdf.font("", 9)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        w, 4.8,
        pdf.t("Evidence-based analysis of the organisation's initiatives, programmes, and workplace practices, "
              "structured around the applicable employee lifecycle pillars based on the category and presentation content:"),
        align="L", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.ln(4)

    for item in pillars:
        if pdf.get_y() > pdf.h - 55:
            pdf.add_page()

        pillar_name = item.get("pillar_name") or "Employee Lifecycle Pillar"
        practices = item.get("initiatives_and_practices") or ""
        evidence = item.get("supporting_evidence") or ""

        # Pillar Badge Header
        pdf.set_fill_color(*TEAL_BG)
        pdf.set_draw_color(*TEAL)
        pdf.rect(20, pdf.get_y(), w, 7.5, style="DF")
        pdf.set_x(23)
        pdf.font("B", 10)
        pdf.set_text_color(*TEAL)
        pdf.cell(w - 6, 7.5, pdf.t(f"Pillar: {pillar_name}"), align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2.5)

        # Initiatives & Practices Content
        pdf.font("", 9.5)
        pdf.set_text_color(*CHARCOAL)
        pdf.multi_cell(w, 5.4, pdf.t(practices), align="L", new_x="LMARGIN", new_y="NEXT")

        # Supporting Evidence callout
        if evidence:
            pdf.ln(1.5)
            y0 = pdf.get_y()
            pdf.font("", 8.5)
            pdf.set_text_color(*MUTED)
            pdf.set_x(24)
            pdf.multi_cell(w - 5, 4.6, pdf.t(f"Supporting Evidence: {evidence}"), align="L", new_x="LMARGIN", new_y="NEXT")
            pdf.set_fill_color(*SLATE_LIGHT)
            pdf.rect(20, y0, 1.2, pdf.get_y() - y0, style="F")

        pdf.ln(5)


def _render_key_findings_and_impact(pdf: ReportPDF, impact: dict) -> None:
    if not impact:
        return
    _section_heading(pdf, "4", "Key Findings & Impact")
    w = pdf.w - 40

    outcomes = impact.get("measurable_outcomes") or []
    if outcomes:
        pdf.font("B", 9.5)
        pdf.set_text_color(*TEAL)
        pdf.cell(0, 6, pdf.t("Demonstrated Outcomes & Comparative Metrics (Organisation-Reported)"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)

        # Table rendering with fpdf2
        try:
            head_style = FontFace(color=CHARCOAL, fill_color=SLATE_HEADER, emphasis="B")
            with pdf.table(
                col_widths=(44, 30, 36, 60),
                headings_style=head_style,
                text_align=("LEFT", "LEFT", "LEFT", "LEFT"),
                line_height=5.2,
            ) as table:
                header = table.row()
                header.cell(pdf.t("Metric / KPI"))
                header.cell(pdf.t("Baseline / Target"))
                header.cell(pdf.t("Achieved Result"))
                header.cell(pdf.t("Significance & Context"))

                for i, row_data in enumerate(outcomes):
                    row = table.row()
                    row.cell(pdf.t(row_data.get("metric_name") or ""))
                    row.cell(pdf.t(row_data.get("baseline_or_previous") or "Not stated"))
                    row.cell(pdf.t(row_data.get("achieved_result") or ""))
                    row.cell(pdf.t(row_data.get("context_and_significance") or ""))
            pdf.ln(4)
        except Exception as exc:
            log.warning("Table layout fallback triggered: %s", exc)
            for row_data in outcomes:
                pdf.font("B", 9)
                pdf.set_text_color(*CHARCOAL)
                pdf.cell(w, 5, pdf.t(f"• {row_data.get('metric_name')}: {row_data.get('achieved_result')} (Baseline: {row_data.get('baseline_or_previous')})"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

    survey = impact.get("survey_and_qualitative_feedback")
    if survey:
        if pdf.get_y() > pdf.h - 45:
            pdf.add_page()
        pdf.font("B", 9.5)
        pdf.set_text_color(*TEAL)
        pdf.cell(0, 6, pdf.t("Employee Survey Results & Qualitative Feedback"), new_x="LMARGIN", new_y="NEXT")
        pdf.font("", 9.5)
        pdf.set_text_color(*CHARCOAL)
        pdf.multi_cell(w, 5.2, pdf.t(survey), align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    progress = impact.get("progress_against_objectives")
    if progress:
        if pdf.get_y() > pdf.h - 45:
            pdf.add_page()
        pdf.font("B", 9.5)
        pdf.set_text_color(*TEAL)
        pdf.cell(0, 6, pdf.t("Progress Against Stated Objectives"), new_x="LMARGIN", new_y="NEXT")
        pdf.font("", 9.5)
        pdf.set_text_color(*CHARCOAL)
        pdf.multi_cell(w, 5.2, pdf.t(progress), align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)


def _render_feedback_and_next_steps(pdf: ReportPDF, fb: dict) -> None:
    if not fb:
        return
    _section_heading(pdf, "5", "Feedback & Next Steps")
    w = pdf.w - 40

    jury_obs = fb.get("jury_observations") or []
    if jury_obs:
        pdf.font("B", 9.5)
        pdf.set_text_color(*TEAL)
        pdf.cell(0, 6, pdf.t("Jury Observations & Judging Discussions"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        for jo in jury_obs:
            if pdf.get_y() > pdf.h - 40:
                pdf.add_page()
            q = jo.get("jury_topic_or_question") or ""
            resp = jo.get("organisation_response") or ""
            obs = jo.get("key_observation") or ""

            pdf.font("B", 9)
            pdf.set_text_color(*CHARCOAL)
            pdf.multi_cell(w, 5, pdf.t(f"• Question / Discussion: {q}"), align="L", new_x="LMARGIN", new_y="NEXT")

            if resp:
                pdf.set_x(26)
                pdf.font("", 8.8)
                pdf.set_text_color(*MUTED)
                pdf.multi_cell(w - 6, 4.6, pdf.t(f"Response: {resp}"), align="L", new_x="LMARGIN", new_y="NEXT")

            if obs:
                pdf.set_x(26)
                pdf.font("I", 8.8)
                pdf.set_text_color(*TEAL)
                pdf.multi_cell(w - 6, 4.6, pdf.t(f"Jury Observation: {obs}"), align="L", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2.5)
        pdf.ln(3)

    evidence_gaps = fb.get("presentation_evidence_gaps") or []
    if evidence_gaps:
        if pdf.get_y() > pdf.h - 35:
            pdf.add_page()
        pdf.font("B", 9.5)
        pdf.set_text_color(*AMBER)
        pdf.cell(0, 6, pdf.t("Areas for Evidence Strengthening (Judging Observations)"), new_x="LMARGIN", new_y="NEXT")
        pdf.font("", 9)
        pdf.set_text_color(*CHARCOAL)
        for gap in evidence_gaps:
            pdf.multi_cell(w, 4.8, pdf.t(f"• {gap}"), align="L", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        pdf.ln(3)

    recs = fb.get("ai_recommendations_and_sustainability") or []
    if recs:
        if pdf.get_y() > pdf.h - 45:
            pdf.add_page()
        pdf.font("B", 9.5)
        pdf.set_text_color(*TEAL)
        pdf.cell(0, 6, pdf.t("Strategic Recommendations & Sustainability Roadmap (AI-Generated)"), new_x="LMARGIN", new_y="NEXT")
        pdf.font("", 9)
        pdf.set_text_color(*CHARCOAL)
        for i, rec in enumerate(recs, 1):
            pdf.multi_cell(w, 5, pdf.t(f"{i}. {rec}"), align="L", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)
        pdf.ln(4)


def _render_conclusion(pdf: ReportPDF, conclusion: str) -> None:
    if not conclusion:
        return
    _section_heading(pdf, "6", "Conclusion")
    w = pdf.w - 40

    top = pdf.get_y()
    pdf.font("", 9.5)
    pdf.set_text_color(*CHARCOAL)

    # Render inside an executive highlighted frame
    pdf.set_fill_color(*OFFWHITE)
    pdf.set_draw_color(*AMBER)
    pdf.set_line_width(0.6)

    # Estimate height or wrap in multi_cell
    pdf.multi_cell(w, 5.6, pdf.t(conclusion), align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.set_line_width(0.2)
    pdf.ln(6)


def build_pdf(analysis: dict, source_name: str, report_id: str, generated_at: datetime,
              out_dir: Path | None = None) -> Path:
    """Render the official EHA report to temp/<report_id>.pdf and return the path."""
    out_dir = out_dir or config.TEMP_DIR
    out_dir.mkdir(exist_ok=True)

    comp_info = analysis.get("company_info") or {}
    company = clean_company(comp_info.get("company_name") or analysis.get("company_name", ""))
    category = comp_info.get("award_category") or analysis.get("company_category", "Not mentioned")
    edition = comp_info.get("awards_edition") or config.DEFAULT_AWARDS_EDITION
    industry = comp_info.get("industry") or "Not specified"
    headcount = comp_info.get("employee_headcount") or "Not specified"
    established = comp_info.get("year_of_establishment") or "Not specified"
    presenter = comp_info.get("presenter_name_and_designation") or "Not specified"

    pdf = ReportPDF()
    pdf.add_page()

    # Title block
    _title_block(pdf, company)

    # Section 1: Company Information
    details = [
        ("Company Name", company),
        ("Award Category", category),
        ("Awards Edition", edition),
        ("Industry", industry),
        ("Employee Headcount", headcount),
        ("Year Established", established),
        ("Presenter & Designation", presenter),
    ]
    _details_block(pdf, details)

    # Section 2: Executive Overview
    overview = analysis.get("executive_overview") or analysis.get("summary") or ""
    _render_executive_overview(pdf, overview)

    # Section 3: Employee Initiatives & Practices (Pillars)
    pillars = analysis.get("pillars_analysis") or []
    _render_pillars(pdf, pillars, category)

    # Section 4: Key Findings & Impact
    impact = analysis.get("key_findings_and_impact") or {}
    _render_key_findings_and_impact(pdf, impact)

    # Section 5: Feedback & Next Steps
    feedback = analysis.get("feedback_and_next_steps") or {}
    _render_feedback_and_next_steps(pdf, feedback)

    # Section 6: Conclusion
    conclusion = analysis.get("conclusion") or ""
    _render_conclusion(pdf, conclusion)

    out_path = out_dir / f"{report_id}.pdf"
    pdf.output(str(out_path))
    log.info("EHA Report PDF written to %s", out_path)
    return out_path
