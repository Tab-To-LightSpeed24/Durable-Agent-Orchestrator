from typing import Callable, Dict, Any

# Type for our node functions: takes state, returns modified state (or None to imply in-place mod)
NodeFunction = Callable[[Dict[str, Any]], Dict[str, Any]]

class Registry:
    def __init__(self):
        self._functions: Dict[str, NodeFunction] = {}

    def register(self, name: str, func: NodeFunction):
        self._functions[name] = func

    def get(self, name: str) -> NodeFunction:
        return self._functions.get(name)

    def list_tools(self):
        return list(self._functions.keys())

# Global registry instance
node_registry = Registry()

# --- Data Quality Pipeline Tools ---

def profile_data(state: Dict[str, Any]) -> Dict[str, Any]:
    print("-> Profiling Data...")
    # Simulate loading a dataset
    if "data_quality_score" not in state:
        state["dataset_size"] = 1000
        # Initialize with some simulated messiness if not present
        state["anomaly_count"] = state.get("anomaly_count", 50) 
    return state

def identify_anomalies(state: Dict[str, Any]) -> Dict[str, Any]:
    count = state.get("anomaly_count", 0)
    print(f"-> Identifying Anomalies: found {count} issues.")
    return state

def generate_rules(state: Dict[str, Any]) -> Dict[str, Any]:
    count = state.get("anomaly_count", 0)
    print(f"-> Generating Rules to fix {count} anomalies...")
    state["rules_generated"] = True
    return state

def apply_rules(state: Dict[str, Any]) -> Dict[str, Any]:
    print("-> Applying Rules (Cleaning data)...")
    current_anomalies = state.get("anomaly_count", 0)
    # Simulate cleaning: remove half of the anomalies
    remaining = int(current_anomalies / 2)
    state["anomaly_count"] = remaining
    print(f"-> Cleaning Complete. Remaining anomalies: {remaining}")
    return state

def finish_pipeline(state: Dict[str, Any]) -> Dict[str, Any]:
    print("-> Pipeline Finished. Final State Reached.")
    return state

# Register them
node_registry.register("profile_data", profile_data)
node_registry.register("identify_anomalies", identify_anomalies)
node_registry.register("generate_rules", generate_rules)
node_registry.register("apply_rules", apply_rules)
node_registry.register("apply_rules", apply_rules)
node_registry.register("finish_pipeline", finish_pipeline)

# HITL Tool
def wait_for_approval(state: Dict[str, Any]) -> Dict[str, Any]:
    print("-> Creating approval request...")
    # We don't block here technically; the engine handles the suspension based on a signal or we can just return.
    # But to follow the pattern, we might rely on the engine detecting this node or a flag.
    # For now, we'll just set a flag in the state that the engine check.
    state["__suspend__"] = True
    return state

node_registry.register("wait_for_approval", wait_for_approval)


