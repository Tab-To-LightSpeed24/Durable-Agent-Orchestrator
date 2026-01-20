from sqlalchemy import Column, String, JSON, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class GraphModel(Base):
    __tablename__ = "graphs"

    id = Column(String, primary_key=True, index=True)
    definition_json = Column(JSON, nullable=False)  # Store the full GraphCreateRequest as JSON
    created_at = Column(DateTime, default=datetime.utcnow)

class WorkflowRunModel(Base):
    __tablename__ = "workflow_runs"

    run_id = Column(String, primary_key=True, index=True)
    graph_id = Column(String, ForeignKey("graphs.id"), nullable=False)
    status = Column(String, default="created", index=True)  # running, completed, failed, awaiting_approval
    current_node_id = Column(String, nullable=True)
    state = Column(JSON, default={})
    logs = Column(JSON, default=[]) # Storing logs as specific JSON list
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

