import os
import sys
import fitz  # PyMuPDF

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from intelligence_hub.config.config import DATA_DIRECTORY


def debug_pdf_text():
    # Target file from previous logs
    # D:\University\CorporateIntelligenceX\data\DFM\EMAAR\reports\structured\EMAAR_PFR__E_14_02_24.pdf

    # Try to locate the file
    base_dir = os.path.join(DATA_DIRECTORY, "DFM", "EMAAR", "reports", "structured")
    target_file = "EMAAR_PFR__E_14_02_24.pdf"
    pdf_path = os.path.join(base_dir, target_file)

    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        # Try checking other dirs just in case
        return

    print(f"Inspecting file: {pdf_path}")
    doc = fitz.open(pdf_path)
    print(f"Pages: {len(doc)}")

    full_text = ""
    for i, page in enumerate(doc):
        text = page.get_text()
        print(f"--- Page {i+1} ---")
        print(f"Length: {len(text)}")
        print(f"First 100 chars: {repr(text[:100])}")
        full_text += text + "\n"

    print(f"Total Text Length: {len(full_text)}")
    print(f"Full Text Repr (start): {repr(full_text[:200])}")


if __name__ == "__main__":
    debug_pdf_text()
