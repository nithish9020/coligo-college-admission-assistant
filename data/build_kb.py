"""Build the SKCET / TNEA knowledge-base PDF for RAG ingestion.

Cutoff figures are transcribed from the official SKCET cut-off PDFs:
  https://skcet.ac.in/wp-content/uploads/2026/01/Cut-off-marks-2024-2025.pdf
  https://skcet.ac.in/wp-content/uploads/2026/01/Cut-off-marks-2023-2024.pdf
Blank cells in the source tables mean no admission was recorded for that
community that year; they are rendered as "not available" rather than guessed.
"""

import textwrap

COMMUNITIES = ["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"]

BRANCH_NAMES = {
    "ECE": "Electronics and Communication Engineering (ECE)",
    "CSE": "Computer Science and Engineering (CSE)",
    "MECH": "Mechanical Engineering (MECH)",
    "EEE": "Electrical and Electronics Engineering (EEE)",
    "CIVIL": "Civil Engineering (CIVIL)",
    "IT": "Information Technology (IT)",
    "MCT": "Mechatronics Engineering (MCT)",
    "CSBS": "Computer Science and Business Systems (CSBS), powered by TCS",
    "AI&DS": "Artificial Intelligence and Data Science (AI&DS)",
    "M.TECH": "M.Tech Integrated Computer Science and Engineering (5-year), powered by Virtusa",
    "CSD": "M.Tech Data Science / Computer Science and Design (CSD)",
    "CYBER": "Computer Science and Engineering - Cyber Security (CYBER)",
}

# marks: 14 slots = OC-H, OC-L, BC-H, BC-L, BCM-H, BCM-L, MBC-H, MBC-L,
#                   SC-H, SC-L, SCA-H, SCA-L, ST-H, ST-L   (None = blank cell)
CUTOFFS = {
    "2024-2025": {
        "ECE": {
            "marks": [196, 190, 190, 188.5, 189, 186.5, 190, 186, 180, 162.5, 165.5, 149, 149, None],
            "ranks": [1911, 8227, 8253, 10529, 9702, 13584, 8285, 14403, 24231, 59309, 52627, 88145, 88304, None],
        },
        "CSE": {
            "marks": [197, 192, 192, 190, 191.5, 187, 191.5, 188, 187.5, 169.5, 176, 157, 160.5, None],
            "ranks": [1300, 5640, 5648, 7919, 6249, 12491, 5993, 10958, 11746, 44648, 31464, 70397, 63345, None],
        },
        "MECH": {
            "marks": [183, 177, 176.5, 172.5, 176.5, 169, 176.5, 165.5, 154, 133.5, 149, 110, 136, None],
            "ranks": [18847, 30054, 30698, 38074, 30878, 45238, 30463, 52428, 76945, 122989, 88584, 170672, 117315, None],
        },
        "EEE": {
            "marks": [190.5, 187, 187, 184.5, 187, 184, 185.5, 181, 165, 146.5, 145.5, 117, None, None],
            "ranks": [7374, 12980, 13048, 16763, 13128, 17274, 14934, 23044, 53634, 94065, 96405, 157674, None, None],
        },
        "CIVIL": {
            "marks": [177.5, 172, 172, 168.5, 171.5, 154.5, 171, 164.5, 155, 139, 105.5, None, None, None],
            "ranks": [29149, 39053, 39407, 46122, 40238, 76539, 40964, 54654, 74818, 110470, 177703, None, None, None],
        },
        "IT": {
            "marks": [194, 189.5, 189.5, 188, 189.5, 185.5, 189, 186, 178, 160.5, 159.5, 151, 157, 149.5],
            "ranks": [3711, 8873, 8889, 11117, 9401, 15203, 9547, 14440, 28068, 63186, 65170, 84508, 71017, 87264],
        },
        "MCT": {
            "marks": [186, 177.5, 177.5, 174, 177.5, 171.5, 175, 166.5, 176.5, 135.5, 134.5, 117, 119, None],
            "ranks": [13999, 28717, 28899, 35167, 29053, 40891, 33343, 50940, 30904, 118032, 120560, 157908, 153788, None],
        },
        "CSBS": {
            "marks": [191, 187.5, 187.5, 186, None, None, 187, 183.5, 167.83, 156.5, 144.13, None, None, None],
            "ranks": [7226, 11980, 12168, 14119, None, None, 12754, 18310, 48083, 71821, 99062, None, None, None],
        },
        "AI&DS": {
            "marks": [195, 190, 190, 188.5, 188, 185.5, 190, 187, 180, 167.5, 170.5, 166, 149.5, 144],
            "ranks": [2842, 7942, 7955, 10558, 11262, 15445, 8100, 12897, 24307, 48720, 42697, 51221, 87677, 99433],
        },
        "M.TECH": {
            "marks": [190.5, 185.5, 185, 182.5, 181, None, 184.5, 179, 168.5, 151.5, 130.5, None, 114, None],
            "ranks": [7263, 14887, 15755, 19785, 22236, None, 16635, 26346, 46441, 82327, 129261, None, 163601, None],
        },
        "CSD": {
            "marks": [189, 186, 185.5, 185, 185, None, 185.5, 183, 166, 152.5, 159.5, None, None, None],
            "ranks": [9579, 14391, 14778, 15835, 15723, None, 15350, 19410, 51297, 80826, 64916, None, None, None],
        },
        "CYBER": {
            "marks": [193, 188.5, 188, 187.5, 187.5, 184.5, 188.5, 184.5, 170, 160, 166, None, 137.5, None],
            "ranks": [4513, 10392, 11006, 12144, 11910, 16616, 10853, 16368, 43911, 64488, 51746, None, 113712, None],
        },
    },
    "2023-2024": {
        "ECE": {
            "marks": [193, 189.5, 189.5, 186.5, 187.5, 183.5, 188.37, 182.5, 177, 153, 159, 135, 117, None],
            "ranks": [3982, 8067, 8159, 11220, 10035, 14464, 9222, 15612, 22969, 63811, 51890, 102899, 141132, None],
        },
        "CSE": {
            "marks": [196.5, 192.5, 192.5, 190, 192, 188.5, 192, 187, 180.5, 157, 165, 153, 151, 136],
            "ranks": [1917, 4705, 4762, 7448, 4907, 8757, 4871, 10521, 17831, 55661, 41098, 63909, 68498, 100857],
        },
        "MECH": {
            "marks": [189, 169, 169, 164, 167, 161, 169, 155, 151, 129, 145, 128, 138, None],
            "ranks": [8609, 33989, 34097, 43711, 38378, 48965, 34790, 60069, 68453, 115716, 79975, 118097, 95580, None],
        },
        "EEE": {
            "marks": [190, 184, 184.5, 180.5, 182, 179, 184, 173, 163, 136, 148, 131, None, None],
            "ranks": [7692, 13399, 13408, 17849, 16043, 19966, 13763, 28083, 44268, 100120, 75127, 110932, None, None],
        },
        "CIVIL": {
            "marks": [174, 162, 162, 153, 159, None, 163, 146, 144, 130, 126, None, 143, None],
            "ranks": [26848, 44022, 46216, 63118, 51204, None, 44318, 78485, 81924, 114967, 122012, None, 84573, None],
        },
        "IT": {
            "marks": [193, 189, 189, 187, 187.6, 182, 188.5, 184.2, 170, 145, 150, 134, 141, None],
            "ranks": [4255, 8563, 8688, 10459, 9754, 15944, 9024, 13563, 32932, 80749, 70364, 105890, 89041, None],
        },
        "MCT": {
            "marks": [185.5, 172, 172, 167, 165, 161, 171, 159, 150, 122, 123, 115, None, None],
            "ranks": [12406, 29675, 29856, 38148, 41793, 48043, 31769, 57763, 69153, 132384, 130044, 145655, None, None],
        },
        "CSBS": {
            "marks": [190.5, 187, 187, 185.5, 187, 183.5, 187, 182.5, 163, 143, 128, 125, None, None],
            "ranks": [6848, 10309, 10470, 11890, 10355, 14627, 10584, 15706, 44689, 85369, 119617, 124145, None, None],
        },
        "AI&DS": {
            "marks": [196.5, 191, 191, 188, 189.5, 188, 189.5, 186, 182.5, 162, 169, 144, 132, None],
            "ranks": [1706, 5893, 5922, 9270, 8003, 9546, 7938, 11762, 15647, 45936, 34163, 83625, 108557, None],
        },
        "M.TECH": {
            "marks": [190.5, 184.5, 184.5, 181.5, None, None, 184, 176, 160, 150, 136, None, None, None],
            "ranks": [6772, 13187, 13222, 16850, None, None, 13905, 23841, 49739, 70398, 99582, None, None, None],
        },
        "CSD": {
            "marks": [188.5, 185.5, 185.5, 183.5, 182, 181.5, 184, 180, 153, 141, 132, None, None, None],
            "ranks": [8858, 12011, 12045, 14423, 16066, 16863, 13710, 18214, 63281, 89880, 110336, None, None, None],
        },
        "CYBER": {
            "marks": [196, 187.5, 187, 186, 185.75, 183.5, 186.5, 181.5, 162, 147, 138, None, 121, None],
            "ranks": [2229, 10078, 10291, 11558, 11881, 14291, 11095, 16668, 46744, 76829, 96397, None, 133311, None],
        },
    },
}


def fmt(v):
    if v is None:
        return None
    return str(int(v)) if float(v) == int(v) else str(v)


def branch_paragraphs(year, code, data):
    """One self-contained paragraph per branch+year, so each RAG chunk that
    lands on it carries the branch name, year and college name."""
    name = BRANCH_NAMES[code]
    marks, ranks = data["marks"], data["ranks"]
    parts = []
    for i, comm in enumerate(COMMUNITIES):
        hm, lm = fmt(marks[2 * i]), fmt(marks[2 * i + 1])
        hr, lr = fmt(ranks[2 * i]), fmt(ranks[2 * i + 1])
        if hm is None and lm is None:
            parts.append(f"{comm}: no admission recorded for this community.")
        elif lm is None:
            parts.append(
                f"{comm}: highest cutoff mark {hm} (rank {hr}); lowest not available."
            )
        else:
            parts.append(
                f"{comm}: highest cutoff mark {hm} (rank {hr}), "
                f"lowest cutoff mark {lm} (rank {lr})."
            )
    body = " ".join(parts)
    return (
        f"SKCET {name} TNEA cutoff marks for the year {year}. "
        f"At Sri Krishna College of Engineering and Technology (SKCET), Coimbatore, "
        f"the {name} branch recorded these TNEA {year} cutoff marks out of 200 and "
        f"the corresponding TNEA general ranks, by community. {body} "
        f"The lowest cutoff mark is the closing cutoff, i.e. the minimum mark at which "
        f"a candidate of that community was admitted to {name} at SKCET in {year}."
    )


def build_content():
    S = []

    S.append(("TITLE", "SKCET Coimbatore - TNEA Admissions Knowledge Base"))
    S.append(
        (
            "P",
            "This document is the knowledge base for the Coligo admission assistant. "
            "It covers Sri Krishna College of Engineering and Technology (SKCET), "
            "Kuniamuthur, Coimbatore, Tamil Nadu 641008, and the Tamil Nadu "
            "Engineering Admissions (TNEA) counselling process. Sources: "
            "skcet.ac.in academics, admission procedure and cut-off marks pages.",
        )
    )

    S.append(("H", "About TNEA counselling"))
    S.append(
        (
            "P",
            "TNEA stands for Tamil Nadu Engineering Admissions. It is the single-window "
            "counselling process run by the Directorate of Technical Education (DoTE), "
            "Government of Tamil Nadu, through tneaonline.org, for admission to B.E. and "
            "B.Tech degree programmes in government, government-aided and self-financing "
            "engineering colleges across Tamil Nadu. TNEA is entirely online and consists "
            "of registration, fee payment, certificate verification, random number "
            "allotment, rank list publication, choice filling, seat allotment, and "
            "confirmation of the allotted seat.",
        )
    )
    S.append(
        (
            "P",
            "TNEA does not use a separate entrance examination. Admission is based purely "
            "on Class 12 (HSC) marks in Physics, Chemistry and Mathematics. The TNEA "
            "cutoff is calculated out of 200 using the formula: Mathematics marks divided "
            "by 2, plus Physics marks divided by 4, plus Chemistry marks divided by 4. "
            "Mathematics therefore contributes a maximum of 100 marks, Physics a maximum "
            "of 50 marks, and Chemistry a maximum of 50 marks, giving a maximum cutoff of "
            "200. For example, a candidate scoring Mathematics 100, Physics 90 and "
            "Chemistry 80 has a TNEA cutoff of 100/2 + 90/4 + 80/4 = 50 + 22.5 + 20 = 92.5.",
        )
    )
    S.append(
        (
            "P",
            "Candidates are ranked by this cutoff mark. When two or more candidates have "
            "the same cutoff mark, ties are broken in order using: marks in Mathematics, "
            "then marks in Physics, then marks in the optional subject, then the older "
            "candidate by date of birth, and finally the randomly allotted number. Every "
            "registered candidate is assigned a 10-digit random number specifically for "
            "this tie-breaking purpose.",
        )
    )
    S.append(
        (
            "P",
            "TNEA reservation follows Tamil Nadu communal reservation categories: OC "
            "(Open Competition), BC (Backward Class), BCM (Backward Class Muslim), MBC "
            "(Most Backward Class and Denotified Communities), SC (Scheduled Caste), SCA "
            "(Scheduled Caste Arunthathiyar), and ST (Scheduled Tribe). A separate 7.5 "
            "percent horizontal reservation applies to eligible government school "
            "students, for whom counselling is conducted ahead of general counselling. "
            "Cutoff marks and closing ranks differ for each community, which is why the "
            "SKCET cutoff tables in this document are broken down by community.",
        )
    )
    S.append(
        (
            "P",
            "A TNEA cutoff rank for a branch in a college means the maximum (numerically "
            "highest) rank that was allotted a seat in that branch, in that college, for "
            "that community. A student whose rank is numerically lower (better) than the "
            "previous year's closing rank has a reasonable chance in that branch, though "
            "cutoffs shift each year with the number of applicants, seat availability and "
            "overall performance trends.",
        )
    )

    S.append(("H", "SKCET admission procedure"))
    S.append(
        (
            "P",
            "Admission to B.E. and B.Tech programmes at SKCET under the government quota "
            "is through TNEA counselling. The steps are: (1) Registration on the TNEA "
            "portal with name, father's name, mobile number and email address - all "
            "further communication about TNEA counselling uses the mobile number and "
            "email given at registration. (2) Payment of the application fee, which is "
            "Rs. 500 for General and OBC candidates and Rs. 250 for SC and ST applicants. "
            "(3) Entry of personal details including nativity, nationality, community "
            "category and qualifying examination marks. (4) Verification and submission "
            "of the completed form - candidates must check all details carefully because "
            "no corrections are allowed at later stages. (5) Allotment of a 10-digit "
            "random number used to resolve ties in the merit list.",
        )
    )
    S.append(
        (
            "P",
            "During SKCET and TNEA counselling, candidates pay an initial fee of Rs. 5,000 "
            "towards college admission, reduced to Rs. 1,000 for SC and ST candidates, and "
            "then rank their college and branch preferences in order of choice.",
        )
    )
    S.append(
        (
            "P",
            "Documents required in original for certificate verification at SKCET and TNEA "
            "counselling: High school and higher secondary (Class 10 and Class 12) mark "
            "sheets, Transfer Certificate, Nativity Certificate where applicable, Community "
            "or category certificate, and a photo identity proof such as Aadhaar card, "
            "election voter ID or driving licence.",
        )
    )
    S.append(
        (
            "P",
            "SKCET contact details for admission enquiries: Sri Krishna College of "
            "Engineering and Technology, Kuniamuthur, Coimbatore, Tamil Nadu 641008. "
            "Phone 0422-267 8001 and 0422-267 8012. Email principal@skcet.ac.in. "
            "Website skcet.ac.in.",
        )
    )

    S.append(("H", "Programmes offered at SKCET"))
    S.append(
        (
            "P",
            "SKCET undergraduate B.E. programmes: Civil Engineering; Computer Science and "
            "Engineering; Computer Science and Engineering (Artificial Intelligence and "
            "Machine Learning); Computer Science and Engineering (Cyber Security); "
            "Electrical and Electronics Engineering; Electronics and Communication "
            "Engineering; Mechanical Engineering; Mechatronics Engineering.",
        )
    )
    S.append(
        (
            "P",
            "SKCET undergraduate B.Tech programmes: Artificial Intelligence and Data "
            "Science; Computer Science and Business Systems (powered by TCS); Information "
            "Technology. SKCET also offers a 5-year M.Tech Integrated programme in "
            "Computer Science and Engineering, powered by Virtusa.",
        )
    )
    S.append(
        (
            "P",
            "SKCET postgraduate programmes: M.E. Computer Science and Engineering; M.E. "
            "Structural Engineering; M.Tech Data Science; Master of Business Administration "
            "(MBA). Admission to M.E. and M.Tech programmes is through TANCA counselling "
            "based on GATE or TANCET scores, and MBA admission is through TANCET, not TNEA.",
        )
    )
    S.append(
        (
            "P",
            "SKCET doctoral (Ph.D.) programmes are offered in Civil Engineering, Computer "
            "Science and Engineering, Electrical and Electronics Engineering, Electronics "
            "and Communication Engineering, Mechanical Engineering, Mechatronics "
            "Engineering, Information Technology, and Physics. The institution holds NAAC "
            "and NBA accreditation and features in NIRF rankings.",
        )
    )

    for year in ["2024-2025", "2023-2024"]:
        S.append(("H", f"SKCET TNEA cutoff marks {year}"))
        S.append(
            (
                "P",
                f"The following are the official SKCET B.E. and B.Tech admission cutoff "
                f"marks for the year {year}, by branch and by community. Cutoff marks are "
                f"out of 200. Ranks are TNEA general ranks. Where a community shows no "
                f"value, no admission was recorded in that category for that branch.",
            )
        )
        for code, data in CUTOFFS[year].items():
            S.append(("P", branch_paragraphs(year, code, data)))

    S.append(("H", "Quick reference: OC closing cutoffs by branch"))
    for year in ["2024-2025", "2023-2024"]:
        bits = []
        for code, data in CUTOFFS[year].items():
            lm = fmt(data["marks"][1])
            lr = fmt(data["ranks"][1])
            if lm:
                bits.append(f"{code} {lm} (rank {lr})")
        S.append(
            (
                "P",
                f"SKCET OC community closing (lowest) cutoff marks for {year}: "
                + "; ".join(bits)
                + ".",
            )
        )
    return S


# ---------------------------------------------------------------- PDF writer
def esc(s):
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def build_pdf(path, sections):
    PW, PH = 612, 792
    ML, MT, MB = 56, 750, 56
    pages, cur, y = [], [], MT

    def newpage():
        nonlocal cur, y
        if cur:
            pages.append(cur)
        cur, y = [], MT

    for kind, text in sections:
        if kind == "TITLE":
            font, size, lead, wrap, gap = "F2", 15, 20, 62, 14
        elif kind == "H":
            font, size, lead, wrap, gap = "F2", 12, 16, 78, 10
        else:
            font, size, lead, wrap, gap = "F1", 10, 13.5, 95, 8

        lines = []
        for para in text.split("\n"):
            lines.extend(textwrap.wrap(para, wrap) or [""])

        if y - (len(lines) * lead) < MB and len(lines) * lead < (MT - MB):
            newpage()

        for ln in lines:
            if y < MB:
                newpage()
            cur.append((font, size, ML, y, ln))
            y -= lead
        y -= gap
    newpage()

    objs, contents = [], []
    for pg in pages:
        s = []
        for font, size, x, yy, ln in pg:
            s.append(f"BT /{font} {size} Tf {x} {yy:.1f} Td ({esc(ln)}) Tj ET")
        contents.append("\n".join(s).encode())

    n_pages = len(pages)
    font_ids = (3 + n_pages * 1, 4 + n_pages * 1)
    kids = " ".join(f"{3 + i} 0 R" for i in range(n_pages))

    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode())
    for i in range(n_pages):
        objs.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PW} {PH}] "
                f"/Contents {3 + n_pages + i} 0 R /Resources << /Font << "
                f"/F1 {font_ids[0] + n_pages} 0 R /F2 {font_ids[1] + n_pages} 0 R >> >> >>"
            ).encode()
        )
    for c in contents:
        objs.append(b"<< /Length " + str(len(c)).encode() + b" >>\nstream\n" + c + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    open(path, "wb").write(bytes(out))
    return n_pages


if __name__ == "__main__":
    import sys

    dest = sys.argv[1]
    n = build_pdf(dest, build_content())
    print(f"wrote {dest} ({n} pages)")
