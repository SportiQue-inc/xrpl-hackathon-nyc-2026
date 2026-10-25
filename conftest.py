import os

# Tests never call an LLM: agents fall back to rule-based sentences.
os.environ["LLM_PROVIDER"] = "none"
