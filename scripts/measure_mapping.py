"""Measure schema mapping against ground truth: the configured LLM (or the replay cache) next to the
name-matching rules. Prints JSON. With no LLM key the LLM column falls back to rules and says so."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentrail.contract import mapping  # noqa: E402

if __name__ == "__main__":
    llm = mapping.measure()
    rules = mapping.measure(lambda s, i: None)
    print(json.dumps({"llm": {k: v for k, v in llm.items() if k != "detail"},
                      "llm_proposed_by": sorted({d["by"] for d in llm["detail"]}),
                      "rules": {k: v for k, v in rules.items() if k != "detail"},
                      "llm_detail": llm["detail"]}, indent=1))
