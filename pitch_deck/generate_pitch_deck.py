#!/usr/bin/env python3
"""
Saga Pitch Deck Generator - WORLD-CLASS VC VERSION

12 slides, proper formatting, optimal space usage, professional design.

Usage:
    python generate_pitch_deck.py [--output path/to/output.pdf]

Requirements:
    pip install reportlab pillow

IMPORTANT: Default output is saga-fe/pitch-files/saga_pitch_deck.pdf
           This directory is PASSWORD PROTECTED via the /pitch route.
           DO NOT output to static/ or any public directory!
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Page dimensions - 16:9 widescreen
PAGE_WIDTH = 13.333 * inch
PAGE_HEIGHT = 7.5 * inch

# Colors
BLACK = colors.black
WHITE = colors.white
DARK_BLUE = colors.Color(0.12, 0.31, 0.47)  # Professional blue
GRAY = colors.Color(0.35, 0.35, 0.35)
LIGHT_GRAY = colors.Color(0.6, 0.6, 0.6)
ACCENT_BLUE = colors.Color(0.2, 0.5, 0.8)

# Paths
SCRIPT_DIR = Path(__file__).parent
ASSETS_DIR = SCRIPT_DIR / "assets"
LOGO_HORIZONTAL_PATH = ASSETS_DIR / "saga-logo-horizontal.png"
ICON_PATH = ASSETS_DIR / "saga-icon.png"

# DEFAULT OUTPUT: Password-protected directory (NOT public static/)
# The pitch-files/ directory is served via /pitch route with password protection
SAGA_ROOT = SCRIPT_DIR.parent.parent  # Goes from pitch_deck -> victor_deployment -> Saga
DEFAULT_OUTPUT_DIR = SAGA_ROOT / "saga-fe" / "pitch-files"


def get_styles():
    """Create professional paragraph styles optimized for 16:9."""
    styles = getSampleStyleSheet()

    # Big title for title slide
    styles.add(ParagraphStyle(
        'BigTitle',
        fontSize=48,
        leading=56,
        textColor=BLACK,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceAfter=20,
    ))

    # Slide title - large and bold
    styles.add(ParagraphStyle(
        'SlideTitle',
        fontSize=36,
        leading=44,
        textColor=BLACK,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceAfter=24,
    ))

    # Key message - bold, impactful
    styles.add(ParagraphStyle(
        'KeyMessage',
        fontSize=24,
        leading=32,
        textColor=BLACK,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceBefore=16,
        spaceAfter=16,
    ))

    # Subheading
    styles.add(ParagraphStyle(
        'Subheading',
        fontSize=18,
        leading=24,
        textColor=DARK_BLUE,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold',
        spaceBefore=16,
        spaceAfter=8,
    ))

    # Body text - centered
    styles.add(ParagraphStyle(
        'BodyCenter',
        fontSize=18,
        leading=26,
        textColor=GRAY,
        alignment=TA_CENTER,
        fontName='Helvetica',
        spaceAfter=12,
    ))

    # Body text - left
    styles.add(ParagraphStyle(
        'BodyLeft',
        fontSize=16,
        leading=24,
        textColor=BLACK,
        alignment=TA_LEFT,
        fontName='Helvetica',
        spaceAfter=8,
    ))

    # Bullet point - with proper indentation and bullet character
    styles.add(ParagraphStyle(
        'SlideBullet',
        fontSize=16,
        leading=24,
        textColor=BLACK,
        alignment=TA_LEFT,
        leftIndent=30,
        firstLineIndent=-15,
        fontName='Helvetica',
        spaceAfter=8,
    ))

    # Quote - italic, gray
    styles.add(ParagraphStyle(
        'Quote',
        fontSize=20,
        leading=28,
        textColor=GRAY,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique',
        spaceBefore=12,
        spaceAfter=12,
    ))

    # Contact info
    styles.add(ParagraphStyle(
        'Contact',
        fontSize=24,
        leading=32,
        textColor=BLACK,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceAfter=8,
    ))

    return styles


class PitchDeckGenerator:
    """Generates world-class VC pitch deck - 12 slides, professional formatting."""

    def __init__(self, output_path: str = None):
        if output_path is None:
            # Default to password-protected pitch-files directory
            DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            output_path = DEFAULT_OUTPUT_DIR / "saga_pitch_deck.pdf"
            print(f"  Output: {output_path} (password-protected)")
            print(f"  WARNING: Do NOT output to static/ or any public directory!")

        self.output_path = Path(output_path)
        self.styles = get_styles()
        self.elements = []

    def add_page_break(self):
        self.elements.append(PageBreak())

    def add_spacer(self, height: float = 0.3):
        self.elements.append(Spacer(1, height * inch))

    def add_title(self, text: str):
        self.elements.append(Paragraph(text, self.styles['SlideTitle']))

    def add_key_message(self, text: str):
        self.elements.append(Paragraph(text, self.styles['KeyMessage']))

    def add_subheading(self, text: str):
        self.elements.append(Paragraph(text, self.styles['Subheading']))

    def add_body(self, text: str, centered: bool = False):
        style = 'BodyCenter' if centered else 'BodyLeft'
        self.elements.append(Paragraph(text, self.styles[style]))

    def add_bullet(self, text: str):
        # Use proper bullet character
        self.elements.append(Paragraph(f"<bullet>&bull;</bullet> {text}", self.styles['SlideBullet']))

    def add_quote(self, text: str):
        self.elements.append(Paragraph(text, self.styles['Quote']))

    def add_logo(self, width: float = 5.0):
        """Add horizontal logo centered."""
        if LOGO_HORIZONTAL_PATH.exists():
            from PIL import Image as PILImage
            with PILImage.open(LOGO_HORIZONTAL_PATH) as img:
                aspect = img.width / img.height
            height = width / aspect
            logo = Image(str(LOGO_HORIZONTAL_PATH), width=width*inch, height=height*inch)
            self.elements.append(logo)

    def add_icon(self, size: float = 1.0):
        """Add globe icon centered."""
        if ICON_PATH.exists():
            icon = Image(str(ICON_PATH), width=size*inch, height=size*inch)
            self.elements.append(icon)

    # =========================================================================
    # 12 SLIDES - WORLD-CLASS VC QUALITY
    # =========================================================================

    def slide_01_title(self):
        """Slide 1: Title - Clean, professional, memorable."""
        self.add_spacer(1.8)
        self.add_logo(width=6.0)
        self.add_spacer(0.8)
        self.add_key_message("Your Judgment. Amplified Beyond Human Scale.")
        self.add_spacer(0.5)
        self.add_quote("What happens when human intuition meets infinite reach?")

    def slide_02_problem(self):
        """Slide 2: The Problem - Emotional hook, clear pain point."""
        self.add_page_break()
        self.add_spacer(0.5)
        self.add_title("The Risks You Can't See")
        self.add_spacer(0.3)

        self.add_key_message("The risks that hurt you aren't the ones you're watching.")

        self.add_spacer(0.4)

        # Create a visual 3-column layout for the examples
        examples = [
            ["A policy shift in Chile", "threatens your lithium exposure"],
            ["A labor dispute in Finland", "cascades into European paper positions"],
            ["A drought in Taiwan", "builds toward a semiconductor shock"],
        ]

        # Use a table for visual impact
        data = [[Paragraph(f"<b>{e[0]}</b><br/><font color='gray'>{e[1]}</font>",
                          ParagraphStyle('ex', fontSize=14, leading=20, alignment=TA_CENTER))
                for e in examples]]

        table = Table(data, colWidths=[3.5*inch, 3.5*inch, 3.5*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ]))
        self.elements.append(table)

        self.add_spacer(0.5)
        self.add_body("You're not failing because you're not smart enough.", centered=True)
        self.add_key_message("No human can watch everything.")

    def slide_03_solution(self):
        """Slide 3: The Solution - What Saga does."""
        self.add_page_break()
        self.add_spacer(0.4)
        self.add_title("Saga: The Living Intelligence Layer")
        self.add_spacer(0.2)

        self.add_quote("See the whole picture - including what you didn't know to look for.")

        self.add_spacer(0.4)

        # Two-column layout using simple HTML paragraphs
        col1_text = """<b>Continuous Monitoring</b><br/>
1,000+ sources analyzed 24/7<br/><br/>
<b>Entity Mapping</b><br/>
Millions of relationships traced"""

        col2_text = """<b>Chain Reaction Detection</b><br/>
Events traced to YOUR positions<br/><br/>
<b>Living Analysis</b><br/>
Your thesis tested daily against new info"""

        style = ParagraphStyle('solcol', fontSize=15, leading=22, textColor=BLACK)
        data = [[Paragraph(col1_text, style), Paragraph(col2_text, style)]]
        table = Table(data, colWidths=[5.0*inch, 5.5*inch])
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 30),
            ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ]))
        self.elements.append(table)

        self.add_spacer(0.5)
        self.add_key_message("Not a snapshot. A living system.")

    def slide_04_differentiation(self):
        """Slide 4: Why We're Different - Category definition."""
        self.add_page_break()
        self.add_spacer(0.4)
        self.add_title("The Category We're Defining")
        self.add_spacer(0.3)

        # Market context
        self.add_body("Palantir built intelligence infrastructure for governments - <b>$400B+</b>", centered=True)
        self.add_body("Recorded Future built it for cybersecurity - <b>$2.7B exit</b>", centered=True)

        self.add_spacer(0.3)
        self.add_key_message("No one has built it for institutional capital.")

        self.add_spacer(0.4)

        # Comparison table - visual and impactful
        data = [
            ['Bloomberg', 'ChatGPT/Perplexity', 'Saga'],
            ['Data Terminal', 'General AI Chat', 'Intelligence Infrastructure'],
            ['What happened', 'Answers questions', "What's building toward YOU"],
            ['$30B revenue', 'Consumer focus', 'Built for capital allocation'],
        ]

        table = Table(data, colWidths=[3.2*inch, 3.2*inch, 3.6*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
            ('BACKGROUND', (2, 0), (2, 0), colors.Color(0.1, 0.4, 0.2)),  # Green for Saga
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 13),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.Color(0.85, 0.85, 0.85)),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (2, 1), (2, -1), colors.Color(0.95, 1.0, 0.95)),  # Light green highlight
        ]))
        self.elements.append(table)

    def slide_05_how_it_works(self):
        """Slide 5: How It Works - Technical credibility without complexity."""
        self.add_page_break()
        self.add_spacer(0.4)
        self.add_title("Infrastructure, Not a Wrapper")
        self.add_spacer(0.2)

        self.add_quote("We don't compete with LLMs. We unleash them.")

        self.add_spacer(0.3)

        self.add_body("For frontier AI to deliver real value, it needs:", centered=True)

        self.add_spacer(0.3)

        # Three pillars - visual layout
        pillars = [
            ["Structured Problems", "Not vague queries - precise,\nwell-formed questions"],
            ["Rich Context", "Knowledge graph with millions\nof entity relationships"],
            ["Time to Work", "Iterative analysis, not\none-shot responses"],
        ]

        data = [[Paragraph(f"<b>{p[0]}</b><br/><br/><font size='12' color='gray'>{p[1]}</font>",
                          ParagraphStyle('pill', fontSize=16, leading=22, alignment=TA_CENTER))
                for p in pillars]]

        table = Table(data, colWidths=[3.3*inch, 3.4*inch, 3.3*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (0, 0), 1, DARK_BLUE),
            ('BOX', (1, 0), (1, 0), 1, DARK_BLUE),
            ('BOX', (2, 0), (2, 0), 1, DARK_BLUE),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        self.elements.append(table)

        self.add_spacer(0.4)
        self.add_key_message("Better AI makes us more valuable, not less.")

    def slide_06_traction(self):
        """Slide 6: Traction - Proof points."""
        self.add_page_break()
        self.add_spacer(0.3)
        self.add_title("Traction & Proof Points")
        self.add_spacer(0.2)

        # Key message up front
        self.add_key_message("Live product. Test customers. Raising to scale - not to build.")

        self.add_spacer(0.2)

        # Two-column layout using simple text bullets
        left_col = """<b>Working Platform</b><br/>
&#8226; 4-6 frontier models running 24/7<br/>
&#8226; Real-time ingestion from 1,000+ sources<br/>
&#8226; Knowledge graph with millions of entities<br/>
&#8226; Multi-agent coordination layer<br/><br/>
<b>Customer Validation</b><br/>
&#8226; Test customers actively using platform<br/>
&#8226; Letters of Intent secured<br/>
&#8226; Target: hedge funds, family offices,<br/>
&nbsp;&nbsp;&nbsp;M&A bankers, commodity traders"""

        right_col = """<b>Competitive Moat</b><br/>
&#8226; Years of entity mapping - not easily replicated<br/>
&#8226; Proprietary multi-agent architecture<br/>
&#8226; Network effects: more data = better patterns<br/>
&#8226; Academic foundation in causal mapping<br/><br/>
<b>Timing Advantage</b><br/>
&#8226; First mover in agentic AI for finance<br/>
&#8226; Building while others are pitching<br/>
&#8226; Infrastructure moat deepens daily"""

        style = ParagraphStyle('col', fontSize=14, leading=22, leftIndent=15)
        data = [[Paragraph(left_col, style), Paragraph(right_col, style)]]
        table = Table(data, colWidths=[5.0*inch, 5.5*inch])
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))
        self.elements.append(table)

    def slide_07_team(self):
        """Slide 7: Team - Credibility."""
        self.add_page_break()
        self.add_spacer(0.5)
        self.add_title("The Team")
        self.add_spacer(0.4)

        self.add_key_message("Victor Appelgren - Founder & CEO")

        self.add_spacer(0.4)

        # Three columns of expertise
        expertise = [
            ["Technical Depth", "Multi-agent AI architectures\nGraph database design\nFrontier model orchestration"],
            ["Domain Expertise", "Portfolio construction\nRisk management\nInstitutional workflows"],
            ["Academic Foundation", "Research on LLMs + graphs\nfor market causality mapping"],
        ]

        data = [[Paragraph(f"<b>{e[0]}</b><br/><br/><font size='13'>{e[1]}</font>",
                          ParagraphStyle('exp', fontSize=15, leading=22, alignment=TA_CENTER))
                for e in expertise]]

        table = Table(data, colWidths=[3.3*inch, 3.4*inch, 3.3*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.97, 0.97, 0.97)),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.Color(0.9, 0.9, 0.9)),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ]))
        self.elements.append(table)

        self.add_spacer(0.5)
        self.add_body("Building with urgency. Hiring key roles with this raise.", centered=True)

    def slide_08_business_model(self):
        """Slide 8: Business Model - Clear unit economics."""
        self.add_page_break()
        self.add_spacer(0.2)
        self.add_title("Business Model")
        self.add_spacer(0.15)

        # Pricing - inline, more compact
        self.add_body("<b>Pricing:</b> Team license ~100K SEK/month | ACV: 1.2M+ SEK (~$120K USD)", centered=False)

        self.add_spacer(0.2)

        # Unit economics table - compact
        data = [
            ['Metric', 'Value', 'Note'],
            ['Gross Margin', '~85%', 'After compute (10%) + data (5%)'],
            ['LTV (5-year)', '4.3M SEK', '10% annual churn assumption'],
            ['CAC', '~100K SEK', 'Founder-led sales initially'],
            ['LTV:CAC', '43x', 'Target benchmark: >3x'],
            ['Payback', '<1 month', 'High ACV covers CAC fast'],
        ]

        table = Table(data, colWidths=[2.0*inch, 1.5*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        self.elements.append(table)

        self.add_spacer(0.25)
        self.add_key_message("Premium pricing justified by alpha generation.")

    def slide_09_the_ask(self):
        """Slide 9: The Ask - Clear, specific, justified."""
        self.add_page_break()
        self.add_spacer(0.2)
        self.add_title("The Ask")
        self.add_spacer(0.1)

        # Status line - crystal clear
        self.add_body("<b>Status:</b> Live product with test customers and LOIs. Raising to scale.", centered=True)
        self.add_spacer(0.15)

        # Deal terms - prominent but compact
        data = [
            ['Raise Amount', '35M SEK (~$3.3M USD)'],
            ['Dilution', '20%'],
            ['Pre-Money', '140M SEK'],
            ['Post-Money', '175M SEK'],
        ]

        table = Table(data, colWidths=[2.5*inch, 3.0*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.97, 0.97, 0.97)),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('BOX', (0, 0), (-1, -1), 2, DARK_BLUE),
        ]))
        self.elements.append(table)

        self.add_spacer(0.2)

        # Use of funds - inline table
        funds_data = [
            ['65% Team', '25% Infrastructure', '10% Operations'],
            ['Scale to 30 people', 'Compute, data, systems', 'Sales, marketing, buffer'],
        ]

        table = Table(funds_data, colWidths=[3.3*inch, 3.3*inch, 3.3*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TEXTCOLOR', (0, 0), (-1, 0), DARK_BLUE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        self.elements.append(table)

        self.add_spacer(0.15)

        # Why 35M - centered and compact
        self.add_body("<b>Why 35M?</b> 22.5M to profitability + 12.5M buffer (10+ months runway)", centered=True)
        self.add_spacer(0.1)
        self.add_key_message("Series A from strength, not desperation.")

    def slide_10_financials(self):
        """Slide 10: Financial Projections - Clean, credible."""
        self.add_page_break()
        self.add_spacer(0.2)
        self.add_title("24-Month Projection")
        self.add_spacer(0.2)

        # Quarterly table
        data = [
            ['', 'Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8'],
            ['Customers', '0', '2', '7', '15', '26', '40', '57', '77'],
            ['Team', '6', '9', '12', '15', '21', '26', '29', '30'],
            ['Revenue (M)', '0', '0.3', '1.5', '3.6', '6.6', '10.5', '15.3', '21.0'],
            ['Expenses (M)', '2.8', '4.1', '5.7', '7.5', '10.3', '13.6', '16.2', '18.4'],
            ['Net (M)', '-2.8', '-3.8', '-4.2', '-3.9', '-3.7', '-3.1', '-0.9', '+2.6'],
            ['Cash (M)', '32', '28', '24', '20', '17', '14', '13', '15'],
        ]

        table = Table(data, colWidths=[1.4*inch] + [0.9*inch]*8)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
            ('BACKGROUND', (5, 0), (-1, 0), colors.Color(0.08, 0.24, 0.38)),  # Year 2 darker
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ('BACKGROUND', (0, 1), (0, -1), colors.Color(0.92, 0.95, 0.98)),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            # Highlight positive net
            ('TEXTCOLOR', (-1, 5), (-1, 5), colors.Color(0.1, 0.5, 0.1)),
        ]))
        self.elements.append(table)

        self.add_spacer(0.25)

        # Key metrics side by side
        metrics = [
            ["Month 5", "First paying customer"],
            ["Month 21", "Breakeven"],
            ["Month 24", "92M SEK ARR"],
            ["Buffer", "12.5M SEK minimum"],
        ]

        data = [[Paragraph(f"<b>{m[0]}</b><br/><font size='11' color='gray'>{m[1]}</font>",
                          ParagraphStyle('met', fontSize=14, leading=20, alignment=TA_CENTER))
                for m in metrics]]

        table = Table(data, colWidths=[2.5*inch]*4)
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, colors.Color(0.9, 0.9, 0.9)),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.Color(0.9, 0.9, 0.9)),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        self.elements.append(table)

        self.add_spacer(0.2)
        self.add_key_message("Series A target: 8-10x ARR = 750M-900M SEK valuation")

    def slide_11_vision(self):
        """Slide 11: The Vision - Endgame."""
        self.add_page_break()
        self.add_spacer(0.2)
        self.add_title("The Endgame")
        self.add_spacer(0.15)

        self.add_body("<b>Today:</b> Saga helps portfolios see chain reactions before they materialize.", centered=True)
        self.add_body("<b>Tomorrow:</b> Every investment decision starts with Saga's intelligence layer.", centered=True)

        self.add_spacer(0.2)

        self.add_key_message("Not a tool. Not a dashboard.")
        self.add_key_message("The nervous system for how capital understands the world.")

        self.add_spacer(0.2)

        # Comparables - inline
        self.add_body("Bloomberg = data | Palantir = defense | Recorded Future = cyber", centered=True)
        self.add_spacer(0.1)
        self.add_quote("Saga = the intelligence layer for capital allocation")

    def slide_12_contact(self):
        """Slide 12: Contact - Clean close."""
        self.add_page_break()
        self.add_spacer(1.2)
        self.add_logo(width=5.5)
        self.add_spacer(0.5)
        self.add_key_message("Your judgment. Amplified beyond human scale.")
        self.add_spacer(0.4)
        self.add_quote("Let's talk.")
        self.add_spacer(0.3)
        self.elements.append(Paragraph("info@saga-labs.com", self.styles['Contact']))

    def generate(self):
        """Generate the full pitch deck PDF."""
        print(f"Generating pitch deck: {self.output_path}")
        print(f"  Logo: {LOGO_HORIZONTAL_PATH} ({'found' if LOGO_HORIZONTAL_PATH.exists() else 'NOT FOUND'})")
        print(f"  Icon: {ICON_PATH} ({'found' if ICON_PATH.exists() else 'NOT FOUND'})")

        # Build all 12 slides
        self.slide_01_title()
        self.slide_02_problem()
        self.slide_03_solution()
        self.slide_04_differentiation()
        self.slide_05_how_it_works()
        self.slide_06_traction()
        self.slide_07_team()
        self.slide_08_business_model()
        self.slide_09_the_ask()
        self.slide_10_financials()
        self.slide_11_vision()
        self.slide_12_contact()

        # Create PDF
        doc = SimpleDocTemplate(
            str(self.output_path),
            pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch,
        )

        doc.build(self.elements)
        print(f"Done! 12-slide pitch deck: {self.output_path}")
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
