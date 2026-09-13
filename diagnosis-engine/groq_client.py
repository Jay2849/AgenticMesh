import os
import json
from groq import Groq
from schemas import RCAResult, FaultyCodeBlock, SuggestedFix

def generate_rca(incident_id: str, error_msg: str, stack_trace: str, faulty_block: dict, historical_context: list) -> RCAResult:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Warning: GROQ_API_KEY not set. Returning mock RCA.")
        return mock_rca(incident_id, faulty_block, historical_context)

    client = Groq(api_key=api_key)
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    prompt = f"""
    You are an AI Incident Triage Engine. Analyze the following incident and output ONLY valid JSON matching the exact schema.
    
    Incident ID: {incident_id}
    Error: {error_msg}
    Stack Trace:
    {stack_trace}
    
    Faulty Code Block:
    {json.dumps(faulty_block, indent=2)}
    
    Historical Context (Similar Incidents):
    {json.dumps([h.model_dump() for h in historical_context], indent=2)}
    
    Provide the root cause, confidence score, and a suggested fix with a unified diff and rollback target tag.
    The response must be parsable JSON.
    """

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            response_format={"type": "json_object"}
        )
        result_json = response.choices[0].message.content
        data = json.loads(result_json)
        
        # Ensure we have required nested structures
        if "faulty_code_block" not in data:
            data["faulty_code_block"] = faulty_block
        if "similar_historical_incidents" not in data:
            data["similar_historical_incidents"] = [h.model_dump() for h in historical_context]
            
        return RCAResult(**data)
    except Exception as e:
        print(f"Groq API Error: {e}. Falling back to mock RCA.")
        return mock_rca(incident_id, faulty_block, historical_context)

def mock_rca(incident_id: str, faulty_block: dict, historical_context: list) -> RCAResult:
    return RCAResult(
        incident_id=incident_id,
        root_cause="Database connection pool exhausted due to unclosed connections in process_payment()",
        faulty_code_block=FaultyCodeBlock(**faulty_block) if faulty_block and "file" in faulty_block else FaultyCodeBlock(
            file="payment_service.py",
            function="process_payment",
            line_start=142,
            line_end=168,
            code_snippet="connections = []\nfor i in range(21):\n  connections.append(f'conn_{i}')"
        ),
        confidence_score=0.87,
        similar_historical_incidents=historical_context,
        suggested_fix=SuggestedFix(
            type="code_patch",
            diff="--- payment_service.py\n+++ payment_service.py\n@@ -142,3 +142,4 @@\n         connections.append(f'conn_{i}')\n+    for c in connections: c.close()\n",
            rollback_target_tag="v2.0"
        ),
        requires_human_approval=True,
        status="AWAITING_APPROVAL"
    )
