import fitz


def replace_text_in_pdf(pdf_bytes, old_text, new_text):

    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")

    for page in pdf:

        text_dict = page.get_text("dict")

        for block in text_dict.get("blocks", []):

            if "lines" not in block:
                continue

            for line in block["lines"]:

                for span in line["spans"]:

                    text = span["text"].strip()

                    if text != old_text:
                        continue

                    x0, y0, x1, y1 = span["bbox"]

                    rect = fitz.Rect(
                        x0,
                        y0,
                        x1,
                        y1
                    )

                    # Cover old text
                    page.draw_rect(
                        rect,
                        color=(1, 1, 1),
                        fill=(1, 1, 1)
                    )

                    # Draw new text inside same box
                    page.insert_textbox(
                        rect,
                        new_text,
                        fontsize=span["size"],
                        fontname="helv",
                        color=(0, 0, 0),
                        align=0
                    )

    output = pdf.tobytes()

    pdf.close()

    return output
