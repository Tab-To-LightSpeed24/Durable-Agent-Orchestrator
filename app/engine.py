import time
import uuid
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from .models import GraphCreateRequest, NodeConfig, EdgeConfig, Condition, GraphStateResponse
from .registry import node_registry
from .persistence_models import GraphModel, WorkflowRunModel
from .database import SessionLocal

class WorkflowExecutionError(Exception):
    pass

class Graph:
    def __init__(self, definition: GraphCreateRequest, graph_id: str):
        self.id = graph_id
        self.definition = definition
        self.nodes = {n.id: n for n in definition.nodes}
        self.edges = definition.edges
        self.start_node = definition.start_node

    def get_node_func(self, node_id: str):
        node_def = self.nodes.get(node_id)
        if not node_def:
            raise WorkflowExecutionError(f"Node {node_id} not found in graph.")
        func = node_registry.get(node_def.function)
        if not func:
            raise WorkflowExecutionError(f"Function {node_def.function} not found in registry.")
        return func

    def get_next_node(self, current_node_id: str, state: Dict[str, Any]) -> Optional[str]:
        candidates = [e for e in self.edges if e.source == current_node_id]
        for edge in candidates:
            if edge.condition:
                if self.evaluate_condition(edge.condition, state):
                    return edge.target
            else:
                return edge.target
        return None

    def evaluate_condition(self, condition: Condition, state: Dict[str, Any]) -> bool:
        val = state.get(condition.key)
        target = condition.value
        op = condition.operator

        if op == "==": return val == target
        elif op == "!=": return val != target
        elif op == ">": return val > target
        elif op == "<": return val < target
        elif op == ">=": return val >= target
        elif op == "<=": return val <= target
        elif op == "in": return val in target
        return False

class Engine:
    def _load_graph(self, db: Session, graph_id: str) -> Graph:
        graph_model = db.query(GraphModel).filter(GraphModel.id == graph_id).first()
        if not graph_model:
            raise ValueError(f"Graph {graph_id} not found")
        # Reconstruct Graph definition from JSON
        definition = GraphCreateRequest(**graph_model.definition_json)
        return Graph(definition, graph_id)

    def create_graph(self, definition: GraphCreateRequest) -> str:
        db = SessionLocal()
        try:
            graph_id = str(uuid.uuid4())
            graph_model = GraphModel(id=graph_id, definition_json=definition.dict())
            db.add(graph_model)
            db.commit()
            return graph_id
        finally:
            db.close()

    async def run_graph(self, graph_id: str, initial_state: Dict[str, Any]) -> GraphStateResponse:
        db = SessionLocal()
        try:
            # 1. Load Graph
            try:
                graph = self._load_graph(db, graph_id)
            except ValueError:
                raise ValueError("Graph not found")

            # 2. Create Run Record
            run_id = str(uuid.uuid4())
            run_model = WorkflowRunModel(
                run_id=run_id,
                graph_id=graph_id,
                status="running",
                current_node_id=graph.start_node,
                state=initial_state,
                logs=[f"Starting run {run_id} with graph {graph_id}"]
            )
            db.add(run_model)
            db.commit()

            # 3. Execute Loop
            return self._execute_loop(db, run_model, graph)
        finally:
            db.close()

    async def resume_run(self, run_id: str) -> GraphStateResponse:
        db = SessionLocal()
        try:
            run_model = db.query(WorkflowRunModel).filter(WorkflowRunModel.run_id == run_id).first()
            if not run_model:
                raise ValueError("Run not found")
            
            graph = self._load_graph(db, run_model.graph_id)

            if run_model.status == "completed":
                return self._to_response(run_model)
            
            if run_model.status == "awaiting_approval":
                 # Manually transition back to running AND advance node
                 # We assume the user 'Action' (calling resume) satisfies the wait.
                 
                 # Calculate next node
                 next_node = graph.get_next_node(run_model.current_node_id, run_model.state)
                 
                 # Advance pointer
                 run_model.current_node_id = next_node
                 run_model.status = "running"
                 
                 self._log(run_model, f"Resuming from AWAITING_APPROVAL. Transitioning to {next_node}")
                 db.commit()

            return self._execute_loop(db, run_model, graph)
        finally:
            db.close()

    def _execute_loop(self, db: Session, run: WorkflowRunModel, graph: Graph) -> GraphStateResponse:
        try:
            max_steps = 50
            steps = 0
            
            while run.current_node_id and steps < max_steps:
                # Check for explicit halt if status changed externally (though we have lock here usually)
                if run.status != "running":
                    break

                steps += 1
                node_id = run.current_node_id
                self._log(run, f"Executing node: {node_id}")
                
                # Get function
                func = graph.get_node_func(node_id)
                
                # Execute
                try:
                    # NOTE: Passing a copy of state to avoid reference issues, 
                    # but returning dict updates it.
                    current_state = dict(run.state)
                    new_state = func(current_state)
                    if new_state is not None:
                        run.state = new_state
                except Exception as e:
                    self._log(run, f"Error executing node {node_id}: {str(e)}")
                    run.status = "failed"
                    db.commit()
                    raise e
                
                # CHECKPOINT 1: State Updated
                db.commit()

                # Check for HITL Suspension
                if run.state.get("__suspend__"):
                    self._log(run, "Suspending for Approval (HITL).")
                    run.status = "awaiting_approval"
                    # Remove the flag so it doesn't trigger again immediately on resume
                    state_copy = dict(run.state)
                    state_copy.pop("__suspend__", None)
                    run.state = state_copy
                    db.commit()
                    return self._to_response(run)

                # Determine Next Node
                next_node = graph.get_next_node(node_id, run.state)
                
                if next_node:
                    self._log(run, f"Transition: {node_id} -> {next_node}")
                    run.current_node_id = next_node
                else:
                    self._log(run, f"No transitions found from {node_id}. Ending.")
                    run.current_node_id = None
                
                # CHECKPOINT 2: Node Transition Commited
                db.commit()

            if steps >= max_steps:
                self._log(run, "Max steps reached. Terminating.")
            
            if not run.current_node_id:
                run.status = "completed"
                db.commit()
            
            return self._to_response(run)

        except Exception as e:
            run.status = "failed"
            self._log(run, f"Run failed: {e}")
            db.commit()
            raise e

    def _log(self, run: WorkflowRunModel, message: str):
        # SQLAlchemy requires reassignment for JSON mutation detection sometimes, 
        # or MutableList. Safest is to reassign.
        current_logs = list(run.logs)
        current_logs.append(message)
        run.logs = current_logs

    def _to_response(self, run: WorkflowRunModel) -> GraphStateResponse:
        return GraphStateResponse(
            run_id=run.run_id,
            status=run.status,
            state=run.state,
            logs=run.logs
        )

    def get_run(self, run_id: str) -> Optional[GraphStateResponse]:
        db = SessionLocal()
        try:
            run = db.query(WorkflowRunModel).filter(WorkflowRunModel.run_id == run_id).first()
            if run:
                return self._to_response(run)
            return None
        finally:
            db.close()

engine = Engine()
