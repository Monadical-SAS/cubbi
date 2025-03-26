from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


class MCPStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    NOT_FOUND = "not_found"
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


class VolumeMount(BaseModel):
    mountPath: str
    description: str = ""


class DriverInit(BaseModel):
    pre_command: Optional[str] = None
    command: str


class Driver(BaseModel):
    name: str
    description: str
    version: str
    maintainer: str
    image: str
    init: Optional[DriverInit] = None
    environment: List[DriverEnvironmentVariable] = []
    ports: List[int] = []
    volumes: List[VolumeMount] = []
    persistent_configs: List[PersistentConfig] = []


class RemoteMCP(BaseModel):
    name: str
    type: str = "remote"
    url: str
    headers: Dict[str, str] = Field(default_factory=dict)


class DockerMCP(BaseModel):
    name: str
    type: str = "docker"
    image: str
    command: str
    env: Dict[str, str] = Field(default_factory=dict)


class ProxyMCP(BaseModel):
    name: str
    type: str = "proxy"
    base_image: str
    proxy_image: str
    command: str
    proxy_options: Dict[str, Any] = Field(default_factory=dict)
    env: Dict[str, str] = Field(default_factory=dict)
    host_port: Optional[int] = None  # External port to bind the SSE port to on the host


MCP = Union[RemoteMCP, DockerMCP, ProxyMCP]


class MCPContainer(BaseModel):
    name: str
    container_id: str
    status: MCPStatus
    image: str
    ports: Dict[str, Optional[int]] = Field(default_factory=dict)
    created_at: str
    type: str


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
    mcps: List[str] = Field(default_factory=list)  # List of MCP server names
    model: str # Model used in this session


class Config(BaseModel):
    docker: Dict[str, str] = Field(default_factory=dict)
    drivers: Dict[str, Driver] = Field(default_factory=dict)
    defaults: Dict[str, object] = Field(
        default_factory=dict
    )  # Can store strings, booleans, or other values
    mcps: List[Dict[str, Any]] = Field(default_factory=list)
