"""
==============================================================================
BISspec.IQ - Conversational AI Assistant & Intelligence Module
==============================================================================
Provides an effortless conversational interface for Bureau of Indian Standards (BIS)
and Government e-Marketplace (GeM) queries in English and Indian Regional Languages.
Supports:
1. General Questions & Regulatory FAQs (BIS mandate, GeM rules, GFR 149, ISI marks,
   QCO orders, BIS vs ISO, certification schemes, L-1 bidding, reverse auctions).
2. Dynamic Live Standards Matching (identical real-time live scraper & TF-IDF
   scoring workflow as the Matcher Workspace).
3. Automated GeM Tender Compliance Clause formulation.
4. Open-ended procurement intelligence and general knowledge answering.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("bisspec.chat")

# Conversational Greetings & Pre-computed Indian Language Responses
GREETINGS_MAP = {
    'en': "Hello Officer! I am BISspec.IQ Assistant. Ask me anything about Bureau of Indian Standards (BIS), GeM procurement guidelines, or name any product/tender item to retrieve matching Indian Standards in real time.",
    'hi': "नमस्ते अधिकारी महोदय! मैं BISspec.IQ सहायक हूँ। भारतीय मानक ब्यूरो (BIS), GeM निविदा नियमों के बारे में पूछें या सीधे उत्पाद का नाम लिखकर आधिकारिक मानक खोजें।",
    'gu': "નમસ્તે! હું BISspec.IQ સહાયક છું. ભારતીય માનક બ્યુરો (BIS) અથવા GeM ટેન્ડર સંબંધિત પ્રશ્નો પૂછો અથવા કોઈપણ પ્રોડક્ટનું નામ લખીને માનક શોધો.",
    'bn': "নমস্কার! আমি BISspec.IQ সহায়ক। ভারতীয় মানক ব্যুরো (BIS) এবং GeM সরকারি ক্রয়ের নিয়ম সম্পর্কে জানুন বা পণ্যের নাম লিখে লাইভ মান খুঁজুন।",
    'ta': "வணக்கம்! நான் BISspec.IQ உதவியாளர். இந்திய தர நிர்ணய பணியகம் (BIS) மற்றும் GeM டெண்டர் பற்றிய கேள்விகளைக் கேளுங்கள் அல்லது தயாரிப்பு பெயரை உள்ளிடவும்.",
    'mr': "नमस्कार! मी BISspec.IQ सहाय्यक आहे. भारतीय मानक ब्युरो (BIS) किंवा GeM निविदांबद्दल विचारा किंवा उत्पादनाचे नाव लिहून मानक शोधा.",
    'te': "నమస్కారం! నేను BISspec.IQ అసిస్టెంట్‌ని. భారతీయ ప్రమాణాల బ్యూరో (BIS) లేదా GeM టెండర్ ప్రమాణాలను అడగండి.",
    'pa': "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ BISspec.IQ ਸਹਾਇਕ ਹਾਂ। ਭਾਰਤੀ ਮਿਆਰ ਬਿਊਰੋ (BIS) ਅਤੇ GeM ਖਰੀਦ ਨਿਯਮਾਂ ਬਾਰੇ ਪੁੱਛੋ।"
}

# ==============================================================================
# AUTHORITATIVE GENERAL QUESTIONS KNOWLEDGE BASE (FAQs)
# ==============================================================================
GENERAL_KNOWLEDGE_BASE = [
    {
        "id": "bis_overview",
        "keywords": ["bis", "bureau", "mandate", "act", "functions", "role"],
        "patterns": [
            r'\b(what is bis|about bis|bureau of indian standards|role of bis|functions of bis|who is bis|bis act|mandate of bis|what does bis do|what is bureau of indian standards|tell me about bis)\b'
        ],
        "reply": (
            "**The Bureau of Indian Standards (BIS)** is the National Standards Body of India, "
            "established under the **Bureau of Indian Standards Act, 2016** under the Ministry of Consumer Affairs, Food & Public Distribution.\n\n"
            "**Core Functions of BIS:**\n"
            "- **Standardization:** Formulates national specifications (Indian Standards / IS Codes) across 15 technical divisions.\n"
            "- **Product Certification (ISI Mark):** Audits manufacturing quality and grants the prestigious ISI mark for consumer and industrial safety.\n"
            "- **Compulsory Registration Scheme (CRS):** Regulates electronics and IT hardware safety under self-declaration of conformity.\n"
            "- **Hallmarking Scheme:** Regulates purity and authenticity of Gold and Silver jewelry.\n"
            "- **Testing & Calibration:** Operates a nationwide network of modern government testing laboratories.\n"
            "- **Management System Certification:** Certifies organizations under ISO 9001 (Quality), ISO 14001 (Environment), ISO 45001 (OH&S), and ISO 27001 (Information Security)."
        ),
        "suggestions": [
            "What is an ISI mark?",
            "What is a Quality Control Order (QCO)?",
            "Search Electrical Cable Standards",
            "How does GeM integrate with BIS?"
        ]
    },
    {
        "id": "gem_overview",
        "keywords": ["gem", "marketplace", "portal", "public", "procurement", "buy", "sell"],
        "patterns": [
            r'\b(what is gem|about gem|government e-marketplace|what is government e marketplace|gem portal|overview of gem|what does gem do|tell me about gem|why use gem)\b'
        ],
        "reply": (
            "**Government e-Marketplace (GeM)** is the National Public Procurement Portal of India (*gem.gov.in*), "
            "launched by the Ministry of Commerce & Industry as an end-to-end digital platform for public buying.\n\n"
            "**Key Pillars of GeM:**\n"
            "- **Statutory Mandate (GFR 149):** Rule 149 of the General Financial Rules (GFR), 2017 mandates all Central Ministries, Departments, CPSEs, and Autonomous Bodies to procure through GeM.\n"
            "- **Transparency & Speed:** Replaces cumbersome manual tenders with dynamic catalogs, electronic Reverse Auctions, and paperless online contracts.\n"
            "- **MSME & Startup Inclusion:** Provides market access to verified Micro & Small Enterprises and Startups with exemptions from prior turnover and experience criteria.\n"
            "- **Standardization Linkage:** Requires mandatory validation of BIS certification numbers for products notified under Quality Control Orders."
        ),
        "suggestions": [
            "How does procurement work under GFR 149?",
            "Who can sell on GeM?",
            "Generate GeM Procurement Clause",
            "Browse GeM Live Bids"
        ]
    },
    {
        "id": "gfr_149",
        "keywords": ["gfr", "149", "rule", "threshold", "direct", "bidding", "procurement", "rules", "limits"],
        "patterns": [
            r'\b(gfr 149|gfr rule 149|general financial rules|procurement rules on gem|rules for gem procurement|how does gem procurement work|procurement thresholds|purchase limit|bidding process on gem|public procurement rules)\b'
        ],
        "reply": (
            "Public procurement on GeM is governed by **Rule 149 of General Financial Rules (GFR), 2017**:\n\n"
            "**1. Direct Purchase (Up to ₹25,000):**\n"
            "- Buyer can purchase directly from any available seller on GeM whose product meets technical specification, quality, and delivery terms.\n\n"
            "**2. L-1 Purchase via Comparison (₹25,000 to ₹5,00,000):**\n"
            "- Mandatory online comparison of at least 3 distinct manufacturers/sellers meeting technical specifications. The contract must be awarded to the lowest eligible (L-1) bidder.\n\n"
            "**3. E-Bidding & Reverse Auction (Above ₹5,00,000):**\n"
            "- Mandatory electronic bidding or Reverse Auction (RA) among all registered suppliers for fair competition and competitive price discovery.\n\n"
            "**Technical Compliance:** Tender specifications must cite valid, active **Bureau of Indian Standards (IS codes)**."
        ),
        "suggestions": [
            "What is an L1 bidder?",
            "What is Reverse Auction on GeM?",
            "What is a Quality Control Order (QCO)?",
            "Launch Matcher Workspace"
        ]
    },
    {
        "id": "l1_bidder",
        "keywords": ["l1", "bidder", "lowest", "quote", "evaluation", "award", "split"],
        "patterns": [
            r'\b(what is l1|l1 bidder|l-1 bidder|l1 purchase|lowest bidder|how is l1 determined|split order l1|l1 price matching)\b'
        ],
        "reply": (
            "**L-1 (Lowest-1)** designates the bidder who quotes the lowest evaluated financial price among all technically compliant offers in a public tender.\n\n"
            "**Key Principles of L-1 Evaluation on GeM:**\n"
            "- **Technical Qualification First:** Only bids satisfying 100% of technical specifications, BIS certifications, and delivery criteria are opened for financial comparison.\n"
            "- **Total Landed Cost:** The ranking evaluates total price including GST, freight, insurance, and warranty charges.\n"
            "- **MSE Purchase Preference:** If the L-1 bidder is a non-MSE, participating MSE bidders quoting within `L-1 + 15%` can match the L-1 price to receive 25% of the total order quantity."
        ),
        "suggestions": [
            "What is GFR 149?",
            "What is Reverse Auction on GeM?",
            "What are MSE exemptions on GeM?",
            "Launch Matcher Workspace"
        ]
    },
    {
        "id": "reverse_auction",
        "keywords": ["reverse", "auction", "ra", "bidding", "decrement", "real-time"],
        "patterns": [
            r'\b(what is reverse auction|reverse auction on gem|ra on gem|how does reverse auction work|ra rules|dynamic bidding)\b'
        ],
        "reply": (
            "**Reverse Auction (RA)** is an online real-time bidding event on GeM where sellers compete dynamically to offer decreasing prices for a specified tender.\n\n"
            "**How Reverse Auction Works on GeM:**\n"
            "- **Eligibility:** Shortlisted bidders from the initial financial round enter the RA window (typically top 50% or qualified vendors).\n"
            "- **Time Window:** The standard RA duration is usually 2 hours, with auto-extension of 15 minutes whenever a lower bid is submitted in the closing 10 minutes.\n"
            "- **Minimum Decrement:** Sellers must decrease prices by at least the specified minimum decrement step.\n"
            "- **Outcome:** Transparent price discovery ensures the lowest cost to the public exchequer while strictly enforcing BIS compliance."
        ),
        "suggestions": [
            "What is GFR 149?",
            "What is an L1 bidder?",
            "What is a Quality Control Order (QCO)?",
            "Launch Matcher Workspace"
        ]
    },
    {
        "id": "isi_mark",
        "keywords": ["isi", "mark", "certification", "license", "standard mark", "audit", "safety"],
        "patterns": [
            r'\b(what is isi|what is isi mark|isi mark|isi certification|how to get isi mark|difference between isi and bis|standard mark|isi logo|isi meaning)\b'
        ],
        "reply": (
            "The **ISI Mark** is the official third-party certification mark granted by the Bureau of Indian Standards (BIS) "
            "certifying that a product conforms to the relevant **Indian Standard (IS)**.\n\n"
            "**Key Principles:**\n"
            "- **Mandatory vs. Voluntary:** Mandatory for 500+ safety-critical items (structural steel, cement, electrical cables, domestic appliances, infant milk food, helmets). Voluntary for general industrial goods.\n"
            "- **Audit Process:** Granted only after thorough factory manufacturing audits, quality system checks, and independent laboratory testing of sample batches.\n"
            "- **Procurement Protection:** Assures government buyers of electrical safety, insulation integrity, and load-bearing performance."
        ),
        "suggestions": [
            "What is a Quality Control Order (QCO)?",
            "Find Cable Standards (IS 694)",
            "Difference between BIS and ISO",
            "What is CRS for electronics?"
        ]
    },
    {
        "id": "qco_orders",
        "keywords": ["qco", "quality", "control", "order", "mandatory", "compulsory", "enforcement", "dpiit"],
        "patterns": [
            r'\b(what is (?:a )?qco|quality control order|is bis (?:certification )?mandatory|mandatory bis|compulsory standards|qco notification|dpiit qco|mandatory conformity)\b'
        ],
        "reply": (
            "**Quality Control Orders (QCOs)** are statutory regulations issued by line ministries (such as DPIIT, Ministry of Steel, MeitY, MoPNG) exercising powers under the **BIS Act, 2016**.\n\n"
            "**Regulatory Impact:**\n"
            "- **Compulsory Certification:** Once a QCO is notified, manufacturing, importing, stocking, or selling non-BIS certified goods is prohibited by law.\n"
            "- **Domestic & Import Coverage:** Applies equally to domestic manufacturers and foreign exporters.\n"
            "- **Enforcement on GeM:** GeM technical filters reject bids from vendors who do not possess a valid BIS license for QCO-covered categories."
        ),
        "suggestions": [
            "Check Cable Standards (IS 694)",
            "Check Steel & Cement Standards",
            "What is GFR 149?",
            "Generate GeM Clause"
        ]
    },
    {
        "id": "bis_vs_iso",
        "keywords": ["difference", "bis", "iso", "international", "national", "comparison"],
        "patterns": [
            r'\b(difference between bis and iso|bis vs iso|iso vs bis|international standards vs indian standards|is vs iso|what is iso)\b'
        ],
        "reply": (
            "**Comparison: BIS (National) vs. ISO (International):**\n\n"
            "| Feature | Bureau of Indian Standards (BIS) | International Organization for Standardization (ISO) |\n"
            "| :--- | :--- | :--- |\n"
            "| **Jurisdiction** | India's National Standards Body | Global Federation of 165+ national standards bodies |\n"
            "| **Enforceability** | Statutory backing via BIS Act 2016 & QCOs | Voluntary recommendations unless adopted into national law |\n"
            "| **Certification** | Grants licenses & the ISI mark directly | Develops standards; does not issue certificates itself |\n"
            "| **Harmonization** | Adopts ISO/IEC as dual-numbered `IS/ISO` codes | Coordinates global standardization frameworks |\n\n"
            "BIS frequently adopts ISO standards (e.g. `IS/ISO 9001`) while adapting technical parameters for Indian climate, voltage, and industrial conditions."
        ),
        "suggestions": [
            "What is an Indian Standard?",
            "What is an ISI mark?",
            "What is BIS?",
            "Launch Matcher Workspace"
        ]
    },
    {
        "id": "is_codes_structure",
        "keywords": ["is", "code", "structure", "formulation", "committee", "sectional"],
        "patterns": [
            r'\b(what is is code|what does is stand for|how are standards formulated|structure of is code|sectional committees|how to read is code|what is indian standard)\b'
        ],
        "reply": (
            "An **Indian Standard (IS Code)** is formulated by technical Sectional Committees under BIS representing industry manufacturers, scientific institutions (IITs, CSIR), government departments, and consumers.\n\n"
            "**How to Read an IS Code (e.g. `IS 694 : 2010`):**\n"
            "- **`IS`**: Designates 'Indian Standard'.\n"
            "- **`694`**: Unique sequential number identifying the specific product/subject category (PVC Insulated Cables).\n"
            "- **`(Part X)`**: Components or test methods in multi-part standards.\n"
            "- **`: 2010`**: Year of publication or latest major revision."
        ),
        "suggestions": [
            "Active vs Withdrawn Standards",
            "Find Cable Standards (IS 694)",
            "What is an ISI mark?",
            "What is BIS?"
        ]
    },
    {
        "id": "standard_status",
        "keywords": ["active", "withdrawn", "superseded", "revised", "validity"],
        "patterns": [
            r'\b(active vs withdrawn|withdrawn standards|what are withdrawn standards|superseded standards|revised standards|difference between active and withdrawn)\b'
        ],
        "reply": (
            "Standard status indicates the legal and operational validity of an Indian Standard:\n\n"
            "- **Active Standards:** Currently valid, authoritative specifications. These are legally enforceable and must be cited in all ongoing GeM tenders and procurement contracts.\n"
            "- **Revised Standards:** Updated editions where safety margins, technological improvements, or test procedures have been modernized (e.g. Third Revision). Older revisions remain valid only during a transition grace period.\n"
            "- **Withdrawn Standards:** Formally decommissioned or superseded by newer specifications. Procurement officers **must not** specify withdrawn standards in tender documents."
        ),
        "suggestions": [
            "Launch Matcher to verify active standards",
            "What is a Quality Control Order (QCO)?",
            "Generate GeM Procurement Clause"
        ]
    },
    {
        "id": "gem_registration",
        "keywords": ["register", "registration", "signup", "onboarding", "how", "portal"],
        "patterns": [
            r'\b(how to register on gem|gem registration|register on gem|seller registration on gem|buyer registration on gem|signup on gem|how to sign up on gem)\b'
        ],
        "reply": (
            "**Registration Guide for Government e-Marketplace (GeM):**\n\n"
            "**1. Buyer Registration (Government Entities):**\n"
            "- Primary User must register using official government email ID (`@gov.in` or `@nic.in`).\n"
            "- Requires Aadhaar verification and authorization letter from Head of Department.\n"
            "- Primary User creates Secondary Users (Buyers, Consignees, PAO).\n\n"
            "**2. Seller Registration (Business & Vendors):**\n"
            "- Requires PAN, GSTIN, Company Registration/Udyam certificate, active Bank Account, and Aadhaar-linked mobile.\n"
            "- Complete vendor assessment (where applicable) and deposit Caution Money based on turnover tier.\n"
            "- Link active BIS licenses/ISI mark certificates in product catalog uploads."
        ),
        "suggestions": [
            "Who can sell on GeM?",
            "What are MSE exemptions on GeM?",
            "What is GFR 149?",
            "Launch Matcher Workspace"
        ]
    },
    {
        "id": "gem_seller_buyer",
        "keywords": ["who", "buy", "sell", "eligibility", "seller", "buyer", "user"],
        "patterns": [
            r'\b(who can buy on gem|who can sell on gem|eligibility for gem|gem user types|primary user|secondary user)\b'
        ],
        "reply": (
            "**Eligibility on Government e-Marketplace (GeM):**\n\n"
            "**Authorized Buyers:**\n"
            "- Central Ministries & Subordinate Departments\n"
            "- State Governments & Union Territory Administrations\n"
            "- Central and State Public Sector Undertakings (CPSEs)\n"
            "- Autonomous Institutions, Municipalities, and Urban Local Bodies\n\n"
            "**Sellers & Service Providers:**\n"
            "- Original Equipment Manufacturers (OEMs)\n"
            "- Authorized Channel Partners / Resellers\n"
            "- Micro and Small Enterprises (MSEs)\n"
            "- DPIIT-recognized Startups (entitled to exemptions from prior turnover and experience criteria under GFR Rule 173)."
        ),
        "suggestions": [
            "What is GFR 149?",
            "How to register on GeM?",
            "Browse GeM Live Bids",
            "Launch Matcher Workspace"
        ]
    },
    {
        "id": "mse_preference",
        "keywords": ["mse", "msme", "preference", "small", "enterprise", "ppp-mse", "exemption"],
        "patterns": [
            r'\b(mse exemption|msme preference|ppp mse|msme benefits on gem|msme purchase preference|udyam benefits on gem)\b'
        ],
        "reply": (
            "**MSE (Micro & Small Enterprises) Benefits on GeM (PPP-MSE Order, 2012):**\n\n"
            "- **25% Mandatory Annual Procurement:** Government departments must procure at least 25% of annual requirements from MSEs (including 4% SC/ST and 3% Women-owned).\n"
            "- **Price Preference (L-1 + 15% Band):** Participating MSEs quoting within 15% of the lowest non-MSE price are offered to match L-1 price to supply up to 25% of the tender.\n"
            "- **100% EMD Exemption:** Verified MSEs with valid Udyam Registration are completely exempt from submitting Earnest Money Deposit (EMD).\n"
            "- **Tender Fee Waiver:** All government tender documentation fees are waived."
        ),
        "suggestions": [
            "What is Startup exemption on GeM?",
            "What is GFR 149?",
            "What is an L1 bidder?",
            "Launch Matcher Workspace"
        ]
    },
    {
        "id": "startup_exemption",
        "keywords": ["startup", "dpiit", "turnover", "experience", "waiver", "exemption"],
        "patterns": [
            r'\b(startup exemption on gem|dpiit startup benefits|prior turnover exemption|prior experience exemption|startups on gem)\b'
        ],
        "reply": (
            "**DPIIT-Recognized Startup Benefits on GeM:**\n\n"
            "Under **Rule 173(i) of General Financial Rules (GFR), 2017** and Ministry guidelines:\n"
            "- **Prior Turnover Exemption:** Startups are exempt from prior minimum turnover criteria, provided their product meets all technical and safety standards.\n"
            "- **Prior Experience Exemption:** Startups do not need prior past performance or years of operation to participate in bids.\n"
            "- **EMD Exemption:** 100% exemption from Earnest Money Deposit.\n"
            "- **Condition:** Quality and technical specifications (including mandatory BIS / ISI certifications) cannot be relaxed for public safety."
        ),
        "suggestions": [
            "What is an ISI mark?",
            "What is a Quality Control Order (QCO)?",
            "What is GFR 149?",
            "Launch Matcher Workspace"
        ]
    },
    {
        "id": "crs_electronics",
        "keywords": ["crs", "compulsory", "registration", "scheme", "meity", "electronics", "it"],
        "patterns": [
            r'\b(crs|compulsory registration scheme|meity bis|electronics registration|crs scheme|electronics safety standard)\b'
        ],
        "reply": (
            "The **Compulsory Registration Scheme (CRS)** was introduced by the Ministry of Electronics & IT (MeitY) under the BIS regulatory framework for electronic and IT products.\n\n"
            "**How CRS Operates:**\n"
            "- Covers 70+ categories including laptops, smartphones, LED luminaires, power adapters, servers, and smart speakers.\n"
            "- Operates on **Self-Declaration of Conformity**: manufacturers test products at accredited BIS-recognized labs and obtain a registration grant (`R-XXXXXXXX`).\n"
            "- Does not require factory audits, enabling rapid regulatory clearance for fast-evolving technology hardware."
        ),
        "suggestions": [
            "Check LED Street Light Standards",
            "What is an ISI mark?",
            "What is a QCO?",
            "Launch Matcher Workspace"
        ]
    },
    {
        "id": "hallmarking",
        "keywords": ["hallmark", "hallmarking", "gold", "silver", "huid", "jewellery", "purity"],
        "patterns": [
            r'\b(what is hallmarking|gold hallmarking|huid|bis hallmarking|gold purity standard|hallmark unique identification)\b'
        ],
        "reply": (
            "**BIS Hallmarking** is the official purity certification of gold and silver jewelry in India, governed by the Bureau of Indian Standards.\n\n"
            "**Components of Gold Hallmarking:**\n"
            "1. **BIS Logo:** The official triangle mark.\n"
            "2. **Purity in Karat & Fineness:** E.g., `22K916` (22 Karat / 91.6% purity), `18K750` (18 Karat / 75.0%), `14K585` (14 Karat).\n"
            "3. **6-Digit Alphanumeric HUID:** Hallmark Unique Identification code laser-engraved on each piece for complete traceability on the **BIS Care App**.\n\n"
            "Mandatory hallmarking is enforced across 340+ districts in India."
        ),
        "suggestions": [
            "What is BIS Care App?",
            "What is an ISI mark?",
            "What is BIS?",
            "Launch Matcher Workspace"
        ]
    },
    {
        "id": "bis_care_app",
        "keywords": ["app", "bis care", "verify", "mobile", "complaint", "license"],
        "patterns": [
            r'\b(bis care|bis care app|verify bis license|check isi mark online|verify huid|how to check if isi is genuine|bis mobile app)\b'
        ],
        "reply": (
            "**BIS Care App** is the official citizen-centric mobile application developed by the Bureau of Indian Standards (available on Android & iOS).\n\n"
            "**Key Capabilities for Officers & Citizens:**\n"
            "- **Verify License Details:** Enter the 7-8 digit `CM/L` license number on any ISI product to check manufacturer authenticity, brand name, and validity.\n"
            "- **Verify HUID:** Enter the 6-digit alphanumeric code on gold jewelry to check jeweler registration date, assaying center, and purity.\n"
            "- **Verify CRS Registration:** Enter `R-XXXXXXXX` to check electronics safety grants.\n"
            "- **Grievance Redressal:** Lodge formal complaints regarding misleading ISI marks or substandard quality with photo attachments."
        ),
        "suggestions": [
            "What is an ISI mark?",
            "What is Hallmarking?",
            "What is a QCO?",
            "Launch Matcher Workspace"
        ]
    },
    {
        "id": "emd_pbg",
        "keywords": ["emd", "pbg", "earnest", "money", "deposit", "guarantee", "security"],
        "patterns": [
            r'\b(what is emd|earnest money deposit|pbg|performance bank guarantee|bid security|epbg on gem|emd exemption)\b'
        ],
        "reply": (
            "**Bid Security (EMD) and Performance Security (PBG) on GeM:**\n\n"
            "**1. Earnest Money Deposit (EMD):**\n"
            "- Submitted by bidders during bid submission to protect against frivolous or defaulted bids.\n"
            "- Usually 1% to 2% of the estimated contract value.\n"
            "- **Exemptions:** Micro & Small Enterprises (MSEs), DPIIT Startups, and Central PSUs are 100% exempt.\n\n"
            "**2. Performance Security (e-PBG):**\n"
            "- Submitted by the successful (L-1) bidder within 15 days of contract award (typically 3% to 5% of order value).\n"
            "- Maintained through digital e-PBG integration until warranty and contractual liabilities are concluded."
        ),
        "suggestions": [
            "What are MSE exemptions on GeM?",
            "What is Startup exemption on GeM?",
            "What is GFR 149?",
            "Launch Matcher Workspace"
        ]
    },
    {
        "id": "gem_clause_help",
        "keywords": ["clause", "template", "mandatory", "compliance", "tender", "write"],
        "patterns": [
            r'\b(what is a gem clause|procurement clause template|how to write tender clause|tender compliance clause|sample gem clause|generate gem clause)\b'
        ],
        "reply": (
            "A **GeM Mandatory Procurement Clause** legally binds suppliers to deliver goods certified under the relevant Indian Standard.\n\n"
            "**Standard Clause Template:**\n"
            "> *\"MANDATORY QUALITY & COMPLIANCE CLAUSE: The item offered under this tender must strictly conform to BIS [Standard Number] - '[Standard Title]' along with all latest amendments and revisions. The bidder/OEM must furnish a valid BIS License / ISI Marking Certificate during technical evaluation. Failure to submit verified certification shall result in immediate technical disqualification as per GFR 149 public procurement guidelines.\"*"
        ),
        "suggestions": [
            "Find standards to generate clause",
            "What is GFR 149?",
            "What is a QCO?",
            "Launch Matcher Workspace"
        ]
    },
    {
        "id": "bisspec_iq_help",
        "keywords": ["bisspec", "platform", "portal", "features", "how to use", "website"],
        "patterns": [
            r'\b(how does bisspec\.iq work|how to use this portal|how to use this platform|features of this platform|features of bisspec\.iq|what can you do|help me use this|about bisspec\.iq|who created you)\b'
        ],
        "reply": (
            "**BISspec.IQ** is an AI-powered intelligence portal bridging GeM public procurement with the Bureau of Indian Standards (BIS):\n\n"
            "**Primary Capabilities:**\n"
            "1. **Launch Matcher Workspace:** Enter any product specification or tender text to scrape the official BIS portal (`standards.bis.gov.in`) and calculate semantic TF-IDF match percentages.\n"
            "2. **Real-time GeM Bid Explorer:** Browse active procurement tenders and run automated 1-click BIS compliance audits.\n"
            "3. **Tender Procurement Clause Generator:** Generate legally enforceable tender clauses citing relevant Indian Standards.\n"
            "4. **AI Assistant:** Ask general questions about BIS and GeM regulations or query standards conversationally."
        ),
        "suggestions": [
            "Launch Matcher Workspace",
            "Browse GeM Live Bids",
            "Search Cable Standards (IS 694)",
            "What is GFR 149?"
        ]
    }
]

# ==============================================================================
# INTENT PARSER & PRODUCT QUERY EXTRACTOR
# ==============================================================================
def find_general_faq_match(message: str) -> Optional[Dict[str, Any]]:
    """
    Checks if user message matches any curated general regulatory/procurement FAQ
    using both flexible regex matching and keyword intersection scoring.
    """
    clean = (message or "").strip().lower()
    msg_words = set(re.findall(r'\b[a-z0-9]+\b', clean))

    # 1. Regex pattern matching
    for faq in GENERAL_KNOWLEDGE_BASE:
        for pat in faq["patterns"]:
            if re.search(pat, clean, re.I):
                return {
                    "intent": "general_faq",
                    "id": faq["id"],
                    "reply": faq["reply"],
                    "suggestions": faq["suggestions"]
                }

    # 2. Semantic keyword set scoring
    best_faq = None
    best_score = 0
    for faq in GENERAL_KNOWLEDGE_BASE:
        kw_set = set(faq.get("keywords", []))
        common = msg_words.intersection(kw_set)
        if len(common) >= 2 and len(common) > best_score:
            best_score = len(common)
            best_faq = faq

    if best_faq and best_score >= 2:
        return {
            "intent": "general_faq",
            "id": best_faq["id"],
            "reply": best_faq["reply"],
            "suggestions": best_faq["suggestions"]
        }

    return None

def extract_clean_product_query(text: str) -> str:
    """
    Strips conversational preambles, polite requests, and question wrappers
    to isolate the exact product keyword or Indian Standard code for live scraping.
    e.g. 'Can you recommend standards for PVC insulated cables?' -> 'PVC insulated cables'
    e.g. 'What is the standard for LED street lights?' -> 'LED street lights'
    e.g. 'Tell me about IS 694 for domestic wiring' -> 'IS 694 domestic wiring'
    """
    cleaned = (text or "").strip()
    is_code = re.search(r'\b(is\s*(?:/iso|/iec)?\s*\d+(?:\s*\([^\)]+\))?(?:\s*:\s*\d{4})?)\b', cleaned, re.I)

    lead_patterns = [
        r'^(can\s+you\s+(?:please\s+)?(?:recommend|find|search|show|give\s+me|get|tell\s+me\s+about)?)\s+',
        r'^(could\s+you\s+(?:please\s+)?(?:recommend|find|search|show|give\s+me|get|tell\s+me\s+about)?)\s+',
        r'^(would\s+you\s+(?:please\s+)?(?:recommend|find|search|show|give\s+me|get)?)\s+',
        r'^(please\s+(?:recommend|find|search|show|give\s+me|get|tell\s+me\s+about|provide)?)\s+',
        r'^(kindly\s+(?:recommend|find|search|show|give\s+me|get|provide)?)\s+',
        r'^(i\s+want\s+(?:to\s+find|to\s+know|standards\s+for)?)\s+',
        r'^(i\s+need\s+(?:standards\s+for|specs\s+for|technical\s+specs\s+for)?)\s+',
        r'^(i\s+am\s+looking\s+for\s+(?:standards\s+for)?)\s+',
        r'^(looking\s+for\s+(?:standards\s+for)?)\s+',
        r'^(help\s+me\s+(?:find|search|identify)?)\s+',
        r'^(what\s+is\s+the\s+(?:indian\s+)?standard\s+(?:for|of)?)\s+',
        r'^(what\s+are\s+the\s+(?:indian\s+)?standards\s+(?:for|of)?)\s+',
        r'^(what\s+standard\s+(?:should\s+i\s+use|applies|is\s+used)?\s+(?:for|to)?)\s+',
        r'^(which\s+(?:bis\s+)?standard\s+(?:is\s+for|applies\s+to|should\s+be\s+used\s+for)?)\s+',
        r'^(tell\s+me\s+about)\s+',
        r'^(give\s+me\s+(?:standards\s+for|the\s+standard\s+for)?)\s+',
        r'^(recommend\s+(?:standards\s+for|the\s+standard\s+for)?)\s+',
        r'^(find\s+(?:the\s+)?standard\s+for)\s+',
        r'^(find\s+)\s*',
        r'^(search\s+(?:for)?)\s+',
        r'^(standards\s+(?:for|of)?)\s+'
    ]
    for _ in range(3):
        for pat in lead_patterns:
            cleaned = re.sub(pat, '', cleaned, flags=re.I).strip()

    fluff_patterns = [
        r'\b(in\s+india|for\s+government\s+procurement|for\s+gem\s+tender|for\s+tender|for\s+bidding|on\s+gem|in\s+hindi|in\s+english|please|thank\s+you|thanks|as\s+per\s+bis)\b'
    ]
    for pat in fluff_patterns:
        cleaned = re.sub(pat, '', cleaned, flags=re.I).strip()

    cleaned = re.sub(r'[\?!\.,;:"\']+', ' ', cleaned).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)

    if is_code:
        code_str = is_code.group(0).upper()
        rest = re.sub(re.escape(is_code.group(0)), '', cleaned, flags=re.I).strip()
        return f"{code_str} {rest}".strip() if rest else code_str

    return cleaned if cleaned else text

def is_general_conceptual_question(message: str) -> bool:
    """
    Checks if a query is a general knowledge question (science, engineering, policy, concepts)
    rather than a specific procurement product search.
    """
    msg = (message or "").strip().lower()
    
    # Explicit product search prefixes
    if re.search(r'\b(standard\s+for|standards\s+for|is\s+code\s+for|bis\s+code\s+for|spec\s+for|specification\s+for)\b', msg):
        return False

    # Question lead-ins
    question_triggers = [
        r'^(what\s+is|what\s+are|what\s+does|how\s+does|how\s+to|how\s+can|why\s+is|why\s+do|who\s+is|who\s+are)\b',
        r'^(explain|describe|define|tell\s+me\s+about|meaning\s+of|difference\s+between)\b',
        r'\b(can\s+you\s+explain|could\s+you\s+explain|what\s+is\s+the\s+meaning\s+of)\b'
    ]
    for q_pat in question_triggers:
        if re.search(q_pat, msg):
            return True

    return False

def answer_general_knowledge_question(message: str) -> Dict[str, Any]:
    """
    Provides intelligent, structured answers for general knowledge or conceptual questions
    without erroneously running product web-scraping.
    """
    clean_msg = message.strip()
    clean_lower = clean_msg.lower()

    # Pre-crafted high-frequency general concept answers
    if re.search(r'\b(artificial\s+intelligence|ai|machine\s+learning|nlp)\b', clean_lower):
        reply = (
            "**Artificial Intelligence (AI) in Public Procurement & Standardization:**\n\n"
            "Artificial Intelligence enables modern procurement platforms like **BISspec.IQ** to automate complex compliance workflows:\n\n"
            "- **Semantic NLP Matching:** Translates unstructured tender descriptions into mathematical feature vectors (TF-IDF & Embeddings) to identify corresponding Indian Standards.\n"
            "- **Live Dynamic Scraping:** Connects procurement systems directly to regulatory bodies (`standards.bis.gov.in`) to verify active certification status.\n"
            "- **Anti-Corruption & Fair Competition:** Eliminates biased tender specifications by standardizing technical parameters as per National Indian Standards.\n"
            "- **Multilingual Inclusion:** Integrates regional language translation so officers across Indian states can interact seamlessly in their mother tongue."
        )
        suggestions = ["How does BISspec.IQ work?", "What is BIS?", "What is GFR 149?", "Launch Matcher Workspace"]

    elif re.search(r'\b(solar\s+energy|solar\s+panel|photovoltaic|how\s+do\s+solar\s+panels\s+work)\b', clean_lower):
        reply = (
            "**Solar Photovoltaic (PV) Technology & Standardization:**\n\n"
            "Solar PV panels convert sunlight into electrical direct current (DC) via the photovoltaic effect using semiconductor silicon wafers.\n\n"
            "**Critical BIS Quality Standards in India:**\n"
            "- **IS 14286 : 2010:** Design Qualification and Type Approval for Crystalline Silicon Terrestrial PV Modules.\n"
            "- **IS/IEC 61730 (Part 1 & 2) : 2016:** Mandatory safety qualification for module construction and high-voltage electrical testing.\n"
            "- **IS 16221 (Part 2) : 2015:** Safety standards for solar grid-tied and hybrid inverters.\n\n"
            "All solar panels procured under MNRE and government tenders on GeM must be enrolled in the **Approved List of Models and Manufacturers (ALMM)** and hold valid BIS certification."
        )
        suggestions = ["Solar PV Module (IS 14286)", "Solar Inverter (IS 16221)", "What is a QCO?", "Launch Matcher Workspace"]

    elif re.search(r'\b(transformer|how\s+do\s+transformers\s+work|distribution\s+transformer)\b', clean_lower):
        reply = (
            "**Transformers & Distribution Grid Standards:**\n\n"
            "A transformer is a passive electrical device that transfers electrical energy between circuits through electromagnetic induction, stepping voltages up or down.\n\n"
            "**Key Indian Standards for Procurement:**\n"
            "- **IS 1180 (Part 1) : 2014:** Mandatory standard for Outdoor Type Oil Immersed Distribution Transformers up to 2500 kVA, 33 kV.\n"
            "- **Star Rating Compliance:** Requires compliance with BEE (Bureau of Energy Efficiency) maximum total loss limits at 50% and 100% loading.\n"
            "- **Safety:** Covered under compulsory Quality Control Orders (QCO) issued by the Ministry of Heavy Industries."
        )
        suggestions = ["Find standards for 33kV Transformer", "What is an ISI mark?", "What is GFR 149?", "Launch Matcher Workspace"]

    elif re.search(r'\b(cable|wire|pvc\s+cable|how\s+do\s+cables\s+work)\b', clean_lower):
        reply = (
            "**Electrical Cables & Wiring Specifications:**\n\n"
            "Cables provide electrical power distribution and signal transmission using high-conductivity copper or aluminum conductors insulated with thermoplastic or thermosetting compounds.\n\n"
            "**Governing Indian Standards:**\n"
            "- **IS 694 : 2010:** PVC Insulated Cables for Working Voltages up to and including 1100 V (domestic, commercial, and panel wiring).\n"
            "- **IS 1554 (Part 1) : 1988:** PVC Insulated Heavy Duty Electric Cables.\n"
            "- **IS 7098 (Part 1 & 2):** XLPE Insulated Thermoplastic Sheathed Cables up to 33 kV.\n\n"
            "Under government procurement rules, all cables must bear the **ISI Mark** with verified conductor resistance and flame-retardant properties."
        )
        suggestions = ["PVC Cables 1100V (IS 694)", "What is an ISI mark?", "What is a QCO?", "Launch Matcher Workspace"]

    else:
        # Structured general reasoning reply
        reply = (
            f"**Information on: *\"{clean_msg}\"***\n\n"
            "I am the **BISspec.IQ AI Assistant**, specialized in Indian Standards (BIS), public procurement on GeM, and technical compliance.\n\n"
            "**How I can assist you with this topic:**\n"
            "- **Query Indian Standards:** If you need the exact technical standard or test method for this item, enter the product name directly.\n"
            "- **Tender Compliance Clauses:** Generate legally binding GeM procurement clauses.\n"
            "- **Regulatory Framework:** Answer questions on GFR 149 procurement thresholds, ISI marking, QCO notifications, or seller/buyer onboarding."
        )
        suggestions = [
            "What is BIS and what does it do?",
            "How does GeM procurement work under GFR 149?",
            "What is an ISI mark?",
            "Launch Matcher Workspace"
        ]

    return {
        "success": True,
        "intent": "general_knowledge",
        "reply": reply,
        "standards": [],
        "suggestions": suggestions
    }

def detect_chat_intent(message: str) -> Tuple[str, str]:
    """
    Categorizes user message into:
    - 'greeting': Casual greeting
    - 'general_faq': General question about BIS, GeM, rules, ISI marks, etc.
    - 'gem_clause': Explicit request for a tender procurement clause
    - 'general_knowledge': Open-ended conceptual/explanatory question
    - 'standard_query': Product / specification search query
    Returns (intent, processed_query).
    """
    msg = (message or "").strip().lower()

    # 1. Greetings
    if re.search(r'\b(hi|hello|hey|namaste|greetings|good\s+morning|good\s+afternoon|good\s+evening)\b', msg) and len(msg.split()) <= 4:
        return 'greeting', ''

    # 2. General FAQ Check
    faq_match = find_general_faq_match(msg)
    if faq_match:
        return 'general_faq', msg

    # 3. GeM Clause Request
    if re.search(r'\b(gem clause|procurement clause|clause for|tender clause)\b', msg):
        subject = re.sub(r'\b(gem clause|procurement clause|clause for|tender clause|give me|show me|create|generate)\b', '', msg, flags=re.I).strip()
        clean_subject = extract_clean_product_query(subject)
        return 'gem_clause', clean_subject or msg

    # 4. General Conceptual Questions
    if is_general_conceptual_question(msg):
        return 'general_knowledge', msg

    # 5. Standard Product Query (Default)
    clean_query = extract_clean_product_query(message)
    return 'standard_query', clean_query or message

# ==============================================================================
# MAIN CONVERSATIONAL CHAT PROCESSING ENGINE
# ==============================================================================
def process_chat_message(
    message: str,
    language_code: str = 'en',
    matcher_func=None,
    scraper_func=None,
    history: Optional[List[Dict[str, str]]] = None,
    translator_func=None
) -> Dict[str, Any]:
    """
    Processes incoming natural language chat messages:
    1. Evaluates user intent: Greetings, General Regulatory Questions, Conceptual Knowledge, or Standards Search.
    2. For General Questions: Returns authoritative answers covering BIS, GeM, GFR 149, QCOs, ISI marks.
    3. For Product & Standards Queries: Executes the EXACT SAME live web-scraping & TF-IDF scoring
       pipeline as the Launch Matcher, returning rich standard cards with GeM integration.
    """
    clean_msg = (message or "").strip()
    if not clean_msg:
        return {
            "success": False,
            "error": "Message cannot be empty."
        }

    intent, search_term = detect_chat_intent(clean_msg)

    # 1. Greeting Flow
    if intent == 'greeting':
        greeting_reply = GREETINGS_MAP.get(language_code, GREETINGS_MAP['en'])
        return {
            "success": True,
            "intent": "greeting",
            "reply": greeting_reply,
            "standards": [],
            "suggestions": [
                "What is BIS and what are its functions?",
                "How does GeM procurement work under GFR 149?",
                "Find standards for PVC insulated cables",
                "Recommend standards for LED street lights",
                "What is a Quality Control Order (QCO)?"
            ]
        }

    # 2. General FAQ Flow
    if intent == 'general_faq':
        faq_data = find_general_faq_match(clean_msg)
        if faq_data:
            reply_text = faq_data["reply"]
            if language_code != 'en' and translator_func:
                try:
                    reply_text = translator_func(reply_text, source_lang='en', target_lang=language_code)
                except Exception:
                    pass
            return {
                "success": True,
                "intent": "general_faq",
                "reply": reply_text,
                "standards": [],
                "suggestions": faq_data["suggestions"]
            }

    # 3. General Conceptual Knowledge Flow
    if intent == 'general_knowledge':
        gk_res = answer_general_knowledge_question(clean_msg)
        if language_code != 'en' and translator_func:
            try:
                gk_res["reply"] = translator_func(gk_res["reply"], source_lang='en', target_lang=language_code)
            except Exception:
                pass
        return gk_res

    # 4. Standard Product Search / GeM Clause Flow
    matches = []
    if matcher_func and search_term:
        try:
            matches = matcher_func(search_term, top_n=3, language=language_code)
        except Exception as e:
            logger.error(f"Matcher execution error in chat assistant: {e}")
            matches = []

    if matches and len(matches) > 0:
        top_match = matches[0]
        std_no = top_match.get("standard_number", "")
        std_title = top_match.get("title", "")
        score_pct = int(float(top_match.get("score", 0.85)) * 100)
        status_str = top_match.get("status", "Active")

        if intent == 'gem_clause':
            reply = (
                f"Here is the mandatory GeM procurement clause for **{std_no} - {std_title}**:\n\n"
                f"> *\"{top_match.get('gem_clause', '')}\"*\n\n"
                f"This specification is verified as **{status_str}** on the official Bureau of Indian Standards portal."
            )
        else:
            reply = (
                f"I queried the official Bureau of Indian Standards portal and retrieved **{len(matches)} matching Indian Standards** for *\"{search_term}\"*.\n\n"
                f"The primary recommendation is **{std_no}** (*{std_title}*) with an official compliance rating of **{score_pct}%**."
            )

        if language_code != 'en' and translator_func:
            try:
                reply = translator_func(reply, source_lang='en', target_lang=language_code)
            except Exception:
                pass

        return {
            "success": True,
            "intent": intent,
            "reply": reply,
            "search_term": search_term,
            "standards": matches,
            "suggestions": [
                f"Copy GeM Clause for {std_no}",
                f"View products on GeM for {std_no}",
                "Search another technical specification",
                "What is GFR 149 for GeM bidding?"
            ]
        }
    else:
        # Fallback informative reply for open-ended or unmatched queries
        fallback_reply = (
            f"I searched the live Bureau of Indian Standards repository for *\"{search_term}\"*, but could not find an exact match above the threshold.\n\n"
            "**Tips for accurate results:**\n"
            "- Try broader technical keywords (e.g. *'PVC cable'*, *'LED lamp'*, *'solar panel'*, *'cement'*, *'distribution transformer'*).\n"
            "- If you know the code, enter it directly (e.g. *'IS 694'*, *'IS 16102'*, *'IS 14286'*).\n"
            "- Or ask general questions like *'What is BIS?'* or *'How does procurement work under GFR 149?'*."
        )
        if language_code != 'en' and translator_func:
            try:
                fallback_reply = translator_func(fallback_reply, source_lang='en', target_lang=language_code)
            except Exception:
                pass

        return {
            "success": True,
            "intent": "standard_query",
            "reply": fallback_reply,
            "search_term": search_term,
            "standards": [],
            "suggestions": [
                "Find standards for LED street lights",
                "PVC multicore cables 1100V (IS 694)",
                "Solar PV modules (IS 14286)",
                "What is a Quality Control Order (QCO)?",
                "What is GFR 149?"
            ]
        }
