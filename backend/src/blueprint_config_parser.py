import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from .blueprint_config_models import (
    EntityDefinitionsSchema, ConfigurationParseResult, ParsedConfiguration,
    EntityConfiguration, ConfigurationSchema, BlueprintUIConfig
)

logger = logging.getLogger(__name__)

class BlueprintConfigurationParser:
    def __init__(self, entity_definitions: EntityDefinitionsSchema):
        self.entity_definitions = entity_definitions
        self.environments = entity_definitions.environments
        
    async def parse_blueprint_directory(self, blueprint_path: str) -> Tuple[ConfigurationParseResult, Optional[BlueprintUIConfig]]:
        """Parse existing blueprint directory and extract configurations"""
        try:
            blueprint_path = Path(blueprint_path)
            
            # Read blueprint_cnf.json
            blueprint_cnf_path = blueprint_path / "blueprint_cnf.json"
            if not blueprint_cnf_path.exists():
                return ConfigurationParseResult(
                    success=False,
                    errors=[f"blueprint_cnf.json not found in {blueprint_path}"]
                ), None
            
            with open(blueprint_cnf_path, 'r') as f:
                blueprint_cnf = json.load(f)
            
            # Extract namespace and schemas
            namespace = blueprint_cnf.get('namespace', '')
            schemas_config = blueprint_cnf.get('schemas', [])
            
            if not schemas_config:
                return ConfigurationParseResult(
                    success=False,
                    errors=["No schemas found in blueprint_cnf.json"]
                ), None
            
            # Parse configurations for each schema
            ui_config = BlueprintUIConfig()
            all_configurations = []
            parse_errors = []
            parse_warnings = []
            
            for schema_config in schemas_config:
                schema_namespace = schema_config.get('namespace', namespace)
                
                # Create configuration schema
                config_schema = ConfigurationSchema(
                    namespace=schema_namespace,
                    configurations=[]
                )
                
                # Parse global configurations with auto-discovery
                global_dir = blueprint_path / "src" / "configs" / "global"
                processed_global_files = set()
                
                if global_dir.exists():
                    # First, process files from blueprint_cnf.json
                    global_files = schema_config.get('global', [])
                    for global_file in global_files:
                        global_path = global_dir / global_file
                        if global_path.exists():
                            processed_global_files.add(global_path.resolve())
                            result = await self._parse_global_config(global_path)
                            if result.success:
                                all_configurations.extend(result.configurations)
                                config_schema.configurations.extend(
                                    [EntityConfiguration(
                                        entityType=config.entityType,
                                        name=config.name,
                                        baseConfig=config.config,
                                        environmentOverrides=config.environments,
                                        inherit=config.inherit
                                    ) for config in result.configurations]
                                )
                            else:
                                parse_errors.extend(result.errors)
                                parse_warnings.extend(result.warnings)
                    
                    # Auto-discover any other .json files in global directory
                    for global_file in global_dir.glob("*.json"):
                        if global_file.resolve() not in processed_global_files:
                            logger.info(f"Auto-discovered global config: {global_file.name}")
                            result = await self._parse_global_config(global_file)
                            if result.success:
                                all_configurations.extend(result.configurations)
                                config_schema.configurations.extend(
                                    [EntityConfiguration(
                                        entityType=config.entityType,
                                        name=config.name,
                                        baseConfig=config.config,
                                        environmentOverrides=config.environments,
                                        inherit=config.inherit
                                    ) for config in result.configurations]
                                )
                            else:
                                parse_errors.extend(result.errors)
                                parse_warnings.extend(result.warnings)
                
                # Parse message configurations with auto-discovery
                messages_dir = blueprint_path / "src" / "configs" / "messages"
                processed_message_files = set()
                
                if messages_dir.exists():
                    # First, process files from blueprint_cnf.json
                    message_files = schema_config.get('messages', [])
                    for message_file in message_files:
                        message_path = messages_dir / message_file
                        if message_path.exists():
                            processed_message_files.add(message_path.resolve())
                            result = await self._parse_message_config(message_path)
                            if result.success:
                                all_configurations.extend(result.configurations)
                                config_schema.configurations.extend(
                                    [EntityConfiguration(
                                        entityType=config.entityType,
                                        name=config.name,
                                        baseConfig=config.config,
                                        environmentOverrides=config.environments,
                                        inherit=config.inherit
                                    ) for config in result.configurations]
                                )
                            else:
                                parse_errors.extend(result.errors)
                                parse_warnings.extend(result.warnings)
                    
                    # Auto-discover any other .json files in messages directory
                    for message_file in messages_dir.glob("*.json"):
                        if message_file.resolve() not in processed_message_files:
                            logger.info(f"Auto-discovered message config: {message_file.name}")
                            result = await self._parse_message_config(message_file)
                            if result.success:
                                all_configurations.extend(result.configurations)
                                config_schema.configurations.extend(
                                    [EntityConfiguration(
                                        entityType=config.entityType,
                                        name=config.name,
                                        baseConfig=config.config,
                                        environmentOverrides=config.environments,
                                        inherit=config.inherit
                                    ) for config in result.configurations]
                                )
                            else:
                                parse_errors.extend(result.errors)
                                parse_warnings.extend(result.warnings)
                
                # Merge duplicate entities with same entityType and name
                # This handles cases where same entity has separate entries for different environments
                merged_configs = {}
                for entity in config_schema.configurations:
                    key = (entity.entityType, entity.name)
                    if key in merged_configs:
                        # Merge environmentOverrides
                        existing = merged_configs[key]
                        existing.environmentOverrides.update(entity.environmentOverrides)
                        # Merge baseConfig (prefer non-empty)
                        if entity.baseConfig and not existing.baseConfig:
                            existing.baseConfig = entity.baseConfig
                        elif entity.baseConfig and existing.baseConfig:
                            # Merge nested dicts
                            existing.baseConfig.update(entity.baseConfig)
                        # Merge inherit lists
                        if entity.inherit:
                            if existing.inherit:
                                existing.inherit = list(set(existing.inherit + entity.inherit))
                            else:
                                existing.inherit = entity.inherit
                    else:
                        merged_configs[key] = entity
                
                # Replace configurations with merged ones
                config_schema.configurations = list(merged_configs.values())
                
                ui_config.schemas.append(config_schema)
            
            # Parse search experience configurations
            # Auto-discover searchExperience JSON files in the directory
            search_exp_dir = blueprint_path / "src" / "searchExperience"
            processed_files = set()
            
            if search_exp_dir.exists():
                # First, process files listed in blueprint_cnf.json
                search_experience = blueprint_cnf.get('searchExperience', {})
                if search_experience:
                    search_configs = search_experience.get('configs', [])
                    for search_config in search_configs:
                        search_path = search_exp_dir / search_config
                        if search_path.exists():
                            processed_files.add(search_path.resolve())
                            result = await self._parse_search_experience_config(search_path)
                            if result.success:
                                all_configurations.extend(result.configurations)
                                # Add to first schema (or create new one if needed)
                                if ui_config.schemas:
                                    ui_config.schemas[0].configurations.extend(
                                        [EntityConfiguration(
                                            entityType=config.entityType,
                                            name=config.name,
                                            baseConfig=config.config,
                                            environmentOverrides=config.environments,
                                            inherit=config.inherit
                                        ) for config in result.configurations]
                                    )
                
                # Auto-discover any other .json files in searchExperience directory
                for search_file in search_exp_dir.glob("*.json"):
                    if search_file.resolve() not in processed_files:
                        logger.info(f"Auto-discovered searchExperience file: {search_file.name}")
                        result = await self._parse_search_experience_config(search_file)
                        if result.success:
                            all_configurations.extend(result.configurations)
                            # Add to first schema (or create new one if needed)
                            if ui_config.schemas:
                                ui_config.schemas[0].configurations.extend(
                                    [EntityConfiguration(
                                        entityType=config.entityType,
                                        name=config.name,
                                        baseConfig=config.config,
                                        environmentOverrides=config.environments,
                                        inherit=config.inherit
                                    ) for config in result.configurations]
                                )
                        else:
                            parse_errors.extend(result.errors)
                            parse_warnings.extend(result.warnings)
            
            return ConfigurationParseResult(
                success=len(parse_errors) == 0,
                configurations=all_configurations,
                errors=parse_errors,
                warnings=parse_warnings
            ), ui_config
            
        except Exception as e:
            logger.error(f"Error parsing blueprint directory: {e}")
            return ConfigurationParseResult(
                success=False,
                errors=[f"Failed to parse blueprint directory: {str(e)}"]
            ), None
    
    async def _parse_global_config(self, config_path: Path) -> ConfigurationParseResult:
        """Parse global configuration file"""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            configurations = []
            errors = []
            warnings = []
            
            # Parse global config section
            global_config = config_data.get('config', {})
            if global_config:
                # Extract different entity types from global config
                for entity_type in ['access', 'messageStorage', 'discoveryStorage', 'inferenceServiceConfigs']:
                    if entity_type in global_config:
                        configurations.append(ParsedConfiguration(
                            entityType=entity_type,
                            name=f"global_{entity_type}",
                            config=global_config[entity_type],
                            environments={}
                        ))
            
            # Parse environment-specific configurations
            # Collect all environments for each entity type first, then create single ParsedConfiguration
            environments_config = config_data.get('environments', {})
            if environments_config:
                # Group environment configs by entity type
                storages_envs = {}
                inference_envs = {}
                access_envs = {}
                
                for env, env_config in environments_config.items():
                    if env.upper() in self.environments:
                        if 'storages' in env_config:
                            storages_envs[env.upper()] = env_config['storages']
                        if 'inferenceServiceConfigs' in env_config:
                            inference_envs[env.upper()] = env_config['inferenceServiceConfigs']
                        if 'access' in env_config:
                            access_envs[env.upper()] = env_config['access']
                
                # Create single ParsedConfiguration for each entity type with all environments
                if storages_envs:
                    configurations.append(ParsedConfiguration(
                        entityType='storages',
                        name='global_storages',
                        config={},
                        environments=storages_envs
                    ))
                
                if inference_envs:
                    configurations.append(ParsedConfiguration(
                        entityType='inferenceServiceConfigs',
                        name='global_inference',
                        config={},
                        environments=inference_envs
                    ))
                
                if access_envs:
                    configurations.append(ParsedConfiguration(
                        entityType='access',
                        name='global_access',
                        config={},
                        environments=access_envs
                    ))
            
            return ConfigurationParseResult(
                success=True,
                configurations=configurations,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error parsing global config {config_path}: {e}")
            return ConfigurationParseResult(
                success=False,
                errors=[f"Failed to parse global config: {str(e)}"]
            )
    
    async def _parse_message_config(self, config_path: Path) -> ConfigurationParseResult:
        """Parse message configuration file"""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            configurations = []
            errors = []
            warnings = []
            
            # Parse environment-specific configurations
            environments_config = config_data.get('environments', {})
            if environments_config:
                for env, env_config in environments_config.items():
                    if env.upper() in self.environments:
                        configs = env_config.get('configs', {})
                        for config_name, config_value in configs.items():
                            # Determine entity type based on config structure
                            entity_type = self._detect_entity_type(config_value)
                            if entity_type:
                                configurations.append(ParsedConfiguration(
                                    entityType=entity_type,
                                    name=config_name,
                                    config={},
                                    environments={env.upper(): config_value}
                                ))
            
            # Parse message configurations
            message_configs = config_data.get('messageConfigs', {})
            if message_configs:
                for config_name, config_value in message_configs.items():
                    # Extract inherit if present
                    inherit = config_value.get('inherit', [])
                    
                    # Determine entity types in this config
                    entity_types = self._extract_entity_types(config_value)
                    
                    if entity_types:
                        for entity_type in entity_types:
                            # Extract the specific config for this entity type
                            entity_config = {}
                            
                            if entity_type == 'transformation' and 'customTransformation' in config_value:
                                entity_config = config_value['customTransformation']
                            elif entity_type == 'imageModeration':
                                if 'preProcessing' in config_value and 'imageModeration' in config_value['preProcessing']:
                                    entity_config = config_value['preProcessing']['imageModeration']
                                elif 'imageModerationConfig' in config_value:
                                    entity_config = config_value['imageModerationConfig']
                                elif 'imageModeration' in config_value:
                                    entity_config = config_value['imageModeration']
                            elif entity_type == 'textModeration':
                                if 'preProcessing' in config_value and 'textModeration' in config_value['preProcessing']:
                                    entity_config = config_value['preProcessing']['textModeration']
                                elif 'textModerationConfig' in config_value:
                                    entity_config = config_value['textModerationConfig']
                                elif 'textModeration' in config_value:
                                    entity_config = config_value['textModeration']
                            elif entity_type == 'discoveryFeatures' and 'access' in config_value:
                                entity_config = config_value['access']
                            elif entity_type in config_value:
                                entity_config = config_value[entity_type]
                            
                            configurations.append(ParsedConfiguration(
                                entityType=entity_type,
                                name=f"{config_name}_{entity_type}",
                                config=entity_config,
                                environments={},
                                inherit=inherit if inherit else None
                            ))
                    else:
                        # Fallback: create a generic configuration if no specific type detected
                        configurations.append(ParsedConfiguration(
                            entityType='unknown',
                            name=config_name,
                            config=config_value,
                            environments={},
                            inherit=inherit if inherit else None
                        ))
            
            return ConfigurationParseResult(
                success=True,
                configurations=configurations,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error parsing message config {config_path}: {e}")
            return ConfigurationParseResult(
                success=False,
                errors=[f"Failed to parse message config: {str(e)}"]
            )
    
    async def _parse_search_experience_config(self, config_path: Path) -> ConfigurationParseResult:
        """Parse search experience configuration file"""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            configurations = []
            
            # Parse queries as a single entity with map structure
            # The 'queries' field is a map where keys are entity names and values are definitions
            queries = config_data.get('queries', {})
            if queries:
                # Create a single entity with the queries map
                # The entity name is derived from the filename
                entity_name = config_path.stem  # e.g., "searchExperience" from "searchExperience.json"
                configurations.append(ParsedConfiguration(
                    entityType='queries',
                    name=entity_name,
                    config={'queries': queries},  # Keep the full map structure
                    environments={}
                ))
            
            return ConfigurationParseResult(
                success=True,
                configurations=configurations,
                errors=[],
                warnings=[]
            )
            
        except Exception as e:
            logger.error(f"Error parsing search experience config {config_path}: {e}")
            return ConfigurationParseResult(
                success=False,
                errors=[f"Failed to parse search experience config: {str(e)}"]
            )
    
    def _detect_entity_type(self, config_data: Dict[str, Any]) -> Optional[str]:
        """Detect entity type based on configuration structure"""
        # Check for direct entity types first
        if 'binaryAssets' in config_data:
            return 'binaryAssets'
        elif 'customTransformation' in config_data:
            return 'transformation'
        elif 'access' in config_data and 'defaultAccessType' in config_data.get('access', {}):
            return 'discoveryFeatures'
        
        # Check for preprocessing-based entities
        if 'preProcessing' in config_data:
            preprocessing = config_data['preProcessing']
            if 'imageModeration' in preprocessing:
                return 'imageModeration'
            elif 'textModeration' in preprocessing:
                return 'textModeration'
        
        # Check for moderation configs directly (alternative structure)
        if any(key in config_data for key in ['imageModerationConfig', 'imageModeration']):
            return 'imageModeration'
        elif any(key in config_data for key in ['textModerationConfig', 'textModeration']):
            return 'textModeration'
        
        # Check for transformation without customTransformation wrapper
        if 'outputModel' in config_data or 'inputSpec' in config_data:
            return 'transformation'
        
        return None
    
    def _extract_entity_types(self, config_data: Dict[str, Any]) -> List[str]:
        """Extract all entity types present in configuration"""
        entity_types = []
        
        # Direct entity type mappings
        direct_mappings = {
            'transformation': 'transformation',
            'customTransformation': 'transformation',
            'discoveryFeatures': 'discoveryFeatures',
            'binaryAssets': 'binaryAssets',
            'imageModerationConfig': 'imageModeration',
            'textModerationConfig': 'textModeration',
            'imageModeration': 'imageModeration',
            'textModeration': 'textModeration'
        }
        
        # Check for direct matches
        for key in config_data.keys():
            if key in direct_mappings:
                entity_type = direct_mappings[key]
                if entity_type not in entity_types:
                    entity_types.append(entity_type)
        
        # Check for preprocessing sub-types
        if 'preProcessing' in config_data:
            preprocessing = config_data['preProcessing']
            if 'imageModeration' in preprocessing:
                if 'imageModeration' not in entity_types:
                    entity_types.append('imageModeration')
            if 'textModeration' in preprocessing:
                if 'textModeration' not in entity_types:
                    entity_types.append('textModeration')
        
        # Check for access-based discovery features
        if 'access' in config_data and isinstance(config_data['access'], dict):
            if 'defaultAccessType' in config_data['access']:
                if 'discoveryFeatures' not in entity_types:
                    entity_types.append('discoveryFeatures')
        
        return entity_types