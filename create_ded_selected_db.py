"""
create_ded_selected_db.py
─────────────────────────
Reads selected_corporates_new.json (the enriched corporate dataset) and
loads every record into a fresh ChromaDB collection called 'ded_selected'
stored at  data/chroma_ded_selected.

Documents (used for embedding & semantic search):
    The 'enhanced_searchable_text' field — contains name, Arabic name,
    sector, company type, tags, aliases, activities and description.

Metadata (stored for LLM reasoning / filtering):
    All scalar fields + JSON-encoded list fields so ChromaDB can accept them.

Run:
    ./venv/Scripts/python.exe create_ded_selected_db.py
"""

import json
import os
import hashlib
import chromadb

# ── Paths ────────────────────────────────────────────────────────────────────
SOURCE_JSON = "data/ded_data/selected_corporates_ded_data.json"
DB_PATH     = os.path.join("data", "chroma_ded_selected")
COLLECTION  = "ded_selected"
BATCH_SIZE  = 100


def safe_str(val) -> str:
    """Ensure a value is a plain string (for ChromaDB metadata)."""
    if isinstance(val, (list, dict)):
        return json.dumps(val, ensure_ascii=False)
    return str(val) if val is not None else ""


def build_document(item: dict) -> str:
    """
    Primary text that gets embedded.
    Prefers the richer enhanced_searchable_text; falls back gracefully.
    """
    enhanced = item.get("enhanced_searchable_text", "").strip()
    if enhanced:
        return enhanced

    # Fallback if field is missing
    name      = item.get("trade_name_en", "Unknown")
    sector    = item.get("sector", "")
    ctype     = item.get("company_type", "")
    tags      = ", ".join(item.get("sector_tags", []))
    aliases   = ", ".join(item.get("known_aliases", []))
    acts      = ", ".join(item.get("activities", []))
    desc      = item.get("description", "")
    return (
        f"Company Name: {name}. Sector: {sector}. Type: {ctype}. "
        f"Tags: {tags}. Aliases: {aliases}. Activities: {acts}. {desc}"
    ).strip()


def build_metadata(item: dict) -> dict:
    """
    Flat dict of scalar / JSON-encoded values for ChromaDB.
    ChromaDB only supports str / int / float / bool values in metadata.
    """
    return {
        # ── Identity ──────────────────────────────────────────────────────
        "trade_name_en":         item.get("trade_name_en", ""),
        "trade_name_ar":         item.get("trade_name_ar", ""),

        # ── Enriched classification ───────────────────────────────────────
        "sector":                item.get("sector", "General Business"),
        "company_type":          item.get("company_type", "Company"),
        "sector_tags":           safe_str(item.get("sector_tags", [])),
        "description":           item.get("description", ""),
        "known_aliases":         safe_str(item.get("known_aliases", [])),
        "is_government_entity":  bool(item.get("is_government_entity", False)),
        "is_priority_corporate": bool(item.get("is_priority_corporate", False)),
        "country_of_origin":     item.get("country_of_origin", "UAE"),
        "llm_hint":              item.get("llm_hint", ""),

        # ── License / registration info ───────────────────────────────────
        "license_count":         int(item.get("license_count", 0)),
        "license_categories":    safe_str(item.get("license_categories", [])),
        "issue_authorities":     safe_str(item.get("issue_authorities", [])),
        "activities":            safe_str(item.get("activities", [])),
        "activity_count":        int(item.get("activity_count", 0)),
        "earliest_issue_date":   item.get("earliest_issue_date", ""),
        "latest_expiry_date":    item.get("latest_expiry_date", ""),
        "commerce_register_numbers": safe_str(item.get("commerce_register_numbers", [])),
        "license_numbers":       safe_str(item.get("license_numbers", [])),

        # ── Group label from original selection process ───────────────────
        "requested_group":       item.get("requested_group", ""),
    }


def make_id(item: dict, index: int) -> str:
    """
    Stable, deterministic doc-id based on trade name + first license number.
    Falls back to index if needed.
    """
    name = item.get("trade_name_en", "")
    lnum = str(item.get("license_numbers", [index])[0]) if item.get("license_numbers") else str(index)
    raw  = f"{name}_{lnum}"
    return "corp_" + hashlib.md5(raw.encode()).hexdigest()[:12]


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    # 1. Load enriched JSON
    if not os.path.exists(SOURCE_JSON):
        raise FileNotFoundError(
            f"Source file not found: {SOURCE_JSON}\n"
            "Run generate_enriched_corporates.py first."
        )

    print(f"Loading {SOURCE_JSON} …")
    with open(SOURCE_JSON, encoding="utf-8") as f:
        data: list = json.load(f)
    print(f"  → {len(data)} records loaded.")

    # 2. Init ChromaDB
    os.makedirs(DB_PATH, exist_ok=True)
    print(f"Initialising ChromaDB at '{DB_PATH}' …")
    client = chromadb.PersistentClient(path=DB_PATH)

    # 3. Drop & recreate collection (fresh load)
    try:
        client.delete_collection(COLLECTION)
        print(f"  → Deleted existing collection '{COLLECTION}'.")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION,
        metadata={
            "description":  "Enriched DED selected corporates with sector, aliases & LLM hints",
            "source":       SOURCE_JSON,
            "total_records": str(len(data)),
        },
    )
    print(f"  → Collection '{COLLECTION}' created.")

    # 4. Build batches
    ids, documents, metadatas = [], [], []
    seen_ids: set = set()

    for i, item in enumerate(data):
        doc_id = make_id(item, i)

        # Handle duplicate IDs (e.g. same company with variant names)
        if doc_id in seen_ids:
            doc_id = doc_id + f"_{i}"
        seen_ids.add(doc_id)

        ids.append(doc_id)
        documents.append(build_document(item))
        metadatas.append(build_metadata(item))

    # 5. Batch upsert
    total = len(ids)
    print(f"Inserting {total} documents in batches of {BATCH_SIZE} …")
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        collection.add(
            ids=ids[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )
        print(f"  ✓ Batch {start + 1}–{end} added.")

    # 6. Verify
    count = collection.count()
    print(f"\n✅ Done! '{COLLECTION}' collection has {count} documents.")
    print(f"   DB path : {os.path.abspath(DB_PATH)}")

    # 7. Quick smoke-test query
    print("\n── Smoke-test: searching 'Emirates NBD bank Dubai' ──")
    results = collection.query(
        query_texts=["Emirates NBD bank Dubai"],
        n_results=3,
        include=["metadatas", "distances", "documents"],
    )
    for rank, (meta, dist) in enumerate(
        zip(results["metadatas"][0], results["distances"][0]), 1
    ):
        print(
            f"  #{rank}  [{dist:.4f}]  {meta['trade_name_en']}"
            f"  |  {meta['sector']}  |  priority={meta['is_priority_corporate']}"
        )

    print("\n── Smoke-test: searching 'ADNOC oil gas Abu Dhabi' ──")
    results = collection.query(
        query_texts=["ADNOC oil gas Abu Dhabi"],
        n_results=3,
        include=["metadatas", "distances"],
    )
    for rank, (meta, dist) in enumerate(
        zip(results["metadatas"][0], results["distances"][0]), 1
    ):
        print(
            f"  #{rank}  [{dist:.4f}]  {meta['trade_name_en']}"
            f"  |  {meta['sector']}  |  gov={meta['is_government_entity']}"
        )


if __name__ == "__main__":
    main()
