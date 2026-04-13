"""
LLM interaction layer for the Big-O Complexity Estimator.
Supports both Ollama (local) and Google Gemini (cloud) backends.
Adds: streaming output, dynamic model selection, batch analysis.
"""

import openai
import requests
from typing import Generator

from config import (
    BACKEND,
    OLLAMA_BASE_URL,
    GOOGLE_API_KEY,
    GEMINI_MODEL,
    MAX_RETRIES,
    TEMPERATURE,
    OLLAMA_MODELS,
    MAX_TOKENS,
    ANALYSIS_TIMEOUT,
)
from prompt import SYSTEM_PROMPT, BATCH_SYSTEM_PROMPT
from parser import parse_output, parse_batch_output


# ── GPU memory release ────────────────────────────────────────────────────────

def unload_model(model: str) -> bool:
    """
    Tell Ollama to immediately evict `model` from GPU/CPU memory by
    sending a no-op generate request with keep_alive=0.

    Returns True if the unload request was accepted, False otherwise.
    Only has an effect when BACKEND == "ollama".
    """
    if BACKEND != "ollama":
        return False
    try:
        base = OLLAMA_BASE_URL.rstrip("/").removesuffix("/v1")
        with requests.post(
            f"{base}/api/generate",
            json={"model": model, "keep_alive": 0},
            timeout=8,
            stream=True,       # return immediately, don't read whole body
        ) as resp:
            resp.raise_for_status()
        return True
    except Exception:
        return False  # never crash the app over this


# ── Default model helpers ──────────────────────────────────────────────────────

def _get_client(model: str | None = None) -> tuple:
    """
    Return an (OpenAI-compat client, resolved model name) pair.
    `model` overrides the default from config when provided.
    """
    if BACKEND == "ollama":
        client = openai.OpenAI(
            base_url=OLLAMA_BASE_URL,
            api_key="ollama",
        )
        resolved_model = model or OLLAMA_MODELS[0]
        return client, resolved_model

    elif BACKEND == "gemini":
        if not GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY is not set. "
                "Set BACKEND=ollama in .env to use local LLM, "
                "or provide a GOOGLE_API_KEY for Gemini."
            )
        client = openai.OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=GOOGLE_API_KEY,
        )
        return client, GEMINI_MODEL

    else:
        raise ValueError(f"Unknown backend: {BACKEND}. Use 'ollama' or 'gemini'.")


# ── Standard (non-streaming) analysis ─────────────────────────────────────────

def analyze_complexity(code: str, language: str = "Auto Detect", model: str | None = None) -> dict:
    """
    Analyze the Big-O complexity of a code snippet.

    Args:
        code:     The source code to analyze.
        language: Programming language hint (or "Auto Detect").
        model:    Ollama model name to use (overrides config default).

    Returns:
        A dict with keys: time_complexity, space_complexity,
        best_case, worst_case, reasoning, success, plus
        optimization fields.
    """
    client, resolved_model = _get_client(model)
    lang_hint = f"\nLanguage: {language}" if language != "Auto Detect" else ""
    user_prompt = f"Analyze the following code snippet:{lang_hint}\n\n```\n{code}\n```"

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=resolved_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                timeout=ANALYSIS_TIMEOUT,
            )
            raw_text = response.choices[0].message.content
            result = parse_output(raw_text)
            result["model_used"] = resolved_model
            if result["success"]:
                return result
            last_error = result["reasoning"]
        except Exception as e:
            last_error = str(e)

    return {
        "time_complexity": "Error",
        "space_complexity": "Error",
        "best_case": "Error",
        "worst_case": "Error",
        "reasoning": f"Analysis failed after {MAX_RETRIES} attempts. Last error: {last_error}",
        "model_used": resolved_model if 'resolved_model' in dir() else "unknown",
        "success": False,
    }


# ── Streaming analysis ─────────────────────────────────────────────────────────

def analyze_complexity_stream(
    code: str,
    language: str = "Auto Detect",
    model: str | None = None,
) -> Generator[str, None, None]:
    """
    Stream the raw LLM token-by-token response, then yield a final
    sentinel dict-like string "__RESULT__:<json>" for the caller to parse.

    Yields:
        str tokens as they arrive from the model.
        A final "__RESULT__:<raw_full_text>" sentinel.
    """
    client, resolved_model = _get_client(model)
    lang_hint = f"\nLanguage: {language}" if language != "Auto Detect" else ""
    user_prompt = f"Analyze the following code snippet:{lang_hint}\n\n```\n{code}\n```"

    full_text = ""
    try:
        stream = client.chat.completions.create(
            model=resolved_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            timeout=ANALYSIS_TIMEOUT,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_text += delta
                yield delta
    except Exception as e:
        yield f"\n\n[Stream error: {e}]"
        full_text = ""

    # Yield sentinel so the caller can parse structured output
    yield f"__RESULT__{full_text}"


# ── Batch file analysis ────────────────────────────────────────────────────────

def analyze_file_functions(
    functions: list[dict],
    language: str = "Auto Detect",
    model: str | None = None,
) -> list[dict]:
    """
    Analyze a list of extracted functions from a file.

    Args:
        functions: List of {"name": str, "code": str} dicts.
        language:  Language hint.
        model:     Model override.

    Returns:
        List of result dicts, each containing the function name plus
        all complexity fields.
    """
    results = []
    for fn in functions:
        result = analyze_complexity(fn["code"], language, model)
        result["function_name"] = fn["name"]
        results.append(result)
    return results
