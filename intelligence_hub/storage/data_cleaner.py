import os
import json
import re
import fitz  # PyMuPDF
import pdfplumber
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
import textwrap
from datetime import datetime


class DataCleaner:
    """
    Handles cleaning and preparation of various data formats (PDF, XLSX, CSV, MD, JSON)
    for embedding into vector databases.
    """

    def __init__(self, output_base_dir: str = "processed_data"):
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(parents=True, exist_ok=True)

    def clean_text(self, text: str) -> str:
        """Remove excessive whitespace and normalize text."""
        if not text:
            return ""
        # Remove multiple newlines
        text = re.sub(r"\n\s*\n", "\n\n", text)
        # Remove repeated spaces
        text = re.sub(r" +", " ", text)
        return text.strip()

    def process_pdf(self, file_path: Path) -> str:
        """
        Extract text and tables from PDF.
        Future Enhancement: Use Vision model for images/charts.
        """
        all_content = []

        # 1. Extract basic text with PyMuPDF (fast)
        try:
            doc = fitz.open(str(file_path))
            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    all_content.append(f"--- PAGE {page_num + 1} TEXT ---\n{text}")
            doc.close()
        except Exception as e:
            print(f"Error reading PDF text with fitz: {e}")

        # 2. Extract tables with pdfplumber (better for structure)
        try:
            with pdfplumber.open(str(file_path)) as pdf:
                for i, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    for j, table in enumerate(tables):
                        if table:
                            df = pd.DataFrame(table[1:], columns=table[0])
                            # Clean dataframe: remove None/NaN
                            df = df.fillna("")
                            md_table = df.to_markdown(index=False)
                            all_content.append(
                                f"--- PAGE {i + 1} TABLE {j + 1} ---\n{md_table}"
                            )
        except Exception as e:
            print(f"Error extracting tables with pdfplumber: {e}")

        return "\n\n".join(all_content)

    def process_excel(self, file_path: Path) -> str:
        """Convert Excel sheets to Markdown tables."""
        output = []
        try:
            xl = pd.ExcelFile(str(file_path))
            for sheet_name in xl.sheet_names:
                df = xl.parse(sheet_name)
                df = df.fillna("")
                md = df.to_markdown(index=False)
                output.append(f"### SHEET: {sheet_name}\n{md}")
        except Exception as e:
            output.append(f"Error processing Excel {file_path.name}: {e}")
        return "\n\n".join(output)

    def process_csv(self, file_path: Path) -> str:
        """Convert CSV to Markdown."""
        try:
            df = pd.read_csv(str(file_path))
            df = df.fillna("")
            return df.to_markdown(index=False)
        except Exception as e:
            return f"Error processing CSV {file_path.name}: {e}"

    def process_json(self, file_path: Path) -> str:
        """Convert JSON to a readable text representation."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Error processing JSON {file_path.name}: {e}"

    def process_markdown(self, file_path: Path) -> str:
        """Normalize Markdown."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error processing Markdown {file_path.name}: {e}"

    def clean_directory(self, input_dir: str):
        """
        Recursively walk input_dir and process all supported files.
        Maintains sub-directory structure inside processed_data/.
        """
        input_path = Path(input_dir)
        if not input_path.exists():
            print(f"Input directory {input_dir} does not exist.")
            return

        print(f"Starting cleaning process for: {input_path}")

        # Use rglob to get everything
        for file_path in input_path.rglob("*"):
            if not file_path.is_file():
                continue

            # Skip hidden files
            if file_path.name.startswith("."):
                continue

            # Determine relative path for output
            rel_path = file_path.relative_to(input_path)
            output_file_name = f"{rel_path.stem}_cleaned.txt"
            output_dir = self.output_base_dir / rel_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_file_name

            ext = file_path.suffix.lower()
            content = ""

            if ext == ".pdf":
                print(f"  Processing PDF: {rel_path}")
                content = self.process_pdf(file_path)
            elif ext in [".xlsx", ".xls"]:
                print(f"  Processing Excel: {rel_path}")
                content = self.process_excel(file_path)
            elif ext == ".csv":
                print(f"  Processing CSV: {rel_path}")
                content = self.process_csv(file_path)
            elif ext in [".md", ".markdown", ".txt"]:
                print(f"  Processing Text/MD: {rel_path}")
                content = self.process_markdown(file_path)
            elif ext == ".json":
                print(f"  Processing JSON: {rel_path}")
                content = self.process_json(file_path)
            else:
                # Unsupported format, skip or just copy?
                continue

            if content:
                cleaned_content = self.clean_text(content)
                meta_header = textwrap.dedent(
                    f"""
                SOURCE_FILE: {file_path.name}
                PROCESSED_AT: {datetime.now().isoformat()}
                FILE_TYPE: {ext}
                ----------------------------------------
                
                """
                ).strip()

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(meta_header + "\n\n" + cleaned_content)

        print(f"Cleaning complete. Output at: {self.output_base_dir}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Clean and prepare data for RAG pipeline."
    )
    parser.add_argument(
        "input_dir", help="Directory containing raw data (e.g., data/dfm/EMAAR)"
    )
    parser.add_argument(
        "--output", default="processed_data", help="Base output directory"
    )

    args = parser.parse_args()

    cleaner = DataCleaner(output_base_dir=args.output)
    cleaner.clean_directory(args.input_dir)
