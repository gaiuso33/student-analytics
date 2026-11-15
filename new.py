from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

output_path = "/mnt/data/Project_Budget_and_Provisional_Invoices.docx"

doc = Document()
sec = doc.sections[0]
sec.top_margin = Inches(0.55)
sec.bottom_margin = Inches(0.55)
sec.left_margin = Inches(0.65)
sec.right_margin = Inches(0.65)

styles = doc.styles
styles["Normal"].font.name = "Aptos"
styles["Normal"].font.size = Pt(9)
styles["Title"].font.name = "Aptos Display"
styles["Title"].font.size = Pt(23)
styles["Title"].font.bold = True
styles["Heading 1"].font.name = "Aptos Display"
styles["Heading 1"].font.size = Pt(16)
styles["Heading 2"].font.name = "Aptos Display"
styles["Heading 2"].font.size = Pt(11)
styles["Heading 2"].font.bold = True

def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)

def set_cell_text(cell, text, bold=False, color=None, size=8):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(str(text))
    r.bold = bold
    r.font.name = "Aptos"
    r.font.size = Pt(size)
    if color:
        r.font.color.rgb = RGBColor(*color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

def set_repeat_table_header(row):
    trPr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    trPr.append(header)

def add_table(headers, rows, widths=None, font_size=8):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        set_cell_text(table.rows[0].cells[i], h, bold=True, color=(255,255,255), size=font_size)
        shade(table.rows[0].cells[i], "23395B")
    set_repeat_table_header(table.rows[0])
    for row in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            set_cell_text(cells[i], val, size=font_size)
            if len(table.rows) % 2 == 0:
                shade(cells[i], "F2F5F9")
    if widths:
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Inches(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table

def add_project_header(code, name, description):
    doc.add_heading(f"{code}. {name}", level=1)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(description)
    r.italic = True
    r.font.size = Pt(9)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(5)
    r = p.add_run("DRAFT — FOR DISCUSSION  |  Currency: NGN (₦)  |  Prepared: 27 October 2026")
    r.bold = True
    r.font.size = Pt(8)

def add_budget_lines(items, note=None):
    rows = [(i, name, detail, "TBD", "Confirm scope / quote")
            for i, (name, detail) in enumerate(items, 1)]
    add_table(["#", "Budget item", "Scope / notes", "Amount (₦)", "Status"],
              rows, widths=[0.35, 1.55, 3.15, 1.05, 1.0], font_size=7.5)
    if note:
        p = doc.add_paragraph(note)
        p.paragraph_format.space_after = Pt(7)
        for r in p.runs:
            r.italic = True
            r.font.size = Pt(8)

def add_bullets(items):
    for item in items:
        doc.add_paragraph(item, style="List Bullet")

# Cover and portfolio summary
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("PROJECT BUDGET & PROVISIONAL INVOICE REGISTER")
r.bold = True
r.font.name = "Aptos Display"
r.font.size = Pt(21)
r.font.color.rgb = RGBColor(35, 57, 91)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Nine-project planning document | Editable working draft")
r.font.size = Pt(11)
r.font.color.rgb = RGBColor(95, 105, 120)

doc.add_paragraph(
    "Prepared for project planning and budget review. Gbera includes the figures visible in the supplied image. "
    "Other project budgets are itemised as editable planning templates, with amounts left as TBD until scope, "
    "team rates, vendor quotes and timelines are confirmed."
)

doc.add_heading("Portfolio budget summary", level=1)
summary = [
    ("1", "SharpEye (placeholder name)", "Browser extension warning users about scam links", "TBD", "Scope not priced"),
    ("2", "ESS — Enterprise Support Service", "Support system for start-ups and SMEs", "TBD", "Scope not priced"),
    ("3", "Gbera", "Dr Oyamakin’s keke-hailing app", "₦406,225.00", "Supplied-item subtotal"),
    ("4", "IHI Data Hackathons", "Data hackathons solving real-world problems", "TBD", "Scope not priced"),
    ("5", "Swag Republic", "Scope and deliverables to confirm", "TBD", "Clarify project"),
    ("6", "Swag Octopus", "Scope and deliverables to confirm", "TBD", "Clarify project"),
    ("7", "Kaggle Partnership", "Partnership initiative and activities", "TBD", "Confirm deliverables"),
    ("8", "Sọrọ-Soke !!!", "AI-native agentic multilingual CRM solution", "TBD", "Scope not priced"),
    ("9", "MyworkAfrica app V2", "Version 2 product development", "TBD", "Confirm V2 scope"),
]
add_table(["#", "Project", "Description", "Budget total", "Budget status"],
          summary, widths=[0.35, 1.65, 2.95, 1.0, 1.15], font_size=7.5)

doc.add_heading("Important budgeting notes", level=2)
add_bullets([
    "Gbera subtotal is the sum of the eight figures shown in the image. The image specifies a card conversion rate of ₦1,385 per US$1.",
    "The supplied Gbera figures are reproduced as shown. Confirm whether software subscriptions are one-off, monthly, annual or project-duration costs.",
    "TBD means information is not yet available; it is not a zero-cost item and should not be interpreted as a quote.",
    "This is a planning budget and provisional invoice template, not a tax invoice or approved purchase order.",
    "Tax/VAT, contingency, payment terms, foreign-exchange charges and approval status must be confirmed with finance."
])

doc.add_page_break()

# Gbera details
add_project_header("03", "Gbera", "Dr Oyamakin’s keke-hailing app — costs transcribed from the supplied budget image.")
gbera = [
    ("Design Guideline", "Design guideline / reference material", "₦40,000.00", "Supplied"),
    ("MacBook Rental (2 days)", "Temporary laptop rental", "₦50,000.00", "Supplied"),
    ("Transportation (bus stop mapping)", "Local transportation for mapping work", "₦10,000.00", "Supplied"),
    ("Miscellaneous", "Unspecified miscellaneous expenses", "₦50,000.00", "Supplied"),
    ("Hosting ($40)", "Converted at ₦1,385 / US$1", "₦55,400.00", "Supplied"),
    ("Codex ($20)", "Converted at ₦1,385 / US$1", "₦27,700.00", "Supplied"),
    ("Claude Pro ($100)", "Converted at ₦1,385 / US$1", "₦138,500.00", "Supplied"),
    ("ChatGPT Plus ($25)", "Converted at ₦1,385 / US$1", "₦34,625.00", "Supplied"),
]
rows = [(i, name, detail, amount, status) for i, (name, detail, amount, status) in enumerate(gbera, 1)]
rows.append(("", "TOTAL OF SUPPLIED ITEMS", "Excludes any unlisted costs, taxes or contingency", "₦406,225.00", "Verify period / scope"))
add_table(["#", "Budget item", "Scope / notes", "Amount (₦)", "Status"],
          rows, widths=[0.35, 1.55, 3.15, 1.05, 1.0], font_size=7.5)
p = doc.add_paragraph("Source conversion rate: ₦1,385 = US$1. Confirm subscription periods and whether these costs are allocated fully to Gbera.")
for r in p.runs:
    r.italic = True
    r.font.size = Pt(8)

projects = [
    ("01", "SharpEye (placeholder name)", "Browser extension that warns users before they click a scam link.", [
        ("Product discovery & requirements", "User stories, threat model, target browsers and success criteria"),
        ("UX/UI design", "Warning states, permissions, settings and onboarding"),
        ("Browser extension development", "Extension interface, link checking and browser compatibility"),
        ("Threat intelligence / detection", "Scam URL data source, detection rules and update strategy"),
        ("Backend / API (if required)", "URL reputation service, analytics, admin tools or accounts"),
        ("Privacy & security review", "Data minimisation, safe URL handling and abuse prevention"),
        ("QA & browser testing", "Browser support scope, automated and manual testing"),
        ("Store listing & release", "Store assets, documentation and publishing"),
        ("Hosting / APIs / monitoring", "Recurring external API and service fees"),
        ("Maintenance & contingency", "Post-launch fixes and reserve"),
    ]),
    ("02", "ESS — Enterprise Support Service", "Enterprise support system for start-ups and SMEs.", [
        ("Discovery & workflow mapping", "Support processes, roles, SLAs and reporting requirements"),
        ("UX/UI design", "Customer portal, agent workspace and admin screens"),
        ("Frontend application", "Customer and staff-facing interfaces"),
        ("Backend & integrations", "Ticketing, notifications, email/chat and CRM integrations"),
        ("Authentication & access control", "Roles, permissions and audit trail"),
        ("Reporting & analytics", "SLA, ticket volume, response and resolution metrics"),
        ("QA, security & accessibility", "Functional, permission, performance and security testing"),
        ("Deployment & documentation", "Environments, backups, handover and user guides"),
        ("Hosting, email & monitoring", "Recurring platform and service charges"),
        ("Support & contingency", "Support period and reserve"),
    ]),
    ("04", "IHI Data Hackathons", "Data-focused hackathons where participants solve real-world problems.", [
        ("Challenge design & partner coordination", "Problem statements, datasets and judging rubric"),
        ("Venue / virtual event platform", "Venue, connectivity or virtual platform"),
        ("Participant recruitment & communications", "Registration, outreach, marketing and community"),
        ("Data preparation & governance", "Data cleaning, permissions, privacy and documentation"),
        ("Mentors, judges & facilitators", "Honoraria, transport and logistics"),
        ("Prizes & participant support", "Prize pool, stipends or data support"),
        ("Event operations", "Staffing, materials, refreshments and logistics"),
        ("Technology & event website", "Registration, submissions, judging and results"),
        ("Media & documentation", "Photography, reports, demos and post-event showcase"),
        ("Contingency", "Reserve for event-day changes"),
    ]),
    ("05", "Swag Republic", "Project scope and deliverables to be confirmed with the product owner.", [
        ("Discovery & scope definition", "Clarify whether this is a brand, commerce platform, campaign or other deliverable"),
        ("Branding & design", "Identity, visual assets, product or interface design"),
        ("Product / platform build", "Website, app, store or other agreed implementation"),
        ("Content & catalogue setup", "Copy, product data, images or campaign materials"),
        ("Payments / logistics (if applicable)", "Payment provider, delivery, inventory or vendor fees"),
        ("Testing & launch", "QA, launch checklist and documentation"),
        ("Hosting / third-party services", "Recurring costs, if applicable"),
        ("Marketing & operations", "Launch communications and operational costs"),
        ("Maintenance & contingency", "Post-launch support and reserve"),
    ]),
    ("06", "Swag Octopus", "Project scope and deliverables to be confirmed with the product owner.", [
        ("Discovery & scope definition", "Clarify relationship to Swag Republic and distinct deliverables"),
        ("Branding & design", "Identity, visual assets, product or interface design"),
        ("Product / platform build", "Website, app, store or other agreed implementation"),
        ("Content & catalogue setup", "Copy, product data, images or campaign materials"),
        ("Integrations (if applicable)", "Payments, inventory, delivery, APIs or external systems"),
        ("Testing & launch", "QA, launch checklist and documentation"),
        ("Hosting / third-party services", "Recurring costs, if applicable"),
        ("Marketing & operations", "Launch communications and operational costs"),
        ("Maintenance & contingency", "Post-launch support and reserve"),
    ]),
    ("07", "Kaggle Partnership", "Partnership initiative; budget depends on agreed scope and partner commitments.", [
        ("Partnership planning", "Objectives, deliverables, owners, timeline and success measures"),
        ("Challenge / competition costs", "Challenge setup, datasets, evaluation and administration"),
        ("Prizes / incentives", "Cash or non-cash awards, if applicable"),
        ("Data preparation & licensing", "Dataset access, cleaning, privacy and usage rights"),
        ("Community & participant engagement", "Outreach, communications and support"),
        ("Events / workshops", "Webinars, mentor sessions or in-person events"),
        ("Marketing & creative assets", "Campaign materials, landing page and announcements"),
        ("Legal / partnership review", "Terms, brand approvals, data and IP considerations"),
        ("Operations & reporting", "Coordination, measurement and final report"),
        ("Contingency", "Reserve for unplanned partnership costs"),
    ]),
    ("08", "Sọrọ-Soke !!!", "Africa’s Premier AI-Native Agentic Multilingual CRM Solution.", [
        ("Product discovery & architecture", "Personas, workflows, languages, agent boundaries and roadmap"),
        ("UX/UI design", "CRM workflows, conversation views, agent controls and dashboards"),
        ("CRM core development", "Contacts, leads, accounts, pipelines, tasks and permissions"),
        ("Agentic AI development", "Agent orchestration, tools, guardrails, approvals and evaluations"),
        ("Multilingual support", "Language selection, localisation and language quality testing"),
        ("Messaging & channel integrations", "Email, web chat, WhatsApp or other approved channels"),
        ("Data layer & integrations", "Database, imports/exports, APIs and migration"),
        ("Security, privacy & governance", "Access controls, audit logs, retention and data protection review"),
        ("QA & AI evaluation", "Functional testing, hallucination checks, red-teaming and load tests"),
        ("Cloud / model usage / monitoring", "Hosting, model/API usage, logging and observability"),
        ("Deployment, training & documentation", "Release, user training and handover"),
        ("Maintenance & contingency", "Support window and reserve"),
    ]),
    ("09", "MyworkAfrica app V2", "Version 2 of the MyworkAfrica application; final feature scope to be confirmed.", [
        ("V1 review & requirements", "User feedback, analytics, backlog and V2 acceptance criteria"),
        ("UX/UI redesign", "Updated user journeys and interface, as required"),
        ("Frontend development", "New and revised app screens and flows"),
        ("Backend / API changes", "New endpoints, data model changes and integrations"),
        ("Migration & compatibility", "Data migration, backward compatibility and rollout plan"),
        ("Testing & quality assurance", "Regression, device/browser, performance and security tests"),
        ("Deployment & release management", "Staging, production release, rollback and monitoring"),
        ("Documentation & user support", "Release notes, help content and handover"),
        ("Hosting / third-party services", "Incremental recurring cost for V2"),
        ("Maintenance & contingency", "Post-release fixes and reserve"),
    ]),
]

for code, name, description, items in projects:
    doc.add_page_break()
    add_project_header(code, name, description)
    add_budget_lines(items, "Enter estimated quantity, unit rate and amount once scope is confirmed. Where useful, separate internal labour, vendor costs and recurring costs.")

# Editable invoice sheet
doc.add_page_break()
doc.add_heading("Reusable cost-entry / provisional invoice sheet", level=1)
doc.add_paragraph("Copy this page for additional vendors, phases, events or change requests. Complete supplier, dates, quantities and payment terms before treating it as an invoice.")
add_table(["Field", "Value"], [
    ("Project / workstream:", "________________________________________"),
    ("Supplier / cost owner:", "________________________________________"),
    ("Invoice / reference no.:", "________________________________________"),
    ("Issue date:", "________________________________________"),
    ("Due date / payment terms:", "________________________________________"),
    ("Prepared / approved by:", "________________________________________"),
], widths=[2.1, 5.0], font_size=8)
invoice_rows = [(i, "", "", "", "", "") for i in range(1, 9)]
invoice_rows += [("", "", "", "", "SUBTOTAL", ""),
                 ("", "", "", "", "Tax / VAT (if applicable)", ""),
                 ("", "", "", "", "Contingency (approved %)", ""),
                 ("", "", "", "", "TOTAL", "")]
add_table(["#", "Description", "Qty", "Unit rate (₦)", "Line total (₦)", "Notes / status"],
          invoice_rows, widths=[0.3, 2.1, 0.45, 1.0, 1.0, 1.4], font_size=7.5)
doc.add_heading("Approval", level=2)
doc.add_paragraph("Project Manager: ______________________________    Date: ______________")
doc.add_paragraph("Budget Owner / Finance: _________________________    Date: ______________")
doc.add_paragraph("Approver: _______________________________________    Date: ______________")

doc.add_heading("Information needed to finalise all budgets", level=1)
add_bullets([
    "For each project: MVP/V1/V2 scope, must-have features, target launch date and acceptance criteria.",
    "Delivery model: internal team, contractors, agencies or mixed; available team members and rate assumptions.",
    "Whether each line is one-off, monthly, annual, per event or per user; contract duration and renewal dates.",
    "Vendor quotes for hosting, domains, APIs, AI/model usage, messaging, design, devices, venues, prizes and logistics.",
    "Existing assets, infrastructure, credits, partner contributions and costs already paid.",
    "Required contingency percentage, tax treatment, payment terms and approval limits.",
    "For Swag Republic and Swag Octopus: confirm what each product is and whether they share infrastructure or scope.",
    "For Kaggle Partnership and IHI hackathons: confirm expected number of events/challenges, participant count and prize commitments."
])

for section in doc.sections:
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("CONFIDENTIAL WORKING DRAFT • Editable budget template • Not an approved invoice")
    r.font.size = Pt(7)
    r.font.color.rgb = RGBColor(110, 120, 135)

doc.save(output_path)
print(f"Created editable Word document: {output_path}")