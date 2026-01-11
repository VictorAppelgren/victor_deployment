#!/usr/bin/env python3
"""
Saga Pitch Deck Generator - GOD TIER VERSION v2

Fixes:
- Content fits on single slides (reduced text)
- No URLs on slides
- SVG logo embedded
- Globe icon for visual interest

Usage:
    python generate_pitch_deck.py [--output path/to/output.pdf]

Requirements:
    pip install reportlab svglib
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing

# We use pre-converted PNG files for graphics
HAS_GRAPHICS = True

# Page dimensions - 16:9 widescreen (modern presentation standard)
PAGE_WIDTH = 13.333 * inch   # 16:9 ratio
PAGE_HEIGHT = 7.5 * inch     # Fills screens better than LETTER

# Colors
BLACK = colors.black
WHITE = colors.white
GRAY = colors.Color(0.4, 0.4, 0.4)
LIGHT_GRAY = colors.Color(0.6, 0.6, 0.6)

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
ASSETS_DIR = SCRIPT_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "saga-logo.png"
LOGO_HORIZONTAL_PATH = ASSETS_DIR / "saga-logo-horizontal.png"
ICON_PATH = ASSETS_DIR / "saga-icon.png"
OUTPUT_DIR = SCRIPT_DIR / "output"


def get_styles():
    """Create custom paragraph styles - COMPACT VERSION."""
    styles = getSampleStyleSheet()

    # Title slide - main title
    styles.add(ParagraphStyle(
        'BigTitle',
        parent=styles['Title'],
        fontSize=52,
        leading=60,
        textColor=BLACK,
        alignment=TA_CENTER,
        spaceAfter=12,
        fontName='Helvetica-Bold',
    ))

    # Slide title centered
    styles.add(ParagraphStyle(
        'SlideTitleCenter',
        parent=styles['Heading1'],
        fontSize=28,
        leading=34,
        textColor=BLACK,
        alignment=TA_CENTER,
        spaceAfter=16,
        fontName='Helvetica-Bold',
    ))

    # Key message - bold centered
    styles.add(ParagraphStyle(
        'KeyMessage',
        parent=styles['Normal'],
        fontSize=18,
        leading=26,
        textColor=BLACK,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceBefore=8,
        spaceAfter=8,
    ))

    # Body text - centered
    styles.add(ParagraphStyle(
        'SlideBodyCenter',
        parent=styles['Normal'],
        fontSize=14,
        leading=20,
        textColor=BLACK,
        alignment=TA_CENTER,
        spaceAfter=8,
        fontName='Helvetica',
    ))

    # Body text - left
    styles.add(ParagraphStyle(
        'SlideBody',
        parent=styles['Normal'],
        fontSize=14,
        leading=20,
        textColor=BLACK,
        alignment=TA_LEFT,
        spaceAfter=8,
        fontName='Helvetica',
    ))

    # Bullet points - compact
    styles.add(ParagraphStyle(
        'SlideBullet',
        parent=styles['Normal'],
        fontSize=13,
        leading=18,
        textColor=BLACK,
        alignment=TA_LEFT,
        leftIndent=24,
        spaceAfter=4,
        fontName='Helvetica',
    ))

    # Quote - italic gray
    styles.add(ParagraphStyle(
        'Quote',
        parent=styles['Normal'],
        fontSize=16,
        leading=24,
        textColor=GRAY,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique',
        spaceBefore=8,
        spaceAfter=8,
    ))

    # Section header (for email, etc)
    styles.add(ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontSize=20,
        leading=26,
        textColor=BLACK,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceAfter=8,
    ))

    return styles


class PitchDeckGenerator:
    """Generates the Saga pitch deck PDF - COMPACT, with SVG graphics."""

    def __init__(self, output_path: str = None):
        if output_path is None:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d")
            output_path = OUTPUT_DIR / f"saga_pitch_deck_{timestamp}.pdf"

        self.output_path = Path(output_path)
        self.styles = get_styles()
        self.elements = []

    def add_page_break(self):
        self.elements.append(PageBreak())

    def add_spacer(self, height: float = 0.3):
        self.elements.append(Spacer(1, height * inch))

    def add_title(self, text: str):
        self.elements.append(Paragraph(text, self.styles['SlideTitleCenter']))

    def add_body(self, text: str, centered: bool = True):
        style = 'SlideBodyCenter' if centered else 'SlideBody'
        self.elements.append(Paragraph(text, self.styles[style]))

    def add_bullet(self, text: str):
        self.elements.append(Paragraph(f"  {text}", self.styles['SlideBullet']))

    def add_quote(self, text: str):
        self.elements.append(Paragraph(text, self.styles['Quote']))

    def add_key_message(self, text: str):
        self.elements.append(Paragraph(text, self.styles['KeyMessage']))

    def add_image(self, img_path: Path, width: float = 2.0, height: float = None, preserve_aspect: bool = True):
        """Add a PNG image to the document with proper aspect ratio."""
        if not HAS_GRAPHICS or not img_path.exists():
            return

        # Get actual image dimensions for proper aspect ratio
        from PIL import Image as PILImage
        with PILImage.open(img_path) as pil_img:
            img_w, img_h = pil_img.size
            aspect_ratio = img_w / img_h

        # Calculate height from width if preserving aspect ratio
        if preserve_aspect and height is None:
            calculated_height = width / aspect_ratio
        else:
            calculated_height = height or width

        img = Image(str(img_path), width=width*inch, height=calculated_height*inch)
        self.elements.append(img)

    def add_globe_decoration(self, size: float = 1.2):
        """Add the globe icon as a visual decoration."""
        self.add_image(ICON_PATH, width=size, height=size)

    # =========================================================================
    # SLIDES - COMPACT VERSION
    # =========================================================================

    def slide_01_title(self):
        """Slide 1: Title with horizontal logo (SagaLabs + globe)."""
        self.add_spacer(1.8)

        # Add horizontal logo - auto aspect ratio from actual image dimensions
        if HAS_GRAPHICS and LOGO_HORIZONTAL_PATH.exists():
            self.add_image(LOGO_HORIZONTAL_PATH, width=5.5)
            self.add_spacer(0.5)

        self.add_key_message("Your Judgment. Amplified Beyond Human Scale.")
        self.add_spacer(0.4)
        self.add_quote("What happens when human intuition meets infinite reach?")

    def slide_02_the_truth(self):
        """Slide 2: AI + Human - COMPACT."""
        self.add_page_break()
        self.add_spacer(0.4)
        self.add_title("The Truth About AI + Human")
        self.add_spacer(0.2)

        self.add_key_message(
            "AI can't do what you do. You can't do what AI does.<br/>"
            "Together, you're unstoppable."
        )

        self.add_spacer(0.3)

        self.add_body(
            "The best investment decisions require human judgment - pattern recognition "
            "built over decades, intuition honed through experience."
        )

        self.add_spacer(0.2)

        self.add_body(
            "But human judgment has a scale ceiling. Too many sources, too many entities, "
            "too many chains of events cascading simultaneously."
        )

        self.add_spacer(0.3)
        self.add_key_message("Saga removes that ceiling.")

        # Add small globe
        if HAS_GRAPHICS and ICON_PATH.exists():
            self.add_spacer(0.3)
            self.add_globe_decoration(size=0.8)

    def slide_03_the_problem(self):
        """Slide 3: The blind spots - COMPACT."""
        self.add_page_break()
        self.add_spacer(0.4)
        self.add_title("The Risks You Don't Know You're Taking")
        self.add_spacer(0.2)

        self.add_key_message(
            "The risks that hurt you aren't the ones you're watching.<br/>"
            "They're the ones you didn't know existed."
        )

        self.add_spacer(0.3)

        self.add_bullet("A policy shift in Chile quietly threatens your lithium exposure")
        self.add_bullet("A labor dispute in Finland cascades into your European paper positions")
        self.add_bullet("A drought in Taiwan is building toward a semiconductor shock")

        self.add_spacer(0.3)
        self.add_key_message("You're not failing because you're not smart enough.<br/>No human can watch everything.")

    def slide_04_the_solution(self):
        """Slide 4: The Living Map - COMPACT."""
        self.add_page_break()
        self.add_spacer(0.4)
        self.add_title("The Living Map")
        self.add_spacer(0.2)

        self.add_quote("See the whole picture - including the parts you didn't know to look for.")

        self.add_spacer(0.3)

        self.add_bullet("1000+ sources monitored continuously")
        self.add_bullet("Millions of entity relationships mapped")
        self.add_bullet("Chain reactions traced to YOUR specific positions")
        self.add_bullet("24/7 vigilance - nothing building undetected")

        self.add_spacer(0.3)
        self.add_key_message("Not a snapshot. A living system.")

        # Add globe
        if HAS_GRAPHICS and ICON_PATH.exists():
            self.add_spacer(0.2)
            self.add_globe_decoration(size=0.8)

    def slide_05_conviction(self):
        """Slide 5: Confidence to Conviction - COMPACT."""
        self.add_page_break()
        self.add_spacer(0.4)
        self.add_title("From Confidence to Conviction")
        self.add_spacer(0.2)

        self.add_key_message(
            "Confidence is 'I think I'm right.'<br/>"
            "Conviction is 'I know I've checked.'"
        )

        self.add_spacer(0.3)

        self.add_body(
            "There's a gap between good judgment and total certainty. "
            "It's filled with doubt and the nagging question: What am I missing?"
        )

        self.add_spacer(0.2)

        self.add_bullet("Walk into meetings without hidden doubt")
        self.add_bullet("Defend your thesis knowing you've checked what others haven't")
        self.add_bullet("Sleep better because nothing is building undetected")

        self.add_spacer(0.3)
        self.add_key_message("Same judgment. Complete conviction.")

    def slide_06_living_analysis(self):
        """Slide 6: Analysis That Lives - COMPACT."""
        self.add_page_break()
        self.add_spacer(0.4)
        self.add_title("Analysis That Doesn't Expire")
        self.add_spacer(0.2)

        self.add_quote("A great analysis isn't a document. It's a conversation that never stops.")

        self.add_spacer(0.3)

        self.add_body(
            "Static reports are dead the moment they're written. "
            "Saga keeps analyzing - your thesis tested against every new piece of information, every day."
        )

        self.add_spacer(0.2)

        self.add_bullet("Your thesis, stress-tested daily")
        self.add_bullet("Risks surfaced as they form, not after they hit")
        self.add_bullet("Intelligence that evolves with the market")

        self.add_spacer(0.3)
        self.add_key_message("You shouldn't have to wonder if your analysis is still valid.")

    def slide_07_infrastructure(self):
        """Slide 7: Not a Wrapper - COMPACT."""
        self.add_page_break()
        self.add_spacer(0.4)
        self.add_title("Infrastructure, Not a Wrapper")
        self.add_spacer(0.2)

        self.add_quote("We're not an AI wrapper. We're the infrastructure that lets frontier AI do what it does best.")

        self.add_spacer(0.3)

        self.add_body("For AI to deliver real value, frontier models need:")

        self.add_spacer(0.2)
        self.add_bullet("Structured problems (not vague queries)")
        self.add_bullet("Rich context (not just raw data)")
        self.add_bullet("Time to work iteratively (not one-shot responses)")

        self.add_spacer(0.3)
        self.add_key_message("Better AI makes us more valuable, not less.")

    def slide_08_category(self):
        """Slide 8: Category - COMPACT."""
        self.add_page_break()
        self.add_spacer(0.4)
        self.add_title("The Category We're Defining")
        self.add_spacer(0.2)

        self.add_body("Palantir built intelligence infrastructure for governments - $400B+")
        self.add_body("Recorded Future built it for cybersecurity - $2.7B exit")

        self.add_spacer(0.2)

        self.add_key_message(
            "No one has built it for the trillions in institutional capital<br/>"
            "where human judgment still matters most."
        )

        self.add_spacer(0.3)

        # Comparison table
        data = [
            ['Bloomberg', 'Perplexity', 'Saga'],
            ['Data', 'Search', 'Intelligence'],
            ['What happened', 'Finds info', 'What\'s building toward YOU'],
        ]
        table = Table(data, colWidths=[2.2*inch, 2.2*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.1, 0.1, 0.1)),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.Color(0.85, 0.85, 0.85)),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        self.elements.append(table)

    def slide_09_moat(self):
        """Slide 9: The Moat - COMPACT."""
        self.add_page_break()
        self.add_spacer(0.4)
        self.add_title("The Moat That Deepens Daily")
        self.add_spacer(0.2)

        self.add_body("<b>Network Effects:</b>", centered=False)
        self.add_bullet("Every day of data = Better entity resolution = Smarter patterns")
        self.add_bullet("More customers = Richer graph = Better warnings")

        self.add_spacer(0.2)

        self.add_body("<b>Infrastructure Advantages:</b>", centered=False)
        self.add_bullet("Millions of entities mapped - years to build")
        self.add_bullet("Multi-agent orchestration - proprietary architecture")
        self.add_bullet("Academic foundation in causal mapping research")

        self.add_spacer(0.2)

        self.add_body("<b>Timing:</b>", centered=False)
        self.add_bullet("First mover in agentic AI for financial intelligence")
        self.add_bullet("Building while others are pitching")

        self.add_spacer(0.2)
        self.add_key_message("Infrastructure-level IP that deepens every day.")

    def slide_10_traction(self):
        """Slide 10: Traction - COMPACT."""
        self.add_page_break()
        self.add_spacer(0.4)
        self.add_title("Traction")
        self.add_spacer(0.2)

        self.add_body("<b>Working Platform:</b>", centered=False)
        self.add_bullet("4-6 frontier models running 24/7")
        self.add_bullet("Real-time ingestion from 1000+ sources")

        self.add_spacer(0.2)

        self.add_body("<b>Proprietary Infrastructure:</b>", centered=False)
        self.add_bullet("Graph database with millions of entities")
        self.add_bullet("Multi-agent coordination layer")

        self.add_spacer(0.2)

        self.add_body("<b>Customer Engagement:</b>", centered=False)
        self.add_bullet("Active pilots with hedge funds, family offices ($500M+ AUM)")
        self.add_bullet("Strong pull - repeat engagement")

        self.add_spacer(0.3)
        self.add_key_message("Not a pitch deck company. A working system.")

    def slide_11_team(self):
        """Slide 11: Team - COMPACT."""
        self.add_page_break()
        self.add_spacer(0.4)
        self.add_title("The Team")
        self.add_spacer(0.2)

        self.add_key_message("Victor Appelgren - Founder")

        self.add_spacer(0.2)

        self.add_bullet("Background spanning finance and technology")
        self.add_bullet("Deep domain expertise in strategic decision-making")

        self.add_spacer(0.2)

        self.add_body("<b>Academic Foundation:</b>", centered=False)
        self.add_bullet("Research on graph databases and LLMs for market causality")

        self.add_spacer(0.1)

        self.add_body("<b>Technical Depth:</b>", centered=False)
        self.add_bullet("Multi-agent AI architectures, graph database design")

        self.add_spacer(0.1)

        self.add_body("<b>Domain Expertise:</b>", centered=False)
        self.add_bullet("Portfolio construction, risk management, mandate constraints")

    def slide_12_business_model(self):
        """Slide 12: Business Model & Unit Economics - IMPROVED."""
        self.add_page_break()
        self.add_spacer(0.2)
        self.add_title("Business Model")
        self.add_spacer(0.15)

        # Pricing section
        self.add_body("<b>Pricing Model:</b> Team license (scales with organization size)", centered=False)
        self.add_bullet("Base: ~100,000 SEK/month for teams up to 10 users")
        self.add_bullet("Enterprise: Custom pricing for larger organizations")
        self.add_bullet("Annual Contract Value (ACV): 1.2M+ SEK (~$120K+ USD)")

        self.add_spacer(0.2)

        # Unit economics table - expanded with full terms
        data = [
            ['Metric', 'Value', 'Explanation'],
            ['Gross Margin', '~85%', 'After compute (10%) and data (5%) costs'],
            ['Customer Lifetime Value', '4.3M SEK', '5-year LTV with 10% annual churn'],
            ['Customer Acquisition Cost', '~100K SEK', 'Founder-led sales, low initially'],
            ['LTV to CAC Ratio', '43x', 'Exceptional unit economics (target >3x)'],
            ['Payback Period', '<1 month', 'High ACV covers acquisition cost fast'],
        ]
        table = Table(data, colWidths=[2.0*inch, 1.2*inch, 3.0*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.12, 0.31, 0.47)),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        self.elements.append(table)

        self.add_spacer(0.2)
        self.add_key_message("Premium pricing justified by alpha generation and risk reduction.")

    def slide_13_the_ask(self):
        """Slide 13: The Ask - with specific numbers and clear rationale."""
        self.add_page_break()
        self.add_spacer(0.2)
        self.add_title("The Ask")
        self.add_spacer(0.15)

        # Deal terms
        data = [
            ['Term', 'Value'],
            ['Raise Amount', '35M SEK (~$3.3M USD)'],
            ['Target Dilution', '20%'],
            ['Pre-Money Valuation', '140M SEK'],
            ['Post-Money Valuation', '175M SEK'],
        ]
        table = Table(data, colWidths=[2.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.12, 0.31, 0.47)),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        self.elements.append(table)

        self.add_spacer(0.2)

        # Use of funds - simplified
        self.add_body("<b>Use of Funds:</b>", centered=False)
        self.add_bullet("65% Team - aggressive hiring to 30 people")
        self.add_bullet("25% Infrastructure - compute, data acquisition, systems")
        self.add_bullet("10% Sales, marketing, operations, buffer")

        self.add_spacer(0.15)

        # Why this amount
        self.add_body("<b>Why 35M SEK?</b>", centered=False)
        self.add_bullet("We use 22.5M to reach profitability (Month 21)")
        self.add_bullet("12.5M buffer = 10+ months runway if sales slow")
        self.add_bullet("Reach Series A from position of strength, not desperation")

    def slide_14_cashflow(self):
        """Slide 14: 24-Month Cash Flow Projection - ALIGNED WITH EXCEL MODEL."""
        self.add_page_break()
        self.add_spacer(0.2)
        self.add_title("24-Month Financial Projection")
        self.add_spacer(0.15)

        # Quarterly summary table - ALIGNED WITH EXCEL MODEL
        # Based on: 90K salary + 32% avgift, first customer M5, higher costs
        data = [
            ['', 'Q1', 'Q2', 'Q3', 'Q4', 'Y2 Q1', 'Y2 Q2', 'Y2 Q3', 'Y2 Q4'],
            ['Customers', '0', '2', '7', '15', '26', '40', '57', '77'],
            ['Team Size', '6', '9', '12', '15', '21', '26', '29', '30'],
            ['Revenue (M)', '0', '0.3', '1.5', '3.6', '6.6', '10.5', '15.3', '21.0'],
            ['Expenses (M)', '2.8', '4.1', '5.7', '7.5', '10.3', '13.6', '16.2', '18.4'],
            ['Net (M)', '-2.8', '-3.8', '-4.2', '-3.9', '-3.7', '-3.1', '-0.9', '+2.6'],
            ['Cash (M)', '32', '28', '24', '20', '17', '14', '13', '15'],
        ]
        table = Table(data, colWidths=[1.2*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.12, 0.31, 0.47)),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
            ('BACKGROUND', (0, 1), (0, -1), colors.Color(0.85, 0.89, 0.95)),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            # Highlight Y2 columns
            ('BACKGROUND', (5, 0), (-1, 0), colors.Color(0.08, 0.24, 0.38)),
        ]))
        self.elements.append(table)

        self.add_spacer(0.25)

        # Key insights - UPDATED TO MATCH MODEL
        self.add_body("<b>Key Financial Highlights:</b>", centered=False)
        self.add_bullet("First paying customer Month 5 - product validation before scaling")
        self.add_bullet("Breakeven Month 21 - capital deployed aggressively for growth")
        self.add_bullet("12.5M SEK buffer at lowest point - 10+ months runway protection")

        self.add_spacer(0.15)

        self.add_body("<b>Series A Position (Month 18-24):</b>", centered=False)
        self.add_bullet("92M SEK ARR, 85% gross margin, 77 customers")
        self.add_bullet("Target: 100-150M SEK raise at 8-10x ARR (750M-900M valuation)")
        self.add_bullet("5x+ return potential for seed investors")

        self.add_spacer(0.15)
        self.add_key_message("High margins + strong growth = premium Series A terms.")

    def slide_15_endgame(self):
        """Slide 15: Endgame - COMPACT."""
        self.add_page_break()
        self.add_spacer(0.4)
        self.add_title("The Endgame")
        self.add_spacer(0.2)

        self.add_body("<b>Today:</b> Saga helps portfolios see chain reactions before they materialize.")
        self.add_spacer(0.1)
        self.add_body("<b>Tomorrow:</b> Every investment decision starts with Saga's intelligence layer.")

        self.add_spacer(0.3)

        self.add_key_message(
            "Not a tool. Not a dashboard.<br/>"
            "The nervous system for how capital understands the world."
        )

        self.add_spacer(0.3)

        self.add_body("Bloomberg = data layer. Palantir = defense intelligence. Recorded Future = cyber.")

        self.add_spacer(0.2)

        self.add_key_message("Saga = the intelligence layer for capital allocation.")

    def slide_16_contact(self):
        """Slide 16: Contact - with horizontal logo."""
        self.add_page_break()
        self.add_spacer(1.5)

        # Add horizontal logo - auto aspect ratio from actual image dimensions
        if HAS_GRAPHICS and LOGO_HORIZONTAL_PATH.exists():
            self.add_image(LOGO_HORIZONTAL_PATH, width=5.5)
            self.add_spacer(0.5)

        self.add_key_message("Your judgment. Amplified beyond human scale.")

        self.add_spacer(0.5)

        self.add_quote("Interested? Let's talk.")

        self.add_spacer(0.3)

        self.elements.append(Paragraph(
            "info@saga-labs.com",
            self.styles['SectionHeader']
        ))

    def generate(self):
        """Generate the full pitch deck PDF."""
        print(f"Generating pitch deck: {self.output_path}")

        if HAS_GRAPHICS:
            print(f"  Logo: {LOGO_PATH} ({'found' if LOGO_PATH.exists() else 'NOT FOUND'})")
            print(f"  Icon: {ICON_PATH} ({'found' if ICON_PATH.exists() else 'NOT FOUND'})")

        # Build all slides (16 total)
        self.slide_01_title()
        self.slide_02_the_truth()
        self.slide_03_the_problem()
        self.slide_04_the_solution()
        self.slide_05_conviction()
        self.slide_06_living_analysis()
        self.slide_07_infrastructure()
        self.slide_08_category()
        self.slide_09_moat()
        self.slide_10_traction()
        self.slide_11_team()
        self.slide_12_business_model()
        self.slide_13_the_ask()
        self.slide_14_cashflow()
        self.slide_15_endgame()
        self.slide_16_contact()

        # Create PDF with 16:9 widescreen dimensions
        doc = SimpleDocTemplate(
            str(self.output_path),
            pagesize=(PAGE_WIDTH, PAGE_HEIGHT),  # 16:9 widescreen
            leftMargin=1.0*inch,
            rightMargin=1.0*inch,
            topMargin=0.6*inch,
            bottomMargin=0.6*inch,
        )

        doc.build(self.elements)
        print(f"Done! PDF: {self.output_path}")
        return self.output_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate Saga pitch deck PDF")
    parser.add_argument("--output", "-o", help="Output PDF path")
    args = parser.parse_args()

    generator = PitchDeckGenerator(output_path=args.output)
    generator.generate()


if __name__ == "__main__":
    main()
