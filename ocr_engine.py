# Inside process_pdf in ocr_engine.py
# ... after getting ocr_result ...
if ocr_result and ocr_result[0]:
    for line in ocr_result[0]:
        box = line[0] # These are pixel coordinates from the image
        text = clean_text(line[1][0])
        conf = float(line[1][1])
        if not text: continue
        
        # FIX: Map pixel coordinates back to PDF points
        # 1.5 is the matrix scale factor we used in get_pixmap
        x0 = min([p[0] for p in box]) / 1.5
        y0 = min([p[1] for p in box]) / 1.5
        x1 = max([p[0] for p in box]) / 1.5
        y1 = max([p[1] for p in box]) / 1.5
        
        bbox = [x0, y0, x1, y1]
        
        blocks.append(build_block(
            block_id, text, bbox, detect_script(text), 
            assign_font(detect_script(text)), 12, conf, "ocr"
        ))
        block_id += 1
