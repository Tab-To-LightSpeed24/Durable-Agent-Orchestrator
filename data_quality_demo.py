import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("1. Creating Data Quality Pipeline Graph...")
    # Pipeline: 
    # Profile -> Identify -> (if > 5 anomalies) -> Generate -> Apply -> Identify 
    #                     -> (else) -> End
    
    graph_def = {
        "nodes": [
            {"id": "profile", "function": "profile_data"},
            {"id": "identify", "function": "identify_anomalies"},
            {"id": "gen_rules", "function": "generate_rules"},
            {"id": "apply", "function": "apply_rules"},
            {"id": "end_step", "function": "finish_pipeline"} 
        ],
        "edges": [
            # 1. Profile -> Identify
            {"source": "profile", "target": "identify"},
            
            # 2. Identify -> Generate Rules (IF count > 5)
            {"source": "identify", "target": "gen_rules", "condition": {"key": "anomaly_count", "operator": ">", "value": 5}},
            
            # 3. Identify -> End (Else / If count <= 5)
            # Since my engine evaluates edges in order, putting this AFTER the conditional one acts as "Else"
            # OR we can make it explicit for safety. Let's make it implicit/fallback for now to test that behavior 
            # or explicit if we want to be sure. Explicit is better for demos.
            {"source": "identify", "target": "end_step", "condition": {"key": "anomaly_count", "operator": "<=", "value": 5}},
            
            # 4. Generate -> Apply
            {"source": "gen_rules", "target": "apply"},
            
            # 5. Apply -> Identify (Loop back to re-check)
            {"source": "apply", "target": "identify"}
        ],
        "start_node": "profile"
    }

    try:
        resp = requests.post(f"{BASE_URL}/graph/create", json=graph_def)
        resp.raise_for_status()
        data = resp.json()
        graph_id = data["graph_id"]
        print(f"   Graph ID: {graph_id}")

        print("\n2. Running Data Quality Pipeline...")
        # Start with a high anomaly count to trigger the loop
        run_req = {
            "graph_id": graph_id,
            "initial_state": {"anomaly_count": 50} 
        }
        resp = requests.post(f"{BASE_URL}/graph/run", json=run_req)
        resp.raise_for_status()
        result = resp.json()
        
        print("   Run Completed!")
        print(f"   Run ID: {result['run_id']}")
        print(f"   Final State: {result['final_state']}")
        print("   Logs:")
        for log in result['logs']:
            print(f"     {log}")
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Make sure uvicorn is running!")

if __name__ == "__main__":
    main()
