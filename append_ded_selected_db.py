"""
append_ded_selected_db.py
─────────────────────────
Incrementally adds NEW entries from selected_corporates_ded_data.json into
the existing  data/chroma_ded_selected  ChromaDB collection.

Only records whose deterministic ID is NOT already in the collection are
inserted — existing records are left untouched.

Run:
    ./venv/Scripts/python.exe append_ded_selected_db.py

Optional flag  --dry-run  prints what would be added without touching the DB.
"""

import argparse
import hashlib
import json
import os

import chromadb

# ── Paths (must match create_ded_selected_db.py) ─────────────────────────────
SOURCE_JSON = "data/ded_data/selected_corporates_ded_data.json"
DB_PATH     = os.path.join("data", "chroma_ded_selected")
COLLECTION  = "ded_selected"
BATCH_SIZE  = 100


# ── Helpers (kept identical to create_ded_selected_db.py) ─────────────────────

def safe_str(val) -> str:
    if isinstance(val, (list, dict)):
        return json.dumps(val, ensure_ascii=False)
    return str(val) if val is not None else ""


def build_document(item: dict) -> str:
    enhanced = item.get("enhanced_searchable_text", "").strip()
    if enhanced:
        return enhanced
    name    = item.get("trade_name_en", "Unknown")
    sector  = item.get("sector", "")
    ctype   = item.get("company_type", "")
    tags    = ", ".join(item.get("sector_tags", []))
    aliases = ", ".join(item.get("known_aliases", []))
    acts    = ", ".join(item.get("activities", []))
    desc    = item.get("description", "")
    return (
        f"Company Name: {name}. Sector: {sector}. Type: {ctype}. "
        f"Tags: {tags}. Aliases: {aliases}. Activities: {acts}. {desc}"
    ).strip()


def build_metadata(item: dict) -> dict:
    return {
        "trade_name_en":             item.get("trade_name_en", ""),
        "trade_name_ar":             item.get("trade_name_ar", ""),
        "sector":                    item.get("sector", "General Business"),
        "company_type":              item.get("company_type", "Company"),
        "sector_tags":               safe_str(item.get("sector_tags", [])),
        "description":               item.get("description", ""),
        "known_aliases":             safe_str(item.get("known_aliases", [])),
        "is_government_entity":      bool(item.get("is_government_entity", False)),
        "is_priority_corporate":     bool(item.get("is_priority_corporate", False)),
        "country_of_origin":         item.get("country_of_origin", "UAE"),
        "llm_hint":                  item.get("llm_hint", ""),
        "license_count":             int(item.get("license_count", 0)),
        "license_categories":        safe_str(item.get("license_categories", [])),
        "issue_authorities":         safe_str(item.get("issue_authorities", [])),
        "activities":                safe_str(item.get("activities", [])),
        "activity_count":            int(item.get("activity_count", 0)),
        "earliest_issue_date":       item.get("earliest_issue_date", ""),
        "latest_expiry_date":        item.get("latest_expiry_date", ""),
        "commerce_register_numbers": safe_str(item.get("commerce_register_numbers", [])),
        "license_numbers":           safe_str(item.get("license_numbers", [])),
        "requested_group":           item.get("requested_group", ""),
    }


def make_id(item: dict, index: int) -> str:
    """Stable deterministic ID — identical logic to create_ded_selected_db.py."""
    name = item.get("trade_name_en", "")
    lnum = (
        str(item.get("license_numbers", [index])[0])
        if item.get("license_numbers")
        else str(index)
    )
    raw = f"{name}_{lnum}"
    return "corp_" + hashlib.md5(raw.encode()).hexdigest()[:12]


# ── Main ──────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False):
    # 1. Load JSON
    if not os.path.exists(SOURCE_JSON):
        raise FileNotFoundError(f"Source file not found: {SOURCE_JSON}")

    print(f"Loading {SOURCE_JSON} …")
    with open(SOURCE_JSON, encoding="utf-8") as f:
        data: list = json.load(f)
    print(f"  → {len(data)} records in JSON.")

    # 2. Connect to existing ChromaDB (do NOT delete the collection)
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"ChromaDB not found at '{DB_PATH}'.\n"
            "Run create_ded_selected_db.py first to initialise it."
        )

    print(f"Opening ChromaDB at '{DB_PATH}' …")
    client = chromadb.PersistentClient(path=DB_PATH)

    try:
        collection = client.get_collection(COLLECTION)
    except Exception:
        raise RuntimeError(
            f"Collection '{COLLECTION}' does not exist.\n"
            "Run create_ded_selected_db.py first."
        )

    existing_count = collection.count()
    print(f"  → Collection '{COLLECTION}' has {existing_count} existing documents.")

    # 3. Fetch all existing IDs from ChromaDB (paginated to avoid memory issues)
    print("Fetching existing IDs …")
    existing_ids: set[str] = set()
    page_size = 500
    offset = 0
    while True:
        page = collection.get(
            limit=page_size,
            offset=offset,
            include=[],          # IDs are always returned; skip documents/metadata
        )
        batch_ids = page.get("ids", [])
        if not batch_ids:
            break
        existing_ids.update(batch_ids)
        offset += len(batch_ids)
        if len(batch_ids) < page_size:
            break
    print(f"  → {len(existing_ids)} IDs fetched.")

    # 4. Compute IDs for every JSON record; collect only the new ones
    new_ids, new_docs, new_metas = [], [], []
    seen_in_json: set[str] = set()          # guard against duplicates within JSON
    skipped = 0

    for i, item in enumerate(data):
        doc_id = make_id(item, i)

        # Replicate the duplicate-suffix logic from the original script
        if doc_id in seen_in_json:
            doc_id = doc_id + f"_{i}"
        seen_in_json.add(doc_id)

        if doc_id in existing_ids:
            skipped += 1
            continue                         # already in DB — skip

        new_ids.append(doc_id)
        new_docs.append(build_document(item))
        new_metas.append(build_metadata(item))

    print(f"\n── Summary ──────────────────────────────────")
    print(f"  Already in DB  : {skipped}")
    print(f"  New to insert  : {len(new_ids)}")

    if not new_ids:
        print("\n✅ Nothing to add — ChromaDB is already up to date.")
        return

    if dry_run:
        print("\n⚠️  DRY RUN — no changes written. New companies that would be added:")
        for meta in new_metas:
            print(f"    • {meta['trade_name_en']}  [{meta['sector']}]")
        return

    # 5. Batch insert the new documents
    print(f"\nInserting {len(new_ids)} new documents in batches of {BATCH_SIZE} …")
    for start in range(0, len(new_ids), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(new_ids))
        collection.add(
            ids=new_ids[start:end],
            documents=new_docs[start:end],
            metadatas=new_metas[start:end],
        )
        print(f"  ✓ Batch {start + 1}–{end} added.")

    # 6. Final count
    final_count = collection.count()
    print(f"\n✅ Done!  '{COLLECTION}' now has {final_count} documents  "
          f"(was {existing_count}, added {final_count - existing_count}).")

    # 7. Quick smoke-test on one of the newly added companies
    if new_metas:
        sample_name = new_metas[0]["trade_name_en"]
        print(f"\n── Smoke-test: searching '{sample_name}' ──")
        results = collection.query(
            query_texts=[sample_name],
            n_results=3,
            include=["metadatas", "distances"],
        )
        for rank, (meta, dist) in enumerate(
            zip(results["metadatas"][0], results["distances"][0]), 1
        ):
            print(
                f"  #{rank}  [{dist:.4f}]  {meta['trade_name_en']}"
                f"  |  {meta['sector']}  |  priority={meta['is_priority_corporate']}"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Incrementally append new records to the ded_selected ChromaDB."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be added without writing anything.",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
