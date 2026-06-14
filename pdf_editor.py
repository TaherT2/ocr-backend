import fitz


def rebuild_pdf(original_pdf_bytes, ocr_data):

    pdf = fitz.open(stream=original_pdf_bytes, filetype="pdf")

    for page_data in ocr_data["pages"]:

        page_index = page_data["page"] - 1
        page = pdf[page_index]

        # ==========================================
        # STEP 1: Add redactions
        # ==========================================

        redactions = []

        for block in page_data["blocks"]:

            if "edited_text" not in block:
                continue

            x0, y0, x1, y1 = block["box"]

            rect = fitz.Rect(x0, y0, x1, y1)

            page.add_redact_annot(
                rect,
                fill=(1, 1, 1)
            )

            redactions.append(block)

        # Permanently remove original content
        if redactions:
            page.apply_redactions()

        # ==========================================
        # STEP 2: Draw replacement text
        # ==========================================

        for block in redactions:

            new_text = block["edited_text"]

            x0, y0, x1, y1 = block["box"]

            font_size = block.get("size", 12)

            insert_x = x0
            insert_y = y1 - (font_size * 0.20)

            page.insert_text(
                (insert_x, insert_y),
                new_text,
                fontsize=font_size,
                fontname="helv",
                color=(0, 0, 0)
            )

    output = pdf.tobytes()

    pdf.close()

    return output
