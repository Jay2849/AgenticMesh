import os
import json
import asyncio
import redis.asyncio as redis
import asyncpg
from langgraph_pipeline import run_diagnosis

async def save_to_db(incident_data, rca_dict):
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@db:5432/agenticmesh")
    try:
        conn = await asyncpg.connect(db_url)
        
        row = await conn.fetchrow('SELECT id FROM incidents WHERE incident_id = $1', incident_data.get('incident_id'))
        incident_uuid = None
        if row:
            incident_uuid = row['id']
            await conn.execute("UPDATE incidents SET status = 'DIAGNOSING' WHERE id = $1", incident_uuid)
        else:
            incident_uuid = await conn.fetchval(
                "INSERT INTO incidents (incident_id, fingerprint_hash, status) VALUES ($1, $2, 'DIAGNOSING') RETURNING id",
                incident_data.get('incident_id'), incident_data.get('fingerprint', 'unknown_hash')
            )
            
        await conn.execute(
            """INSERT INTO rca_results 
               (incident_id, root_cause, faulty_file, faulty_function, code_snippet, confidence_score, suggested_fix_diff, rollback_target_tag)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
               incident_uuid,
               rca_dict.get('root_cause', ''),
               rca_dict.get('faulty_file', ''),
               rca_dict.get('faulty_function', ''),
               rca_dict.get('code_snippet', ''),
               rca_dict.get('confidence_score', 0.0),
               rca_dict.get('suggested_fix_diff', ''),
               rca_dict.get('rollback_target_tag', '')
        )
        await conn.execute("UPDATE incidents SET status = 'AWAITING_APPROVAL' WHERE id = $1", incident_uuid)
        await conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

async def main_loop():
    redis_url = os.getenv("UPSTASH_REDIS_URL", "redis://redis:6379/0")
    r = redis.from_url(redis_url, decode_responses=True)
    
    stream_name = "incidents"
    group_name = "diagnosis_group"
    
    try:
        await r.xgroup_create(stream_name, group_name, id="0", mkstream=True)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            print(f"Error creating group: {e}")
            
    print("Diagnosis Engine listening for incidents (Async Mode)...")
    
    while True:
        try:
            messages = await r.xreadgroup(group_name, "consumer1", {stream_name: ">"}, count=1, block=5000)
            if not messages:
                continue
                
            for stream, msgs in messages:
                for msg_id, msg_data in msgs:
                    payload = msg_data.get("payload")
                    if payload:
                        incident_data = json.loads(payload)
                        print(f"Diagnosing incident: {incident_data.get('incident_id')}")
                        
                        rca = await asyncio.to_thread(run_diagnosis, incident_data)
                        rca_dict = rca.model_dump()
                        
                        print(f"RCA Complete for {rca.incident_id}. Publishing to DB and Redis...")
                        
                        await save_to_db(incident_data, rca_dict)
                        await r.publish("rca-results", json.dumps(rca_dict))
                        await r.xack(stream_name, group_name, msg_id)
                        
        except Exception as e:
            print(f"Error in diagnosis loop: {e}")
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main_loop())
