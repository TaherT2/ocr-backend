import fitz


def export_pdf_from_blocks(pdf_bytes, ocr_result):
    """
    Rebuilds PDF using edited OCR JSON blocks.
    """

    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")

    for page_data in ocr_result["pages"]:

        page_index = page_data["page"] - 1
        page = pdf[page_index]

        # Go through all blocks
        for block in page_data["blocks"]:

            x0, y0, x1, y1 = block["box"]

            rect = fitz.Rect(x0, y0, x1, y1)

            # 1. erase old text area
            page.draw_rect(
                rect,
                color=(1, 1, 1),
                fill=(1, 1, 1)
            )

            # 2. write new text
            page.insert_textbox(
                rect,
                block["text"],
                fontsize=block.get("size", 12),
                fontname="helv",
                color=(0, 0, 0),
                align=0
            )

    output = pdf.tobytes()
    pdf.close()

    return output
