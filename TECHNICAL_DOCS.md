# Technical Documentation: Durable Agent Workflow Engine

## 1. Executive Summary

The Durable Agent Workflow Engine is a high-availability orchestration platform designed to execute complex, stateful workflows with fault tolerance and failsafe recovery. Inspired by LangGraph and modern workflow systems like Temporal, this project implements a specialized graph execution engine that decouples workflow selection (graph definition) from implementation (code execution). 

Key capabilities include:
- **Durable Execution**: Persistence of state after every atomic operation, ensuring zero data loss during infrastructure failures.
- **Human-in-the-Loop (HITL)**: Native support for asynchronous approval steps that suspend execution and release compute resources.
- **Dynamic Branching**: Runtime evaluation of conditional logic to alter execution paths based on intermediate data states.
- **Failsafe Recovery**: A robust mechanism to resume interrupted workflows from their exact last known state.

---

## 2. System Architecture

The system follows a standard 3-tier architecture:

### 2.1. API Layer (FastAPI)
- **Role**: Entry point for client interactions.
- **Responsibilities**: 
  - Validates incoming graph definitions and execution requests.
  - Exposes endpoints for creating graphs (`/graph/create`), running workflows (`/graph/run`), and managing lifecycle (`/graph/resume`, `/graph/state`).
  - Handles asynchronous request processing.

### 2.2. Core Engine (The "Brain")
- **Role**: State machine and execution loop.
- **Responsibilities**:
  - **Graph Traversal**: Uses a directed graph model where Nodes represent functions and Edges represent transitions.
  - **State Management**: Maintains a JSON-serializable context dictionary passed between nodes.
  - **Logic Evaluation**: Dynamically evaluates conditional edges (operators: `>`, `<`, `==`, `in`) to determine the next step.
  - **Registry Lookup**: Resolves string identifiers (e.g., "profile_data") to executable Python callables at runtime.

### 2.3. Persistence Layer (PostgreSQL & SQLAlchemy)
- **Role**: Source of truth for all system state.
- **Schema**:
  - `graphs`: Stores the immutable definition of workflow structures (nodes/edges).
  - `workflow_runs`: Stores the mutable execution state (current cursor, variables, logs).
- **Strategy**: **Checkpoint-on-Transition**. Commits to the database occur atomically after every function execution and before every state transition.

---

## 3. Key Technical Workflows

### 3.1. Workflow Creation
1.  **Definition**: Client submits a JSON definition specifying Nodes (steps) and Edges (logic).
2.  **Validation**: The Engine ensures all referenced functions exist in the internal `Registry`.
3.  **Storage**: The definition is serialized and stored in the `graphs` table with a unique UUID.

### 3.2. Durable Execution Loop
The engine does not run workflows as a single linear script. Instead, it operates as a persistent loop:
1.  **Load**: Fetches the run state from the DB.
2.  **Execute**: Retrieves the function for the `current_node_id`, executes it, and updates the state.
3.  **Checkpoint (Commit 1)**: Saves the *result* of the execution to the DB.
4.  **Decide**: Evaluates edge conditions to find the `target` node.
5.  **Transition**: Updates the `current_node_id` pointer.
6.  **Checkpoint (Commit 2)**: Saves the *position* to the DB.
7.  **Repeat**: The loop continues until no outgoing edges remain.

### 3.3. Human-in-the-Loop & Suspension
1.  **Trigger**: A specific node (e.g., `wait_for_approval`) sets a `__suspend__` flag in the state.
2.  **Detection**: The Engine loop detects this flag after execution.
3.  **Halt**: The system sets the run status to `awaiting_approval`, commits the state, and *terminates the Python process*. No background threads remain running.
4.  **Resume**: An API call to `/graph/resume/{id}` triggers the engine to reload the state, manually advance the pointer past the wait node, and restart the execution loop.

---

## 4. Data Models

### 4.1. Graph Definition
```json
{
  "nodes": [{"id": "step1", "function": "do_work"}],
  "edges": [{"source": "step1", "target": "step2", "condition": {...}}]
}
```

### 4.2. Database Schema (SQLAlchemy)
- **GraphModel**: `id` (PK), `definition_json` (JSON)
- **WorkflowRunModel**: 
  - `run_id` (PK)
  - `graph_id` (FK)
  - `status` (Enum: running, completed, applied, failed)
  - `current_node_id` (Cursor)
  - `state` (The entire memory context)

---

## 5. Deployment & Scalability

- **Statelessness**: The API server is stateless. Any request can be handled by any replica, as all state is offloaded to the Persistence Layer.
- **Concurrency**: The engine uses Python's `asyncio` for handling API throughput, while protecting data integrity with database transactions.
- **Environment**: 
  - **Runtime**: Python 3.10+
  - **Database**: PostgreSQL (Production) / SQLite (Dev)
  - **Dependencies**: FastAPI, SQLAlchemy, Uvicorn, Pydantic.

---

## 6. Future Roadmap

- **Distributed Workers**: Moving node execution to a task queue (e.g., Celery/RabbitMQ) for massive scale.
- **Versioning**: Implementing graph version control to handle updates to live workflows.
- **UI Dashboard**: A visual interface for monitoring workflow progress and manually approving HITL steps.
