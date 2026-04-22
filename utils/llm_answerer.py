"""
OpenRouter-based quiz answerer — zero external dependencies (uses urllib).

answer_question(question, options, api_key, topic, model) -> Optional[int]
  Returns the 0-based index of the best answer, or None on any failure.

Strategy: Chain-of-Thought reasoning.
  Instead of asking the model to output just a digit, we ask it to reason
  step-by-step and end with "ANSWER: N". This dramatically improves accuracy
  vs. asking for a bare number (especially on tricky/ambiguous questions).

Model fallback chain: if primary model returns 429/error, tries next in list.
"""

import json
import re
import urllib.error
import urllib.request
from typing import List, Optional, Tuple

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# (display_label, model_id)
FREE_MODELS: List[Tuple[str, str]] = [
    ("GPT-4o-mini class 120B (free)",   "openai/gpt-oss-120b:free"),
    ("Llama 3.3 70B (free)",            "meta-llama/llama-3.3-70b-instruct:free"),
    ("Hermes 3 — 405B (free)",          "nousresearch/hermes-3-llama-3.1-405b:free"),
    ("Nvidia Nemotron 120B (free)",     "nvidia/nemotron-3-super-120b-a12b:free"),
    ("GPT-4o-mini class 20B (free)",    "openai/gpt-oss-20b:free"),
    ("Gemma 3 27B (free)",              "google/gemma-3-27b-it:free"),
    ("Gemma 4 31B (free)",              "google/gemma-4-31b-it:free"),
    ("Qwen 3 80B (free)",               "qwen/qwen3-next-80b-a3b-instruct:free"),
    ("Gemma 3 12B (free)",              "google/gemma-3-12b-it:free"),
    ("Llama 3.2 3B (free)",             "meta-llama/llama-3.2-3b-instruct:free"),
]

DEFAULT_MODEL = FREE_MODELS[0][1]

# Fallback order when primary model fails (429 / network error)
_FALLBACK_MODELS = [
    "openai/gpt-oss-20b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
]


def _extract_index(text: str, n_options: int) -> Optional[int]:
    """Extract answer index from model response.
    Looks for 'ANSWER: N' pattern first, then any standalone digit.
    """
    # Primary: ANSWER: N (from chain-of-thought prompt)
    m = re.search(r'ANSWER\s*:\s*(\d+)', text, re.IGNORECASE)
    if m:
        idx = int(m.group(1))
        if 0 <= idx < n_options:
            return idx

    # Secondary: last standalone digit in response (model may not follow format exactly)
    digits = [int(d) for d in re.findall(r'\b(\d+)\b', text) if int(d) < n_options]
    if digits:
        return digits[-1]   # last digit is usually the final answer

    return None


def _call_model(model: str, payload_dict: dict, api_key: str) -> Optional[str]:
    """Make one API call. Returns raw text content or None on error."""
    payload = json.dumps(payload_dict).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://github.com/ABAonDEMAND-automation",
            "X-Title":       "ABA on Demand Automator",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            return content if content else None
    except (urllib.error.HTTPError, urllib.error.URLError,
            KeyError, IndexError, json.JSONDecodeError):
        return None


def answer_question(
    question: str,
    options: List[str],
    api_key: str,
    topic: str = "",
    model: str = "",
) -> Optional[int]:
    """
    Use chain-of-thought reasoning to pick the correct MS Learn quiz answer.
    Tries the primary model first; falls back to alternatives on failure.
    Returns option index (0-based) or None if all models fail.
    """
    if not api_key or not api_key.strip():
        return None
    if not options:
        return None

    primary = model.strip() or DEFAULT_MODEL
    opts_lines = "\n".join(f"{i}: {opt}" for i, opt in enumerate(options))
    topic_ctx  = f"Topic: {topic}\n" if topic else ""

    system_msg = (
        "You are a Microsoft technology expert answering knowledge check quizzes "
        "for Microsoft Learn certifications. "
        "You have deep knowledge of Azure, GitHub, Python, C#, JavaScript, TypeScript, "
        "web development, databases, DevOps, and AI/ML fundamentals. "
        "Always reason carefully before answering."
    )

    user_msg = (
        f"{topic_ctx}"
        f"Question: {question}\n\n"
        f"Options:\n{opts_lines}\n\n"
        "Think step by step: analyze each option and explain why it is correct or incorrect. "
        "Then on the LAST line, write exactly:\n"
        "ANSWER: <number>\n"
        "(where <number> is the 0-based index of the correct option)"
    )

    base_payload = {
        "max_tokens": 400,
        "temperature": 0.1,   # slight non-zero for reasoning quality
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_msg},
        ],
    }

    # Try primary model, then fallbacks
    models_to_try = [primary] + [m for m in _FALLBACK_MODELS if m != primary]

    for try_model in models_to_try:
        content = _call_model(try_model, {**base_payload, "model": try_model}, api_key)
        if content is None:
            continue
        idx = _extract_index(content.strip(), len(options))
        if idx is not None:
            return idx

    return None
