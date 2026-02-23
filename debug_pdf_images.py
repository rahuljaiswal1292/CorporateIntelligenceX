import os
import sys
import fitz  # PyMuPDF

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from intelligence_hub.config.config import DATA_DIRECTORY


def debug_pdf_images():
    base_dir = os.path.join(DATA_DIRECTORY, "DFM", "EMAAR", "reports", "structured")
    target_file = "EMAAR_PFR__E_14_02_24.pdf"
    pdf_path = os.path.join(base_dir, target_file)

    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    print(f"Inspecting file: {pdf_path}")
    doc = fitz.open(pdf_path)

    for i, page in enumerate(doc):
        images = page.get_images()
        blocks = page.get_text("blocks")
        print(f"--- Page {i+1} ---")
        print(f"Images: {len(images)}")
        print(f"Text Blocks: {len(blocks)}")
        if blocks:
            print(f"First block: {blocks[0]}")


if __name__ == "__main__":
    debug_pdf_images()
