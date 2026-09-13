from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
from schemas import RCAResult
import ast_pruner
import embeddings
import rag_retriever
import groq_client

class AgentState(TypedDict):
    incident_id: str
    service: str
    error_msg: str
    stack_trace: str
    needs_rca: bool
    faulty_block: Optional[dict]
    historical_context: Optional[list]
    rca_result: Optional[RCAResult]

def triage_node(state: AgentState):
    # Determine if it needs full RCA. For this demo, always true if it's an ERROR
    return {"needs_rca": True}

def retrieval_node(state: AgentState):
    signature = f"{state['service']} | {state['error_msg']}"
    emb = embeddings.generate_embedding(signature)
    history = rag_retriever.get_similar_incidents(emb)
    block = ast_pruner.prune_code_for_incident(state['service'], state['stack_trace'])
    return {"historical_context": history, "faulty_block": block}

def rca_node(state: AgentState):
    rca = groq_client.generate_rca(
        incident_id=state['incident_id'],
        error_msg=state['error_msg'],
        stack_trace=state['stack_trace'],
        faulty_block=state['faulty_block'],
        historical_context=state['historical_context']
    )
    return {"rca_result": rca}

def build_pipeline():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("Triage", triage_node)
    workflow.add_node("Retrieval", retrieval_node)
    workflow.add_node("RCA", rca_node)
    
    workflow.set_entry_point("Triage")
    
    workflow.add_conditional_edges(
        "Triage",
        lambda x: "Retrieval" if x["needs_rca"] else END
    )
    
    workflow.add_edge("Retrieval", "RCA")
    workflow.add_edge("RCA", END)
    
    return workflow.compile()

pipeline = build_pipeline()

def run_diagnosis(incident_data: dict) -> RCAResult:
    initial_state = {
        "incident_id": incident_data.get("incident_id"),
        "service": incident_data.get("service"),
        "error_msg": incident_data.get("message", ""),
        "stack_trace": incident_data.get("sample_stack_trace", ""),
        "needs_rca": False,
        "faulty_block": None,
        "historical_context": None,
        "rca_result": None
    }
    
    result = pipeline.invoke(initial_state)
    return result["rca_result"]
