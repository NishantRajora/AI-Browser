"""
Prompt templates for AI Browser's local-AI features.

Currently used by: on-demand page summarization (browser/ai_panel.py +
ai/ollama.generate_completion). This module intentionally does NOT
contain any quiz/question/answer prompt template — see ai/verifier.py
for why that feature is not implemented.
"""

from __future__ import annotations

# Keep prompts well under typical local-model context windows.
_MAX_PAGE_TEXT_CHARS = 6000


def build_summary_prompt(page_title: str, page_text: str) -> str:
    """
    Build a prompt asking the model to summarize a webpage's visible text.

    The page text is truncated to keep the prompt a reasonable size for
    small local models; the model is explicitly told not to invent
    information beyond what's given.
    """
    trimmed_text = page_text.strip()[:_MAX_PAGE_TEXT_CHARS]
    title = (page_title or "Untitled page").strip()

    return (
        "You are summarizing a webpage for someone who hasn't read it.\n"
        "Write a concise summary in 3-5 sentences covering the main points.\n"
        "Only use information present in the text below; do not add facts "
        "that aren't there.\n\n"
        f"Page title: {title}\n\n"
        f"Page text:\n{trimmed_text}"
    )
