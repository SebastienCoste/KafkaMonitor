// Configuration API integration for Blueprint Creator
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || import.meta.env.REACT_APP_BACKEND_URL;

class ConfigurationAPI {
  static async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    const response = await fetch(url, { ...defaultOptions, ...options });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  // Entity Definitions
  static async getEntityDefinitions() {
    return this.request('/api/blueprint/config/entity-definitions');
  }

  // UI Configuration
  static async getUIConfig() {
    return this.request('/api/blueprint/config/ui-config');
  }

  static async resetUIConfig() {
    return this.request('/api/blueprint/config/reset', {
      method: 'POST'
    });
  }

  // Schema Management
  static async createSchema(data) {
    return this.request('/api/blueprint/config/schemas', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Entity Management
  static async createEntity(data) {
    return this.request('/api/blueprint/config/entities', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  static async updateEntity(entityId, data) {
    return this.request(`/api/blueprint/config/entities/${entityId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  static async deleteEntity(entityId) {
    return this.request(`/api/blueprint/config/entities/${entityId}`, {
      method: 'DELETE',
    });
  }

  // Environment Overrides
  static async setEnvironmentOverride(entityId, data) {
    return this.request(`/api/blueprint/config/entities/${entityId}/environment-overrides`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // File Generation
  static async generateFiles(data) {
    return this.request('/api/blueprint/config/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Validation
  static async validateConfiguration() {
    return this.request('/api/blueprint/config/validate');
  }

  // Generate all files for all schemas
  static async generateAllFiles() {
    try {
      // Get UI config first to get all schemas
      const uiConfig = await this.getUIConfig();
      
      if (!uiConfig.config.schemas || uiConfig.config.schemas.length === 0) {
        return {
          success: false,
          error: 'No schemas found to generate files'
        };
      }

      let totalFilesGenerated = 0;
      const errors = [];

      // Generate files for each schema
      for (const schema of uiConfig.config.schemas) {
        try {
          const result = await this.generateFiles({
            schemaId: schema.id,
            environments: ['DEV', 'TEST', 'INT', 'LOAD', 'PROD'] // Generate for all environments
          });

          if (result.success) {
            totalFilesGenerated += result.files.length;
          } else {
            errors.push(...(result.errors || [`Failed to generate files for schema ${schema.namespace}`]));
          }
        } catch (error) {
          errors.push(`Error generating files for schema ${schema.namespace}: ${error.message}`);
        }
      }

      // Also generate blueprint_cnf.json
      try {
        const blueprintCnfResult = await this.generateBlueprintCNF();
        if (blueprintCnfResult.success) {
          totalFilesGenerated += 1; // Count blueprint_cnf.json as one file
        } else {
          errors.push('Failed to generate blueprint_cnf.json: ' + (blueprintCnfResult.error || 'Unknown error'));
        }
      } catch (error) {
        errors.push('Error generating blueprint_cnf.json: ' + error.message);
      }

      return {
        success: errors.length === 0,
        filesGenerated: totalFilesGenerated,
        error: errors.length > 0 ? errors.join('; ') : null
      };

    } catch (error) {
      return {
        success: false,
        error: error.message,
        filesGenerated: 0
      };
    }
  }

  // Generate blueprint_cnf.json file
  static async generateBlueprintCNF() {
    try {
      // Get UI config to generate blueprint CNF
      const uiConfig = await this.getUIConfig();
      
      if (!uiConfig.config.schemas || uiConfig.config.schemas.length === 0) {
        return {
          success: false,
          error: 'No schemas found to generate blueprint CNF'
        };
      }

      // Build blueprint CNF configuration
      const blueprintConfig = {
        namespace: uiConfig.config.schemas[0]?.namespace || 'com.example.blueprint',
        version: 'git_version',
        owner: 'Blueprint Creator',
        description: 'Generated blueprint configuration',
        schemas: uiConfig.config.schemas.map(schema => ({
          id: schema.id,
          namespace: schema.namespace,
          enabled: true,
          global: [],
          messages: []
        })),
        transformSpecs: [],
        searchExperience: {
          configs: [],
          templates: []
        }
      };

      // Save the blueprint CNF via create-file API
      const backendUrl = process.env.REACT_APP_BACKEND_URL || import.meta.env.REACT_APP_BACKEND_URL;
      const response = await fetch(`${backendUrl}/api/blueprint/create-file`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          path: 'blueprint_cnf.json',
          content: JSON.stringify(blueprintConfig, null, 2),
          overwrite: true
        })
      });

      if (response.ok) {
        const result = await response.json();
        return {
          success: result.success,
          error: result.success ? null : (result.message || 'Failed to save blueprint_cnf.json')
        };
      } else {
        const errorData = await response.json().catch(() => ({}));
        return {
          success: false,
          error: errorData.detail || errorData.message || 'Failed to save blueprint_cnf.json'
        };
      }
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }
}

export default ConfigurationAPI;