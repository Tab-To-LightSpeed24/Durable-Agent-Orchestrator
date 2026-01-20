# Durable Agent Orchestrator

A failsafe, database-backed workflow engine inspired by Temporal and LangGraph. It enables **durable execution**, **human-in-the-loop (HITL)** approvals, and **crash recovery** for complex agentic workflows.

## Features
- **Durable Execution**: Every step is checkpointed to PostgreSQL/SQLite. If the server crashes, the workflow can resume exactly where it left off.
- **Human-in-the-Loop (HITL)**: Native support for "Wait for Approval" steps that suspend execution and release resources until an external API signal is received.
- **Dynamic Graph Logic**: Define workflows as JSON graphs with branching conditions (loops, if/else) evaluated at runtime.
- **State Persistence**: The full context (variables, history) is preserved across server restarts.

## Setup & Running

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Requires `sqlalchemy` and `psycopg2-binary` (or uses built-in sqlite for dev).*

2. **Start the Server**:
   ```bash
   python run_server.py
   ```
   The API will point to `http://127.0.0.1:8000`.

## API Usage

### 1. Check Available Tools
`GET /tools`

### 2. Create a Graph
`POST /graph/create`
**Body**:
```json
{
  "nodes": [
    {"id": "step1", "function": "profile_data"},
    {"id": "step2", "function": "wait_for_approval"},
    {"id": "step3", "function": "finish_pipeline"}
  ],
  "edges": [
    {"source": "step1", "target": "step2"},
    {"source": "step2", "target": "step3"}
  ],
  "start_node": "step1"
}
```

### 3. Run a Graph
`POST /graph/run`
**Body**:
```json
{
  "graph_id": "<ID_FROM_CREATE>",
  "initial_state": {"project_name": "Demo"}
}
```

### 4. Resume a Suspended Run (HITL)
If a workflow hits a `wait_for_approval` node, it enters `awaiting_approval` status. To approve and continue:
`POST /graph/resume/{run_id}`

### 5. Check State
`GET /graph/state/{run_id}`

## Demos
We have provided scripts to demonstrate the capabilities:

1. **Data Quality Pipeline (Loops & Logic)**:
   ```bash
   python data_quality_demo.py
   ```
2. **Persistence & HITL (Pause/Resume)**:
   ```bash
   python test_persistence.py
   ```

## Architecture
- **Engine**: Python 3.10+ async execution loop.
- **Database**: SQLAlchemy ORM (PostgreSQL/SQLite).
- **API**: FastAPI.

## Docs
See `TECHNICAL_DOCS.md` for a deep dive into the architecture and database schema.
