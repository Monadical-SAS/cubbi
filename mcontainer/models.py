from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


class DriverEnvironmentVariable(BaseModel):
    name: str
    description: str
    required: bool = False
    default: Optional[str] = None
    sensitive: bool = False


class PersistentConfig(BaseModel):
    source: str
    target: str
    type: str  # "directory" or "file"
    description: str = ""


class Driver(BaseModel):
    name: str
    description: str
    version: str
    maintainer: str
    image: str
    environment: List[DriverEnvironmentVariable] = []
    ports: List[int] = []
    volumes: List[Dict[str, str]] = []
    persistent_configs: List[PersistentConfig] = []


class Session(BaseModel):
    id: str
    name: str
    driver: str
    status: SessionStatus
    container_id: Optional[str] = None
    environment: Dict[str, str] = Field(default_factory=dict)
    project: Optional[str] = None
    created_at: str
    ports: Dict[int, int] = Field(default_factory=dict)


class Config(BaseModel):
    docker: Dict[str, str] = Field(default_factory=dict)
    drivers: Dict[str, Driver] = Field(default_factory=dict)
    sessions: Dict[str, dict] = Field(
        default_factory=dict
    )  # Store as dict to avoid serialization issues
    defaults: Dict[str, str] = Field(default_factory=dict)
