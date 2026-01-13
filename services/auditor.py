from typing import List, Dict, Any
from services.clients import get_anthropic
from config import FLAGS
from utils.parsing import extract_response_text

AUDITOR_PROMPT = """
You are the **Adversarial Auditor**, an internal critic for a fact-checking system.
Your goal is to find weaknesses, contradictions, and potential biases in the retrieved search results before they are used to write a final report.

### Search Results for Audit:
{context}

### Instructions:
Analyze the results and provide a concise "Internal Memo" (for the lead analyst only) that covers:
1. **Contradictions**: Do different sources disagree?
2. **Age of Data**: Are any key findings based on old data (more than 2-3 years old)?
3. **Circular Reasoning**: Do multiple sources just quote the same original source?
4. **Context Gaps**: What is MISSING that would be needed to make a definitive ruling?

Format your response as a series of 3-5 bullet points. Be skeptical, blunt, and direct.
If the results are high-quality and consistent, say "No significant red flags detected."
"""

def audit_search_results(sources_data: List[Dict[str, Any]]) -> str:
    """
    Analyzes search results for red flags/weaknesses.
    Uses Claude Sonnet for speed and objective analysis.
    """
    context_items = []
    for source in sources_data:
        name = source.get("source_name", "Unknown")
        for res in source.get("results", []) or []:
            block = (
                f"Source: {name} / {res.get('publisher', 'Unknown')}\n"
                f"Claim: {res.get('claim', 'N/A')}\n"
                f"Rating: {res.get('rating', 'N/A')}\n"
                f"Explanation: {res.get('explanation', '')[:200]}...\n"
            )
            context_items.append(block)
    
    if not context_items:
        return "Internal Memo: No external search results retrieved to audit."

    context_str = "\n---\n".join(context_items)
    prompt = AUDITOR_PROMPT.format(context=context_str)

    try:
        client = get_anthropic()
        # Use Sonnet for internal utility tasks
        resp = client.messages.create(
            model=FLAGS.ANTHROPIC_SONNET_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        return extract_response_text(resp)
    except Exception as e:
        return f"Internal Memo: Auditor encountered an error: {e}"
