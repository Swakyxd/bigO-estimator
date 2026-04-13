"""
Configuration for the Big-O Complexity Estimator.
Supports both Ollama (local) and Google Gemini (cloud) backends.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Backend Selection ---
BACKEND = os.getenv("BACKEND", "ollama")

# --- Ollama Settings (Local) ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

# Ordered list of Ollama models available in the selector
OLLAMA_MODELS = [
    "qwen2.5-coder:7b",
    "llama3.2:latest",
    "mistral:latest",
    "gemma3:4b",
    "gemma4:latest",
]
# Legacy single-model alias kept for backwards compat
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", OLLAMA_MODELS[0])

# Speed/size metadata shown in the UI  (label, emoji-speed)
MODEL_META = {
    "qwen2.5-coder:7b":  ("7B  · Code",   "⚡⚡⚡"),   # best for JSON output
    "llama3.2:latest":   ("3B  · Fast",   "⚡⚡⚡"),   # smallest / fastest
    "mistral:latest":    ("7B  · General","⚡⚡"),
    "gemma3:4b":         ("4B  · Fast",   "⚡⚡⚡"),
    "gemma4:latest":     ("New · Fast",   "⚡⚡⚡"),
}

# --- Gemini Settings (Cloud) ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# --- Analysis Settings ---
MAX_RETRIES = 2
TEMPERATURE = 0          # Deterministic reasoning
MAX_TOKENS = 1024        # Cap output length — keeps responses short and fast
ANALYSIS_TIMEOUT = 90   # seconds — abort if model takes longer than this
