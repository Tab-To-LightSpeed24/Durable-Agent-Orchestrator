# Agent Workflow Engine

A minimal agent workflow engine inspired by LangGraph. It allows defining graphs of nodes (Python functions) and edges (transitions with conditions), maintaining a shared state.

## Features
- **Nodes**: Python functions reading/modifying shared state.
- **Edges**: Directed connections with optional conditional logic.
- **State**: A flexible dictionary passed between nodes.
- **Branching**: Conditional transitions based on state values.
- **Looping**: Cycles in the graph are supported (capped at 50 steps for safety).
- **API**: FastAPI endpoints to create and run graphs.

## Setup & Running

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   ```bash
   python -m uvicorn app.main:app --reload
   # OR
   python run_server.py
   ```
   The API will point to `http://127.0.0.1:8000`.

## API Usage

### 1. Check Available Tools
`GET /tools`

### 2. Create a Graph (Data Quality Example)
`POST /graph/create`
**Body**:
```json
{
  "nodes": [
    {"id": "profile", "function": "profile_data"},
    {"id": "check", "function": "identify_anomalies"},
    {"id": "fix", "function": "apply_rules"},
    {"id": "end", "function": "finish_pipeline"}
  ],
  "edges": [
    {"source": "profile", "target": "check"},
    {"source": "check", "target": "fix", "condition": {"key": "anomaly_count", "operator": ">", "value": 5}},
    {"source": "check", "target": "end", "condition": {"key": "anomaly_count", "operator": "<=", "value": 5}},
    {"source": "fix", "target": "check"}
  ],
  "start_node": "profile"
}
```

### 3. Run a Graph
`POST /graph/run`
**Body**:
```json
{
  "graph_id": "<ID_FROM_CREATE>",
  "initial_state": {"anomaly_count": 50}
}
```

### 4. Check State (Optional, for ongoing/past runs)
`GET /graph/state/{run_id}`

## Quick Start Demo
We have provided a script to demonstrate the API usage efficiently.
1. Start the server: 
   ```bash
   python run_server.py
   ```
2. In another terminal, run: 
   ```bash
   python data_quality_demo.py
   ```

## Future Improvements
- **Persistent Storage**: Use SQLite/Postgres for generic persistence of graphs and run history.
- **Dynamic Tool Loading**: Allow uploading Python scripts safely.
- **Async Nodes**: Fully async node execution.
- **Visualizer**: distinct UI to view the graph topology.
