from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"
    NOTE = "note"
    IMAGE = "image"


class ResourceStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ResourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Resource name")
    type: ResourceType = Field(..., description="Resource type")
    path: Optional[str] = Field(None, max_length=1024, description="File or directory path")
    size: int = Field(0, ge=0, description="Resource size in bytes")
    mime_type: Optional[str] = Field(None, max_length=255, description="MIME type")
    tags: Optional[str] = Field(None, max_length=255, description="Comma-separated tags")
    description: Optional[str] = Field(None, description="Resource description")
    status: ResourceStatus = Field(ResourceStatus.ACTIVE, description="Resource status")


class ResourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Resource name")
    path: Optional[str] = Field(None, max_length=1024, description="File or directory path")
    size: Optional[int] = Field(None, ge=0, description="Resource size in bytes")
    mime_type: Optional[str] = Field(None, max_length=255, description="MIME type")
    tags: Optional[str] = Field(None, max_length=255, description="Comma-separated tags")
    description: Optional[str] = Field(None, description="Resource description")
    status: Optional[ResourceStatus] = Field(None, description="Resource status")


class ResourceResponse(BaseModel):
    id: int
    name: str
    type: ResourceType
    path: Optional[str] = None
    size: int
    mime_type: Optional[str] = None
    tags: Optional[str] = None
    description: Optional[str] = None
    status: ResourceStatus
    created_by: int
    created_at: str

    class Config:
        from_attributes = True


class ResourceListResponse(BaseModel):
    resources: List[ResourceResponse]
    total: int
    page: int
    page_size: int
    pages: int

    model_config = {"from_attributes": True}
