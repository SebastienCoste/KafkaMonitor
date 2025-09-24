import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from .blueprint_config_models import (
    EntityDefinitionsSchema, BlueprintUIConfig, ConfigurationSchema,
    EntityConfiguration, FileGenerationResult, GeneratedFile
)

logger = logging.getLogger(__name__)

class BlueprintConfigurationGenerator:
    def __init__(self, entity_definitions: EntityDefinitionsSchema):
        self.entity_definitions = entity_definitions
        self.file_mappings = entity_definitions.fileMappings
        self.config_structure = entity_definitions.configStructure
        
    async def generate_all_files(
        self, 
        ui_config: BlueprintUIConfig, 
        environments: List[str],
        output_path: Optional[str] = None
    ) -> FileGenerationResult:
        """Generate all blueprint configuration files"""
        try:
            generated_files = []
            errors = []
            
            for schema in ui_config.schemas:
                # Generate files for this schema
                schema_files = await self._generate_schema_files(schema, environments, output_path)
                generated_files.extend(schema_files.files)
                errors.extend(schema_files.errors)
            
            return FileGenerationResult(
                success=len(errors) == 0,
                files=generated_files,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Error generating files: {e}")
            return FileGenerationResult(
                success=False,
                errors=[f"Failed to generate files: {str(e)}"]
            )
    
    async def _generate_schema_files(
        self, 
        schema: ConfigurationSchema, 
        environments: List[str],
        output_path: Optional[str] = None
    ) -> FileGenerationResult:
        """Generate files for a specific schema"""
        generated_files = []
        errors = []
        
        try:
            # Group configurations by file type
            file_groups = self._group_configurations_by_file(schema.configurations)
            
            # Generate global configuration file
            if 'global' in file_groups:
                global_file = await self._generate_global_config(
                    file_groups['global'], schema.namespace, environments, output_path
                )
                if global_file:
                    generated_files.append(global_file)
            
            # Generate message configuration files
            if 'messageConfigs' in file_groups:
                message_files = await self._generate_message_configs(
                    file_groups['messageConfigs'], environments, output_path
                )
                generated_files.extend(message_files)
            
            # Generate search experience files
            if 'searchExperience' in file_groups:
                search_files = await self._generate_search_experience_configs(
                    file_groups['searchExperience'], environments, output_path
                )
                generated_files.extend(search_files)
            
            return FileGenerationResult(
                success=True,
                files=generated_files,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Error generating schema files: {e}")
            return FileGenerationResult(
                success=False,
                errors=[f"Failed to generate schema files: {str(e)}"]
            )
    
    def _group_configurations_by_file(self, configurations: List[EntityConfiguration]) -> Dict[str, List[EntityConfiguration]]:
        """Group configurations by target file type"""
        file_groups = {}
        
        for config in configurations:
            # Determine which file this entity belongs to
            target_file = None
            for file_type, mapping in self.file_mappings.items():
                if config.entityType in mapping.entities:
                    target_file = file_type
                    break
            
            if target_file:
                if target_file not in file_groups:
                    file_groups[target_file] = []
                file_groups[target_file].append(config)
        
        return file_groups
    
    async def _generate_global_config(
        self, 
        configurations: List[EntityConfiguration],
        schema_namespace: str,
        environments: List[str],
        output_path: Optional[str] = None
    ) -> Optional[GeneratedFile]:
        """Generate schema-specific global configuration file"""
        try:
            global_config = {
                "environments": {},
                "config": {}
            }
            
            # Process each configuration
            for config in configurations:
                if not config.enabled:
                    continue
                    
                # Add to global config section
                if config.baseConfig:
                    global_config["config"][config.entityType] = config.baseConfig
                
                # Add environment overrides
                for env in environments:
                    if env in config.environmentOverrides:
                        if env not in global_config["environments"]:
                            global_config["environments"][env] = {}
                        
                        global_config["environments"][env][config.entityType] = config.environmentOverrides[env]
            
            # Create schema-specific filename to avoid conflicts
            mapping = self.file_mappings['global']
            # Convert namespace to safe filename (replace dots with underscores)
            safe_namespace = schema_namespace.replace('.', '_').replace('-', '_')
            schema_filename = f"global_{safe_namespace}.json"
            file_path = mapping.path  # Just the path, not path + filename
            
            return GeneratedFile(
                filename=schema_filename,
                path=file_path,
                content=global_config
            )
            
        except Exception as e:
            logger.error(f"Error generating global config: {e}")
            return None
    
    async def _generate_message_configs(
        self, 
        configurations: List[EntityConfiguration], 
        environments: List[str],
        output_path: Optional[str] = None
    ) -> List[GeneratedFile]:
        """Generate message configuration files"""
        generated_files = []
        
        try:
            # Group by entity type (each entity type gets its own file)
            entity_groups = {}
            for config in configurations:
                if config.entityType not in entity_groups:
                    entity_groups[config.entityType] = []
                entity_groups[config.entityType].append(config)
            
            # Generate file for each entity type
            for entity_type, configs in entity_groups.items():
                message_config = {
                    "environments": {},
                    "messageConfigs": {}
                }
                
                # Process configurations
                for config in configs:
                    if not config.enabled:
                        continue
                    
                    # Add to messageConfigs section
                    config_data = {}
                    
                    # Add inheritance
                    if config.inherit:
                        config_data["inherit"] = config.inherit
                    
                    # Add base configuration
                    if config.baseConfig:
                        config_data[config.entityType] = config.baseConfig
                    
                    # Add other entity-specific data
                    if config.entityType == 'discoveryFeatures':
                        if 'discoverable' not in config_data:
                            config_data['discoverable'] = True
                        if 'processingOnly' not in config_data:
                            config_data['processingOnly'] = False
                    
                    message_config["messageConfigs"][config.name] = config_data
                    
                    # Add environment-specific configurations
                    for env in environments:
                        if env in config.environmentOverrides:
                            if env not in message_config["environments"]:
                                message_config["environments"][env] = {"configs": {}}
                            
                            if "configs" not in message_config["environments"][env]:
                                message_config["environments"][env]["configs"] = {}
                            
                            message_config["environments"][env]["configs"][config.name] = {
                                config.entityType: config.environmentOverrides[env]
                            }
                
                # Create file
                mapping = self.file_mappings['messageConfigs']
                filename = mapping.filename.replace('{EntityName}', entity_type.capitalize())
                file_path = mapping.path  # Just the path, not path + filename
                
                generated_files.append(GeneratedFile(
                    filename=filename,
                    path=file_path,
                    content=message_config
                ))
            
            return generated_files
            
        except Exception as e:
            logger.error(f"Error generating message configs: {e}")
            return []
    
    async def _generate_search_experience_configs(
        self, 
        configurations: List[EntityConfiguration], 
        environments: List[str],
        output_path: Optional[str] = None
    ) -> List[GeneratedFile]:
        """Generate search experience configuration files"""
        generated_files = []
        
        try:
            for config in configurations:
                if not config.enabled:
                    continue
                
                search_config = {}
                
                # Add base configuration
                if config.baseConfig:
                    search_config.update(config.baseConfig)
                
                # Add environment overrides (if any)
                # Note: Search experience typically doesn't have environment overrides
                # but we support it for flexibility
                
                # Create file
                mapping = self.file_mappings['searchExperience']
                filename = f"{config.name}.json" if config.name != 'search_queries' else mapping.filename
                file_path = mapping.path  # Just the path, not path + filename
                
                generated_files.append(GeneratedFile(
                    filename=filename,
                    path=file_path,
                    content=search_config
                ))
            
            return generated_files
            
        except Exception as e:
            logger.error(f"Error generating search experience configs: {e}")
            return []
    
    async def generate_blueprint_cnf(
        self, 
        ui_config: BlueprintUIConfig, 
        namespace: str,
        version: str = "git_version",
        owner: str = "",
        description: str = ""
    ) -> GeneratedFile:
        """Generate blueprint_cnf.json file"""
        try:
            blueprint_cnf = {
                "namespace": namespace,
                "version": version,
                "owner": owner,
                "description": description,
                "schemas": [],
                "transformSpecs": [],
                "searchExperience": {
                    "configs": [],
                    "templates": []
                }
            }
            
            # Add schemas
            for schema in ui_config.schemas:
                schema_config = {
                    "namespace": schema.namespace,
                    "global": [],
                    "messages": []
                }
                
                # Determine which files this schema needs
                entity_types = set()
                for config in schema.configurations:
                    entity_types.add(config.entityType)
                
                # Add global files
                global_entities = set(self.file_mappings['global'].entities)
                if entity_types.intersection(global_entities):
                    schema_config["global"].append("global.json")
                
                # Add message files
                message_entities = set(self.file_mappings['messageConfigs'].entities)
                message_entity_types = entity_types.intersection(message_entities)
                for entity_type in message_entity_types:
                    filename = f"config{entity_type.capitalize()}.json"
                    schema_config["messages"].append(filename)
                
                blueprint_cnf["schemas"].append(schema_config)
                
                # Add search experience files
                search_entities = set(self.file_mappings['searchExperience'].entities)
                if entity_types.intersection(search_entities):
                    blueprint_cnf["searchExperience"]["configs"].append("searchExperience.json")
            
            return GeneratedFile(
                filename="blueprint_cnf.json",
                path="",
                content=blueprint_cnf
            )
            
        except Exception as e:
            logger.error(f"Error generating blueprint_cnf.json: {e}")
            raise
    
    async def write_files_to_disk(self, files: List[GeneratedFile], base_path: str) -> List[str]:
        """Write generated files to disk"""
        written_files = []
        
        try:
            base_path = Path(base_path)
            
            for file in files:
                # Create directory if it doesn't exist
                file_path = base_path / file.path / file.filename
                
                try:
                    # Ensure parent directories exist
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Handle existing file - try multiple approaches to remove permission issues
                    if file_path.exists():
                        try:
                            # Try to make file writable first
                            file_path.chmod(0o666)
                            file_path.unlink()
                            logger.info(f"Removed existing file: {file_path}")
                        except PermissionError as e:
                            logger.warning(f"Could not remove existing file {file_path}: {e}")
                            # Try backup approach - write to temp file then replace
                            import tempfile
                            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                                json.dump(file.content, tmp_file, indent=2)
                                tmp_path = Path(tmp_file.name)
                            
                            # Try to replace the file
                            try:
                                tmp_path.replace(file_path)
                                logger.info(f"Replaced existing file via temp: {file_path}")
                            except Exception as replace_error:
                                tmp_path.unlink()  # Clean up temp file
                                raise PermissionError(f"Cannot write to {file_path}: {replace_error}")
                    else:
                        # File doesn't exist, write normally
                        with open(file_path, 'w') as f:
                            json.dump(file.content, f, indent=2)
                        logger.info(f"Created new file: {file_path}")
                    
                    written_files.append(str(file_path))
                    
                except PermissionError as perm_error:
                    logger.error(f"Permission denied writing to {file_path}: {perm_error}")
                    # Try alternative location or suggest user action
                    raise PermissionError(
                        f"Cannot write to {file_path}. Please check file permissions or close any applications that might have the file open."
                    )
                except Exception as file_error:
                    logger.error(f"Error writing file {file_path}: {file_error}")
                    raise
        
        except Exception as e:
            logger.error(f"Error writing files to disk: {e}")
            raise
        
        return written_files