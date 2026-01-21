#!/usr/bin/env python3
"""Database initialization script"""
import os
import sys
import chromadb
from intelligence_hub.config.settings import config
from intelligence_hub.utils.helpers import setup_logging

logger = setup_logging()

def initialize_database():
    """Initialize ChromaDB collections"""
    try:
        logger.info("Initializing ChromaDB database...")

        os.makedirs(config.VECTOR_DB_PATH, exist_ok=True)

        client = chromadb.PersistentClient(path=config.VECTOR_DB_PATH)

        identity_collection = client.get_or_create_collection(
            name="company_identities",
            metadata={"description": "Resolved company identities and tickers"}
        )

        data_collection = client.get_or_create_collection(
            name="company_data",
            metadata={"description": "Cached company financial and profile data"}
        )

        logger.info("✅ Database initialized successfully")
        logger.info(f"📁 Database path: {config.VECTOR_DB_PATH}")
        logger.info(f"📊 Collections created: company_identities, company_data")

        add_sample_data(identity_collection, data_collection)

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)

def add_sample_data(identity_collection, data_collection):
    """Add sample data for testing"""
    try:
        logger.info("Adding sample data...")

        sample_identities = [
            {
                "id": "fab",
                "document": '{"canonical_name": "First Abu Dhabi Bank PJSC", "ticker": "FAB", "exchange": "ADX"}',
                "metadata": {"source": "sample", "timestamp": "2024-01-01"}
            },
            {
                "id": "enbd",
                "document": '{"canonical_name": "Emirates NBD Bank PJSC", "ticker": "ENBD", "exchange": "DFM"}',
                "metadata": {"source": "sample", "timestamp": "2024-01-01"}
            },
            {
                "id": "adcb",
                "document": '{"canonical_name": "Abu Dhabi Commercial Bank PJSC", "ticker": "ADCB", "exchange": "ADX"}',
                "metadata": {"source": "sample", "timestamp": "2024-01-01"}
            }
        ]

        identity_collection.add(
            documents=[item["document"] for item in sample_identities],
            ids=[item["id"] for item in sample_identities],
            metadatas=[item["metadata"] for item in sample_identities]
        )

        logger.info("✅ Sample data added successfully")

    except Exception as e:
        logger.warning(f"⚠️ Failed to add sample data: {e}")

if __name__ == "__main__":
    initialize_database()