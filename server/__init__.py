"""
Backend client package.

client.py sends data to a configurable backend URL and never blocks or
breaks browsing if that backend is offline. It is currently used for one
real thing: optionally saving AI Assistant page summaries. It has no
quiz-answer submission logic, since quiz detection/answering (quiz/,
ai/verifier.py) remains unimplemented — see README.md for why.
"""