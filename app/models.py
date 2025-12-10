from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class NodeConfig(BaseModel):
    id: str
    function: str  # The name of the function in the registry

class Condition(BaseModel):
    # A simple condition representation
    # e.g., key="status", operator="==", value="completed"
    key: str
    operator: str
    value: Any

class EdgeConfig(BaseModel):
    source: str
    target: str
    condition: Optional[Condition] = None

class GraphCreateRequest(BaseModel):
    nodes: List[NodeConfig]
    edges: List[EdgeConfig]
    start_node: str

class GraphRunRequest(BaseModel):
    graph_id: str
    initial_state: Dict[str, Any]
    
class GraphStateResponse(BaseModel):
    run_id: str
    status: str # "running", "completed", "failed"
    state: Dict[str, Any]
    logs: List[str]

