import fitz


def rebuild_pdf(original_pdf_bytes, ocr_data):

    pdf = fitz.open(stream=original_pdf_bytes, filetype="pdf")

    for page_data in ocr_data["pages"]:
        page_index = page_data["page"] - 1
        page = pdf[page_index]

        for block in page_data["blocks"]:

            if "edited_text" not in block:
                continue

            new_text = block["edited_text"]
            old_text = block["text"]

            x0, y0, x1, y1 = block["box"]

            rect = fitz.Rect(x0, y0, x1, y1)

            # remove old text (mask)
            page.draw_rect(
                rect,
                color=(1, 1, 1),
                fill=(1, 1, 1)
            )

            # insert new text inside same box
            page.insert_textbox(
                rect,
                new_text,
                fontsize=block.get("size", 12),
                fontname="helv",
                color=(0, 0, 0),
                align=0
            )

    output = pdf.tobytes()
    pdf.close()

    return output
