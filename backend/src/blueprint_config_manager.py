import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
import asyncio

from .blueprint_config_models import (
    EntityDefinitionsSchema, BlueprintUIConfig, ConfigurationSchema,
    EntityConfiguration, ConfigValidationResult, FileGenerationResult,
    CreateEntityRequest, UpdateEntityRequest, CreateSchemaRequest,
    GenerateFilesRequest, EnvironmentOverrideRequest
)
from .blueprint_config_parser import BlueprintConfigurationParser
from .blueprint_config_generator import BlueprintConfigurationGenerator
from .blueprint_file_manager import BlueprintFileManager

logger = logging.getLogger(__name__)

class BlueprintConfigurationManager:
    def __init__(self, entity_definitions_path: str, blueprint_file_manager: BlueprintFileManager):
        self.entity_definitions_path = entity_definitions_path
        self.blueprint_file_manager = blueprint_file_manager
        self.entity_definitions: Optional[EntityDefinitionsSchema] = None
        self.parser: Optional[BlueprintConfigurationParser] = None
        self.generator: Optional[BlueprintConfigurationGenerator] = None
        
        # Load entity definitions synchronously to avoid race conditions
        self._load_entity_definitions_sync()
    
    def _load_entity_definitions_sync(self):
        """Load entity definitions from configuration file synchronously"""
        try:
            with open(self.entity_definitions_path, 'r') as f:
                definitions_data = json.load(f)
            
            self.entity_definitions = EntityDefinitionsSchema(**definitions_data)
            self.parser = BlueprintConfigurationParser(self.entity_definitions)
            self.generator = BlueprintConfigurationGenerator(self.entity_definitions)
            
            logger.info(f"Loaded entity definitions with {len(self.entity_definitions.entityTypes)} entity types")
            
        except Exception as e:
            logger.error(f"Failed to load entity definitions: {e}")
            raise

    async def load_entity_definitions(self):
        """Load entity definitions from configuration file (async version for backward compatibility)"""
        if not self.entity_definitions:
            self._load_entity_definitions_sync()
    
    async def get_entity_definitions(self) -> EntityDefinitionsSchema:
        """Get entity definitions schema"""
        if not self.entity_definitions:
            await self.load_entity_definitions()
        return self.entity_definitions
    
    async def load_blueprint_config(self, blueprint_path: str) -> Tuple[BlueprintUIConfig, List[str]]:
        """Load or create blueprint UI configuration"""
        try:
            blueprint_path = Path(blueprint_path)
            ui_config_path = blueprint_path / "blueprint_ui_config.json"
            
            if ui_config_path.exists():
                # Load existing UI config
                with open(ui_config_path, 'r') as f:
                    ui_config_data = json.load(f)
                ui_config = BlueprintUIConfig(**ui_config_data)
                
                logger.info(f"Loaded existing blueprint UI config with {len(ui_config.schemas)} schemas")
                return ui_config, []
            else:
                # Parse existing blueprint files and create UI config
                if not self.parser:
                    await self.load_entity_definitions()
                
                parse_result, ui_config = await self.parser.parse_blueprint_directory(str(blueprint_path))
                
                if ui_config:
                    # Save the newly created UI config
                    await self.save_blueprint_config(str(blueprint_path), ui_config)
                    logger.info(f"Created new blueprint UI config from existing files")
                    return ui_config, parse_result.warnings
                else:
                    # Create empty UI config
                    ui_config = BlueprintUIConfig()
                    logger.info("Created empty blueprint UI config")
                    return ui_config, parse_result.errors if parse_result else []
                    
        except Exception as e:
            logger.error(f"Error loading blueprint config: {e}")
            # Return empty config with error
            return BlueprintUIConfig(), [f"Failed to load blueprint config: {str(e)}"]
    
    async def save_blueprint_config(self, blueprint_path: str, ui_config: BlueprintUIConfig) -> bool:
        """Save blueprint UI configuration"""
        try:
            blueprint_path = Path(blueprint_path)
            ui_config_path = blueprint_path / "blueprint_ui_config.json"
            
            # Update last modified timestamp
            ui_config.lastModified = datetime.now().isoformat()
            
            # Ensure directory exists
            ui_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save configuration
            with open(ui_config_path, 'w') as f:
                json.dump(ui_config.dict(), f, indent=2)
            
            logger.info(f"Saved blueprint UI config to {ui_config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving blueprint config: {e}")
            return False
    
    async def create_schema(self, blueprint_path: str, request: CreateSchemaRequest) -> Tuple[str, List[str]]:
        """Create a new configuration schema"""
        try:
            ui_config, warnings = await self.load_blueprint_config(blueprint_path)
            
            # Create new schema
            new_schema = ConfigurationSchema(namespace=request.namespace)
            ui_config.schemas.append(new_schema)
            
            # Save configuration
            success = await self.save_blueprint_config(blueprint_path, ui_config)
            if success:
                return new_schema.id, warnings
            else:
                return "", warnings + ["Failed to save configuration"]
                
        except Exception as e:
            logger.error(f"Error creating schema: {e}")
            return "", [f"Failed to create schema: {str(e)}"]
    
    async def create_entity(self, blueprint_path: str, request: CreateEntityRequest) -> Tuple[str, List[str]]:
        """Create a new entity configuration"""
        try:
            ui_config, warnings = await self.load_blueprint_config(blueprint_path)
            
            # Find target schema
            target_schema = None
            if request.schemaId:
                for schema in ui_config.schemas:
                    if schema.id == request.schemaId:
                        target_schema = schema
                        break
            else:
                # Use first schema or create one
                if ui_config.schemas:
                    target_schema = ui_config.schemas[0]
                else:
                    target_schema = ConfigurationSchema(namespace="default")
                    ui_config.schemas.append(target_schema)
            
            if not target_schema:
                return "", warnings + ["Target schema not found"]
            
            # Validate entity type
            if not self.entity_definitions:
                await self.load_entity_definitions()
            
            if request.entityType not in self.entity_definitions.entityTypes:
                return "", warnings + [f"Invalid entity type: {request.entityType}"]
            
            # Create new entity
            new_entity = EntityConfiguration(
                entityType=request.entityType,
                name=request.name,
                baseConfig=request.baseConfig
            )
            
            target_schema.configurations.append(new_entity)
            
            # Save configuration
            success = await self.save_blueprint_config(blueprint_path, ui_config)
            if success:
                return new_entity.id, warnings
            else:
                return "", warnings + ["Failed to save configuration"]
                
        except Exception as e:
            logger.error(f"Error creating entity: {e}")
            return "", [f"Failed to create entity: {str(e)}"]
    
    async def update_entity(
        self, 
        blueprint_path: str, 
        entity_id: str, 
        request: UpdateEntityRequest
    ) -> Tuple[bool, List[str]]:
        """Update an existing entity configuration"""
        try:
            ui_config, warnings = await self.load_blueprint_config(blueprint_path)
            
            # Find target entity
            target_entity = None
            for schema in ui_config.schemas:
                for entity in schema.configurations:
                    if entity.id == entity_id:
                        target_entity = entity
                        break
                if target_entity:
                    break
            
            if not target_entity:
                return False, warnings + ["Entity not found"]
            
            # Update entity properties
            if request.name is not None:
                target_entity.name = request.name
            if request.baseConfig is not None:
                target_entity.baseConfig = request.baseConfig
            if request.environmentOverrides is not None:
                target_entity.environmentOverrides = request.environmentOverrides
            if request.inherit is not None:
                target_entity.inherit = request.inherit
            if request.enabled is not None:
                target_entity.enabled = request.enabled
            
            # Save configuration
            success = await self.save_blueprint_config(blueprint_path, ui_config)
            return success, warnings if success else warnings + ["Failed to save configuration"]
            
        except Exception as e:
            logger.error(f"Error updating entity: {e}")
            return False, [f"Failed to update entity: {str(e)}"]
    
    async def delete_entity(self, blueprint_path: str, entity_id: str) -> Tuple[bool, List[str]]:
        """Delete an entity configuration"""
        try:
            ui_config, warnings = await self.load_blueprint_config(blueprint_path)
            
            # Find and remove target entity
            removed = False
            for schema in ui_config.schemas:
                for i, entity in enumerate(schema.configurations):
                    if entity.id == entity_id:
                        schema.configurations.pop(i)
                        removed = True
                        break
                if removed:
                    break
            
            if not removed:
                return False, warnings + ["Entity not found"]
            
            # Save configuration
            success = await self.save_blueprint_config(blueprint_path, ui_config)
            return success, warnings if success else warnings + ["Failed to save configuration"]
            
        except Exception as e:
            logger.error(f"Error deleting entity: {e}")
            return False, [f"Failed to delete entity: {str(e)}"]
    
    async def set_environment_override(
        self, 
        blueprint_path: str, 
        request: EnvironmentOverrideRequest
    ) -> Tuple[bool, List[str]]:
        """Set environment-specific override for an entity"""
        try:
            ui_config, warnings = await self.load_blueprint_config(blueprint_path)
            
            # Find target entity
            target_entity = None
            for schema in ui_config.schemas:
                for entity in schema.configurations:
                    if entity.id == request.entityId:
                        target_entity = entity
                        break
                if target_entity:
                    break
            
            if not target_entity:
                return False, warnings + ["Entity not found"]
            
            # Validate environment
            if not self.entity_definitions:
                await self.load_entity_definitions()
            
            if request.environment not in self.entity_definitions.environments:
                return False, warnings + [f"Invalid environment: {request.environment}"]
            
            # Set override
            target_entity.environmentOverrides[request.environment] = request.overrides
            
            # Save configuration
            success = await self.save_blueprint_config(blueprint_path, ui_config)
            return success, warnings if success else warnings + ["Failed to save configuration"]
            
        except Exception as e:
            logger.error(f"Error setting environment override: {e}")
            return False, [f"Failed to set environment override: {str(e)}"]
    
    async def generate_files(self, blueprint_path: str, request: GenerateFilesRequest) -> FileGenerationResult:
        """Generate blueprint configuration files"""
        try:
            if not self.generator:
                await self.load_entity_definitions()
            
            ui_config, warnings = await self.load_blueprint_config(blueprint_path)
            
            # Find target schema
            target_schema = None
            if request.schemaId:
                for schema in ui_config.schemas:
                    if schema.id == request.schemaId:
                        target_schema = schema
                        break
            
            if not target_schema:
                return FileGenerationResult(
                    success=False,
                    errors=["Schema not found"]
                )
            
            # Generate files for the schema
            result = await self.generator.generate_all_files(
                BlueprintUIConfig(schemas=[target_schema]),
                request.environments,
                request.outputPath
            )
            
            # Write files to disk if output path is provided
            if result.success and request.outputPath:
                output_path = request.outputPath or blueprint_path
                written_files = await self.generator.write_files_to_disk(result.files, output_path)
                logger.info(f"Generated {len(written_files)} files to {output_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating files: {e}")
            return FileGenerationResult(
                success=False,
                errors=[f"Failed to generate files: {str(e)}"]
            )
    
    async def validate_configuration(self, blueprint_path: str) -> ConfigValidationResult:
        """Validate current blueprint configuration"""
        try:
            ui_config, load_warnings = await self.load_blueprint_config(blueprint_path)
            
            errors = []
            warnings = load_warnings.copy()
            
            # Validate each schema
            for schema in ui_config.schemas:
                if not schema.namespace:
                    errors.append(f"Schema {schema.id} missing namespace")
                
                # Validate entities
                for entity in schema.configurations:
                    if not entity.name:
                        errors.append(f"Entity {entity.id} missing name")
                    
                    if entity.entityType not in self.entity_definitions.entityTypes:
                        errors.append(f"Entity {entity.id} has invalid type: {entity.entityType}")
                    
                    # Validate inheritance references
                    if entity.inherit:
                        for inherit_name in entity.inherit:
                            # Check if inherited config exists
                            found = any(
                                other.name == inherit_name 
                                for other in schema.configurations 
                                if other.id != entity.id
                            )
                            if not found:
                                warnings.append(f"Entity {entity.name} inherits from non-existent config: {inherit_name}")
            
            return ConfigValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error validating configuration: {e}")
            return ConfigValidationResult(
                valid=False,
                errors=[f"Failed to validate configuration: {str(e)}"]
            )