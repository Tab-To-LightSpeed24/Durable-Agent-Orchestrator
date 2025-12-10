import time
import uuid
import asyncio
from typing import Dict, Any, List, Optional
from .models import GraphCreateRequest, NodeConfig, EdgeConfig, Condition
from .registry import node_registry

class WorkflowExecutionError(Exception):
    pass

class Graph:
    def __init__(self, definition: GraphCreateRequest):
        self.id = str(uuid.uuid4())
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
        # Find all edges starting from current_node_id
        candidates = [e for e in self.edges if e.source == current_node_id]
        
        for edge in candidates:
            # Check condition
            if edge.condition:
                if self.evaluate_condition(edge.condition, state):
                    return edge.target
            else:
                # Unconditional edge (default path). 
                # If we want to support order, we should probably check conditional ones first?
                # For simplicity, we stick to the list order. 
                # If the user defines an unconditional edge before a conditional one, it might block it.
                # Usually unconditional is the 'else', so it should be last.
                # Detailed logic: if multiple edges match, take the first one?
                return edge.target
        return None

    def evaluate_condition(self, condition: Condition, state: Dict[str, Any]) -> bool:
        val = state.get(condition.key)
        target = condition.value
        op = condition.operator

        if op == "==":
            return val == target
        elif op == "!=":
            return val != target
        elif op == ">":
            return val > target
        elif op == "<":
            return val < target
        elif op == ">=":
            return val >= target
        elif op == "<=":
            return val <= target
        elif op == "in":
            return val in target
        return False

class WorkflowRun:
    def __init__(self, run_id: str, graph: Graph, initial_state: Dict[str, Any]):
        self.run_id = run_id
        self.graph = graph
        self.state = initial_state
        self.status = "created"
        self.logs = []
        self.current_node_id = graph.start_node

    def log(self, message: str):
        self.logs.append(message)

# Global storage (simulated DB)
graphs_db: Dict[str, Graph] = {}
runs_db: Dict[str, WorkflowRun] = {}

class Engine:
    def create_graph(self, definition: GraphCreateRequest) -> str:
        graph = Graph(definition)
        graphs_db[graph.id] = graph
        return graph.id

    async def run_graph(self, graph_id: str, initial_state: Dict[str, Any]) -> WorkflowRun:
        graph = graphs_db.get(graph_id)
        if not graph:
            raise ValueError("Graph not found")

        run_id = str(uuid.uuid4())
        run = WorkflowRun(run_id, graph, initial_state)
        runs_db[run_id] = run

        run.status = "running"
        run.log(f"Starting run {run_id} with graph {graph_id}")

        try:
            # Limit steps to prevent infinite loops in this demo
            max_steps = 50
            steps = 0

            while run.current_node_id and steps < max_steps:
                steps += 1
                node_id = run.current_node_id
                run.log(f"Executing node: {node_id}")
                
                # Get function
                func = graph.get_node_func(node_id)
                
                # Execute (sync for now, could be async wrapper)
                # We update state in place or replace it
                try:
                    new_state = func(run.state)
                    if new_state is not None:
                        run.state = new_state
                except Exception as e:
                    run.log(f"Error executing node {node_id}: {str(e)}")
                    run.status = "failed"
                    raise e
                
                # Determining next node
                next_node = graph.get_next_node(node_id, run.state)
                
                if next_node:
                    run.log(f"Transition: {node_id} -> {next_node}")
                    run.current_node_id = next_node
                else:
                    run.log(f"No transitions found from {node_id}. Ending.")
                    run.current_node_id = None
            
            if steps >= max_steps:
                run.log("Max steps reached. Terminating.")
            
            run.status = "completed"
            
        except Exception as e:
            run.status = "failed"
            run.log(f"Run failed: {e}")
        
        return run

    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        return runs_db.get(run_id)

# Singleton engine
engine = Engine()
