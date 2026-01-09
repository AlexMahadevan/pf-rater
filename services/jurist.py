from typing import List, Dict, Any
from services.clients import get_anthropic
from config import FLAGS
from utils.parsing import extract_response_text

JURIST_PROMPT = """
You are the **Legacy Jurist**, an expert in PolitiFact's fact-checking methodology and historical jurisprudence.
Your role is to analyze a current claim against a set of retrieved historical fact-checks to ensure consistency in logic and determine if any significant "shifts" in editorial standards are present.

### Current Claim:
{query}

### Retrieved Historical Fact-Checks:
{context}

### Instructions:
1. **Analyze Logic**: Compare the reasoning in the retrieved fact-checks with the logic required to evaluate the current claim.
2. **Identify Precedent**: Find specific historical cases that are most logically similar to the current one.
3. **Check Consistency**: If the retrieved articles were ruled "True" or "False", explain why a similar (or different) ruling would be consistent today.
4. **Editorial Warning**: Highlight if a certain ruling on the current claim would represent a departure from how PolitiFact has historically handled such topics.

Format your output in a professional, concise "Jurisprudence Report" with the following sections:
- **Precedential Summary**: (1-2 sentences on historical handling)
- **Methodological Analysis**: (Comparison of logic/evidence)
- **Consistency Recommendation**: (How to rule while maintaining standards)
- **Shifts/Warnings**: (Any potential departures from legacy standards)
"""

def analyze_jurisprudence_consistency(query: str, sources_data: List[Dict[str, Any]]) -> str:
    """
    Analyzes the consistency of a claim against retrieved fact-checks.
    Uses Claude Opus for high-level reasoning.
    """
    # Flatten results from different sources for the LLM
    context_items = []
    for source in sources_data:
        for res in source.get("results", []) or []:
            if res.get("publisher", "").lower() == "politifact":
                block = (
                    f"Claim: {res.get('claim', 'N/A')}\n"
                    f"Rating: {res.get('rating', 'N/A')}\n"
                    f"URL: {res.get('url', '')}\n"
                )
                context_items.append(block)
    
    if not context_items:
        return "No sufficient PolitiFact precedents found to perform a Jurisprudence analysis."

    context_str = "\n\n---\n\n".join(context_items)
    prompt = JURIST_PROMPT.format(query=query, context=context_str)

    try:
        client = get_anthropic()
        resp = client.messages.create(
            model=FLAGS.ANTHROPIC_OPUS_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )
        return extract_response_text(resp)
    except Exception as e:
        return f"Legacy Jurist encountered an error: {e}"
