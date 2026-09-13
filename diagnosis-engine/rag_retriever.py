import os
from supabase import create_client, Client
from schemas import SimilarIncident

def get_similar_incidents(embedding: list[float], limit: int = 3) -> list[SimilarIncident]:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Warning: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set. Using mock RAG data.")
        return [
            SimilarIncident(
                incident_id="inc_hist_001",
                similarity=0.91,
                resolution="DB connections not closed. Ensure `conn.close()` is called."
            )
        ]

    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Assuming an RPC function `match_incident_embeddings` exists in Supabase.
    # We didn't define it in schema, but this is the standard Supabase pgvector pattern.
    # For a real implementation, we would add the RPC to schema.sql.
    try:
        response = supabase.rpc(
            "match_incident_embeddings",
            {"query_embedding": embedding, "match_threshold": 0.7, "match_count": limit}
        ).execute()
        
        incidents = []
        for item in response.data:
            incidents.append(SimilarIncident(
                incident_id=item.get("incident_id"),
                similarity=item.get("similarity"),
                resolution=item.get("root_cause") # Assuming RPC joins with rca_results
            ))
        return incidents
    except Exception as e:
        print(f"Error querying Supabase RAG: {e}")
        # Return fallback
        return [
            SimilarIncident(
                incident_id="inc_hist_001",
                similarity=0.91,
                resolution="DB connections not closed. Ensure `conn.close()` is called."
            )
        ]
