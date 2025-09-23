from pydantic import BaseModel, Field, validator
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import uuid

class EntityFieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    MAP = "map"
    SELECT = "select"

class EntityFieldDefinition(BaseModel):
    type: EntityFieldType
    title: str
    description: Optional[str] = None
    required: Optional[bool] = False
    default: Optional[Any] = None
    min: Optional[float] = None
    max: Optional[float] = None
    options: Optional[List[str]] = None
    items: Optional[Dict[str, Any]] = None
    fields: Optional[Dict[str, 'EntityFieldDefinition']] = None
    valueType: Optional['EntityFieldDefinition'] = None

# Fix forward reference
EntityFieldDefinition.model_rebuild()

class EntityDefinition(BaseModel):
    title: str
    description: str
    fields: Dict[str, EntityFieldDefinition]

class FileMapping(BaseModel):
    filename: str
    path: str
    entities: List[str]

class ConfigStructureDefinition(BaseModel):
    type: str
    contains: Optional[List[str]] = None
    supports: Optional[List[str]] = None

class EntityDefinitionsSchema(BaseModel):
    entityTypes: Dict[str, EntityDefinition]
    environments: List[str]
    fileMappings: Dict[str, FileMapping]
    configStructure: Dict[str, Dict[str, ConfigStructureDefinition]]

class EntityConfiguration(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entityType: str
    name: str
    baseConfig: Dict[str, Any] = Field(default_factory=dict)
    environmentOverrides: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    inherit: Optional[List[str]] = None
    enabled: bool = True

class ConfigurationSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    namespace: str
    configurations: List[EntityConfiguration] = Field(default_factory=list)

class BlueprintUIConfig(BaseModel):
    schemas: List[ConfigurationSchema] = Field(default_factory=list)
    fileOutputs: Dict[str, Any] = Field(default_factory=dict)
    lastModified: Optional[str] = None

# API Request Models
class CreateEntityRequest(BaseModel):
    entityType: str
    name: str
    baseConfig: Dict[str, Any] = Field(default_factory=dict)
    schemaId: Optional[str] = None

class UpdateEntityRequest(BaseModel):
    name: Optional[str] = None
    baseConfig: Optional[Dict[str, Any]] = None
    environmentOverrides: Optional[Dict[str, Dict[str, Any]]] = None
    inherit: Optional[List[str]] = None
    enabled: Optional[bool] = None

class CreateSchemaRequest(BaseModel):
    namespace: str

class GenerateFilesRequest(BaseModel):
    schemaId: str
    environments: List[str]
    outputPath: Optional[str] = None

class ConfigValidationResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class EnvironmentOverrideRequest(BaseModel):
    entityId: str
    environment: str
    overrides: Dict[str, Any]

# File Generation Models
class GeneratedFile(BaseModel):
    filename: str
    path: str
    content: Dict[str, Any]

class FileGenerationResult(BaseModel):
    success: bool
    files: List[GeneratedFile] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

# Configuration Parsing Models
class ParsedConfiguration(BaseModel):
    entityType: str
    name: str
    config: Dict[str, Any]
    environments: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    inherit: Optional[List[str]] = None

class ConfigurationParseResult(BaseModel):
    success: bool
    configurations: List[ParsedConfiguration] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)