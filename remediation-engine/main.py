import os
import json
import time
import datetime
import redis
from docker_actions import rollback_container
from github_pr import create_pull_request

def main():
    redis_url = os.getenv("UPSTASH_REDIS_URL", "redis://redis:6379/0")
    r = redis.from_url(redis_url, decode_responses=True)
    
    pubsub = r.pubsub()
    pubsub.subscribe("approvals")
    
    print("Remediation Engine listening for approvals...")
    
    for message in pubsub.listen():
        if message["type"] == "message":
            try:
                data = json.loads(message["data"])
                incident_id = data.get("incident_id")
                decision = data.get("decision")
                action = data.get("action")
                service = data.get("service", "payment-service") # dynamically parsed from payload
                
                print(f"Received approval event for {incident_id}: {decision}")
                
                if decision == "APPROVED":
                    # Dynamically construct container name
                    service_name = f"mock-services-{service}-1"
                    
                    success = rollback_container(service_name, "v2.0")
                    pr_url = create_pull_request(incident_id, "mock diff")
                    
                    result = {
                        "incident_id": incident_id,
                        "action_taken": action,
                        "success": success,
                        "details": f"Container {service_name} restarted/rolled back, health check {'passed' if success else 'failed'}",
                        "github_pr_url": pr_url,
                        "resolved_at": datetime.datetime.utcnow().isoformat() + "Z",
                        "final_status": "HEALTHY" if success else "REMEDIATION_FAILED"
                    }
                    
                    print(f"Publishing remediation status for {incident_id}")
                    r.publish("remediation-status", json.dumps(result))
                else:
                    print(f"Incident {incident_id} rejected. No action taken.")
                    
            except Exception as e:
                print(f"Error processing approval: {e}")

if __name__ == "__main__":
    main()
