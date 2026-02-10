import os
from dotenv import load_dotenv

# Load .env file from project root by default
load_dotenv()

# API Keys
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Model Configuration
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4-turbo")
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.1"))
MODEL_MAX_TOKENS = int(os.getenv("MODEL_MAX_TOKENS", "4096"))

# Agent Configuration
AGENT_MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "15"))
AGENT_MAX_EXECUTION_TIME = int(os.getenv("AGENT_MAX_EXECUTION_TIME", "300"))  # seconds

# General Data Directory
DATA_DIRECTORY = os.getenv("DATA_DIRECTORY", os.path.join(os.getcwd(), "data"))

# ChromaDB Configuration
CHROMADB_PERSIST_DIRECTORY = os.getenv(
    "CHROMADB_PERSIST_DIRECTORY", os.path.join(DATA_DIRECTORY, "chroma_db")
)
CHROMADB_COLLECTION_NAME = os.getenv("CHROMADB_COLLECTION_NAME", "company_profiles")

# Search Configuration
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "10"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
