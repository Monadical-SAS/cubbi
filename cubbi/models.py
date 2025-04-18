from enum import Enum
from typing import Any, Dict, List, Optional, Union

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


class ImageEnvironmentVariable(BaseModel):
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


class ImageInit(BaseModel):
    pre_command: Optional[str] = None
    command: str


class Image(BaseModel):
    name: str
    description: str
    version: str
    maintainer: str
    image: str
    init: Optional[ImageInit] = None
    environment: List[ImageEnvironmentVariable] = []
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
    image: str
    status: SessionStatus
    container_id: Optional[str] = None
    ports: Dict[int, int] = Field(default_factory=dict)


class Config(BaseModel):
    docker: Dict[str, str] = Field(default_factory=dict)
    images: Dict[str, Image] = Field(default_factory=dict)
    defaults: Dict[str, object] = Field(
        default_factory=dict
    )  # Can store strings, booleans, or other values
    mcps: List[Dict[str, Any]] = Field(default_factory=list)
