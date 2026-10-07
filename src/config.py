# -*- coding: utf-8 -*-
"""Configuration module for Arabic-first Customer Support Resolution Agent."""
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

if not os.getenv("CI"):
    load_dotenv(override=True)
else:
    load_dotenv(override=False)

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "arabic_support_dataset"
DATA_DIR = DATASET_DIR / "data"

# Dataset paths
DB_PATH = DATA_DIR / "db.json"
POLICIES_PATH = DATA_DIR / "policies.json"
TOOLS_PATH = DATA_DIR / "tools.json"
TICKETS_PATH = DATA_DIR / "tickets.jsonl"
PROMOS_PATH = DATA_DIR / "promos.json"
EPISODIC_SEED_PATH = DATA_DIR / "episodic_seed.jsonl"

# Environment & Business Constraints
# Frozen reference clock per project spec (do not change)
REFERENCE_TIME = datetime(2026, 9, 15, 10, 0, 0)
REFERENCE_TIME_ISO = "2026-09-15T10:00:00"

# Auto refund threshold (Policy P04, P05) - requires human-in-the-loop if above
AUTO_REFUND_LIMIT_USD = 50.0

# Agent step budget
MAX_STEPS = 8
TEMPERATURE = 0.0

# LLM Providers & Keys
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Default Models
DEFAULT_MAIN_MODEL = os.getenv("DEFAULT_MAIN_MODEL", "gemini-3.8-flash")
DEFAULT_FAST_MODEL = os.getenv("DEFAULT_FAST_MODEL", "gemini-3.8-flash")
