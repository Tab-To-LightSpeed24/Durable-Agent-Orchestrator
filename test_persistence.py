import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_hitl_and_resume():
    print("\n--- Testing Durable Execution, HITL, and Recovery ---")
    
    # 1. Create a Graph with a Pause
    # Flow: profile -> wait_for_approval -> finish
    graph_def = {
        "nodes": [
            {"id": "node_A", "function": "profile_data"},
            {"id": "node_B", "function": "wait_for_approval"},
            {"id": "node_C", "function": "finish_pipeline"} 
        ],
        "edges": [
            {"source": "node_A", "target": "node_B"},
            {"source": "node_B", "target": "node_C"}
        ],
        "start_node": "node_A"
    }

    try:
        print("1. Creating Graph...")
        resp = requests.post(f"{BASE_URL}/graph/create", json=graph_def)
        resp.raise_for_status()
        graph_id = resp.json()["graph_id"]
        print(f"   Graph Created: {graph_id}")

        # 2. Run Graph - Should Stop at node_B
        print("\n2. Starting Run (expecting suspension)...")
        run_req = {
            "graph_id": graph_id,
            "initial_state": {"test_run": True} 
        }
        resp = requests.post(f"{BASE_URL}/graph/run", json=run_req)
        resp.raise_for_status()
        result = resp.json()
        
        run_id = result["run_id"]
        status = result["status"]
        print(f"   Run ID: {run_id}")
        print(f"   Status: {status}")
        
        if status != "awaiting_approval":
            print(f"FAILURE: Expected 'awaiting_approval', got '{status}'")
            return
        
        print("   SUCCESS: Run suspended as expected.")

        # 3. Resume Run
        print("\n3. Resuming Run...")
        # Small sleep just to be realistic
        time.sleep(1)
        
        resp = requests.post(f"{BASE_URL}/graph/resume/{run_id}")
        resp.raise_for_status()
        result = resp.json()
        
        final_status = result["status"]
        print(f"   Resume Status: {final_status}")
        
        if final_status != "completed":
             print(f"FAILURE: Expected 'completed' after resume, got '{final_status}'")
             return

        print("   SUCCESS: Run resumed and completed.")
        print("   Final Logs:")
        print(result["logs"])

    except Exception as e:
        print(f"ERROR: {e}")
        # If connection refused, maybe server needs restart
        if "Connection refused" in str(e):
            print("Server might be down. Please restart run_server.py")

if __name__ == "__main__":
    # Wait a moment for server to likely be up if it was reloading
    time.sleep(2)
    test_hitl_and_resume()
