"""
Blueprint Manager for namespace detection and configuration

Handles blueprint configuration reading and namespace extraction for Redis operations.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class BlueprintManager:
    """Manages blueprint configuration and namespace detection"""
    
    def __init__(self, blueprint_file_manager=None):
        self.blueprint_file_manager = blueprint_file_manager
    
    async def get_current_namespace(self, blueprint_path: str = "blueprint_cnf.json") -> Optional[str]:
        """Extract namespace from blueprint configuration"""
        try:
            if self.blueprint_file_manager and hasattr(self.blueprint_file_manager, 'read_file'):
                # Use the existing blueprint file manager if available
                logger.info(f"Reading blueprint config from file manager: {blueprint_path}")
                try:
                    config_content = await self.blueprint_file_manager.read_file(blueprint_path)
                    config = json.loads(config_content)
                except Exception as e:
                    logger.warning(f"Could not read blueprint config via file manager: {e}")
                    return None
            else:
                # Fallback to direct file reading
                config_file = Path(blueprint_path)
                if not config_file.exists():
                    logger.warning(f"Blueprint config not found: {blueprint_path}")
                    return None
                
                logger.info(f"Reading blueprint config from filesystem: {blueprint_path}")
                with open(config_file, 'r') as f:
                    config = json.load(f)
            
            # Extract namespace from root.namespace
            namespace = config.get("root", {}).get("namespace")
            
            if not namespace:
                # Try alternative paths
                namespace = config.get("namespace")
                if not namespace:
                    logger.warning("No namespace found in blueprint config")
                    return None
            
            logger.info(f"✅ Detected blueprint namespace: {namespace}")
            return namespace
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in blueprint config: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to read blueprint config: {e}")
            return None
    
    async def validate_blueprint_config(self, blueprint_path: str = "blueprint_cnf.json") -> Dict[str, Any]:
        """Validate blueprint configuration exists and is valid"""
        try:
            namespace = await self.get_current_namespace(blueprint_path)
            
            if namespace:
                return {
                    "valid": True,
                    "namespace": namespace,
                    "message": f"Valid blueprint configuration with namespace: {namespace}"
                }
            else:
                return {
                    "valid": False,
                    "namespace": None,
                    "message": "No valid namespace found in blueprint configuration"
                }
                
        except Exception as e:
            return {
                "valid": False,
                "namespace": None,
                "message": f"Error validating blueprint configuration: {str(e)}"
            }
    
    def extract_namespace_from_config_dict(self, config: Dict[str, Any]) -> Optional[str]:
        """Extract namespace from a configuration dictionary"""
        try:
            # Try root.namespace first
            namespace = config.get("root", {}).get("namespace")
            
            # Fallback to direct namespace field
            if not namespace:
                namespace = config.get("namespace")
            
            return namespace
            
        except Exception as e:
            logger.error(f"Error extracting namespace from config: {e}")
            return None