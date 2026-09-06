"""
Not implemented, by design.

This module would take a QuizQuestion, send it to Ollama, and validate a
structured "answer" response. Combined with quiz/detector.py, that
pipeline amounts to a real-time quiz/exam-answering tool, which this
project does not build regardless of how the request is framed. See
README.md ("Scope decisions") for the full explanation.

ai/ollama.py's generate_completion() is a real, working, general-purpose
text-generation call -- it's used today for on-demand page summarization
(browser/ai_panel.py) and could power other non-quiz features later.
"""
