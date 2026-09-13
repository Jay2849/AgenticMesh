import os
import json
import time
import redis
from langgraph_pipeline import run_diagnosis

def main():
    redis_url = os.getenv("UPSTASH_REDIS_URL", "redis://redis:6379/0")
    r = redis.from_url(redis_url, decode_responses=True)
    
    stream_name = "incidents"
    group_name = "diagnosis_group"
    
    # Create consumer group if it doesn't exist
    try:
        r.xgroup_create(stream_name, group_name, id="0", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            print(f"Error creating group: {e}")
            
    print("Diagnosis Engine listening for incidents...")
    
    while True:
        try:
            # Read new messages for this consumer
            messages = r.xreadgroup(group_name, "consumer1", {stream_name: ">"}, count=1, block=5000)
            if not messages:
                continue
                
            for stream, msgs in messages:
                for msg_id, msg_data in msgs:
                    payload = msg_data.get("payload")
                    if payload:
                        incident_data = json.loads(payload)
                        print(f"Diagnosing incident: {incident_data.get('incident_id')}")
                        
                        rca = run_diagnosis(incident_data)
                        
                        rca_dict = rca.model_dump()
                        
                        # Write to RCA Postgres (mocked here, should use Supabase client ideally)
                        print(f"RCA Complete for {rca.incident_id}. Publishing to rca-results...")
                        
                        # Publish to Pub/Sub
                        r.publish("rca-results", json.dumps(rca_dict))
                        
                        # Ack the message
                        r.xack(stream_name, group_name, msg_id)
                        
        except Exception as e:
            print(f"Error in diagnosis loop: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
