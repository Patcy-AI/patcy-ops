"""
llm.py — the agent's language brain (Groq).

Optional and fail-safe by design: if no GROQ_API_KEY is set (or a call fails), every function
falls back to a deterministic template, so the app and the test suite run perfectly with no key.

The split that keeps it safe: the LLM handles the *fuzzy* work — writing drafts, summarizing,
reading messy text. The *consequential* work — money, filings, authorization — stays rule-based
and human-gated in ops.py/guardrails.py. The model never decides to move money.
"""
import os

# Fast + free on Groq. Override with GROQ_MODEL if you want the bigger llama-3.3-70b-versatile.
MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")


def available():
    """True if an LLM key is configured."""
    return bool(os.environ.get("GROQ_API_KEY"))


def chat(system, user, fallback="", temperature=0.3, max_tokens=600):
    """Ask the LLM. Returns its reply, or `fallback` if there's no key / the call fails.
    Never raises — the agent must keep working even when the model is unavailable."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return fallback
    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model=MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        return (resp.choices[0].message.content or "").strip() or fallback
    except Exception:
        return fallback
