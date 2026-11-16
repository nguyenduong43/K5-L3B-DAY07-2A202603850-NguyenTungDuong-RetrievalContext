"""Extract and chunk the 152-page UNICEF research document for the Advanced Challenge."""
import json
import re
from pathlib import Path
import pypdf


def extract_and_chunk():
    pdf_path = Path("data/advanced/suc-khoe-tam-than-152p.pdf")
    reader = pypdf.PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    print(f"Reading {total_pages} pages from {pdf_path}...")

    chunks = []
    chunk_counter = 0

    for p_idx, page in enumerate(reader.pages):
        page_num = p_idx + 1
        raw_text = page.extract_text() or ""
        clean_text = raw_text.strip()
        if not clean_text:
            continue

        # Split into sections / paragraphs
        # Normalize double newlines
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', clean_text) if len(p.strip()) > 50]
        
        # If page has very little structure, split by ~800 chars
        if not paragraphs:
            # Fallback chunking
            stride = 700
            for i in range(0, len(clean_text), stride):
                sub = clean_text[i : i + 800].strip()
                if len(sub) > 40:
                    chunk_id = f"sktt_p{page_num}_c{chunk_counter}"
                    chunks.append({
                        "id": chunk_id,
                        "source_id": "suc-khoe-tam-than-152p",
                        "source": "data/advanced/suc-khoe-tam-than-152p.pdf",
                        "page": page_num,
                        "text": sub,
                        "metadata": {"page": page_num, "char_count": len(sub)}
                    })
                    chunk_counter += 1
        else:
            for para in paragraphs:
                # If paragraph is too long (> 1200 chars), split it
                if len(para) > 1200:
                    for i in range(0, len(para), 800):
                        sub = para[i : i + 900].strip()
                        if len(sub) > 40:
                            chunk_id = f"sktt_p{page_num}_c{chunk_counter}"
                            chunks.append({
                                "id": chunk_id,
                                "source_id": "suc-khoe-tam-than-152p",
                                "source": "data/advanced/suc-khoe-tam-than-152p.pdf",
                                "page": page_num,
                                "text": sub,
                                "metadata": {"page": page_num, "char_count": len(sub)}
                            })
                            chunk_counter += 1
                else:
                    chunk_id = f"sktt_p{page_num}_c{chunk_counter}"
                    chunks.append({
                        "id": chunk_id,
                        "source_id": "suc-khoe-tam-than-152p",
                        "source": "data/advanced/suc-khoe-tam-than-152p.pdf",
                        "page": page_num,
                        "text": para,
                        "metadata": {"page": page_num, "char_count": len(para)}
                    })
                    chunk_counter += 1

    out_file = Path("data/advanced/chunks.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"Extracted {len(chunks)} chunks across {total_pages} pages to {out_file}")


if __name__ == "__main__":
    extract_and_chunk()
