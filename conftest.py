import os

# Tests never call an LLM: agents fall back to rule-based sentences.
os.environ["LLM_PROVIDER"] = "none"
os.environ["LLM_CACHE"] = os.path.join(os.path.dirname(__file__), "tests", "no_llm_cache.json")  # never replay
os.environ["LLM_RECORD"] = "0"
