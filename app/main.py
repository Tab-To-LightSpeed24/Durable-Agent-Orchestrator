from fastapi import FastAPI, HTTPException, BackgroundTasks
from typing import Dict, Any
from .models import GraphCreateRequest, GraphRunRequest, GraphStateResponse
from .engine import engine, runs_db
from .registry import node_registry

app = FastAPI(title="Agent Workflow Engine")

@app.get("/")
def home():
    return {"message": "Welcome to the Agent Workflow Engine"}

@app.get("/tools")
def list_tools():
    return {"tools": node_registry.list_tools()}

@app.post("/graph/create")
def create_graph(request: GraphCreateRequest):
    try:
        graph_id = engine.create_graph(request)
        return {"graph_id": graph_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/graph/run")
async def run_graph(request: GraphRunRequest):
    # This runs synchronously in the response (awaiting the async function)
    # matching the requirement: "Output: final state + a simple execution log"
    try:
        run = await engine.run_graph(request.graph_id, request.initial_state)
        return {
            "run_id": run.run_id,
            "status": run.status,
            "final_state": run.state,
            "logs": run.logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph/state/{run_id}")
def get_run_state(run_id: str):
    run = engine.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return {
        "run_id": run.run_id,
        "status": run.status,
        "state": run.state,
        "logs": run.logs
    }
