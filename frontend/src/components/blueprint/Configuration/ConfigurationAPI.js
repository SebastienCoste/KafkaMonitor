// Configuration API integration for Blueprint Creator
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || import.meta.env.REACT_APP_BACKEND_URL;

class ConfigurationAPI {
  static async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const defaultOptions = {
      headers: { 'Content-Type': 'application/json', ...options.headers },
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

  // UI Configuration (force parse optional)
  static async getUIConfig(force = false) {
    const q = force ? '?force=true' : '';
    return this.request(`/api/blueprint/config/ui-config${q}`);
  }

  static async resetUIConfig() {
    return this.request('/api/blueprint/config/reset', { method: 'POST' });
  }

  // Schema Management
  static async createSchema(data) {
    return this.request('/api/blueprint/config/schemas', { method: 'POST', body: JSON.stringify(data) });
  }

  // Entity Management
  static async createEntity(data) {
    return this.request('/api/blueprint/config/entities', { method: 'POST', body: JSON.stringify(data) });
  }
  static async updateEntity(entityId, data) {
    return this.request(`/api/blueprint/config/entities/${entityId}`, { method: 'PUT', body: JSON.stringify(data) });
  }
  static async deleteEntity(entityId) {
    return this.request(`/api/blueprint/config/entities/${entityId}`, { method: 'DELETE' });
  }

  // Environment Overrides
  static async setEnvironmentOverride(entityId, data) {
    return this.request(`/api/blueprint/config/entities/${entityId}/environment-overrides`, { method: 'POST', body: JSON.stringify(data) });
  }

  // File Generation
  static async generateFiles(data) {
    return this.request('/api/blueprint/config/generate', { method: 'POST', body: JSON.stringify(data) });
  }

  // Validation
  static async validateConfiguration() {
    return this.request('/api/blueprint/config/validate');
  }

  // Generate all files for all schemas
  static async generateAllFiles() {
    return this.request('/api/blueprint/config/generate-all', { method: 'POST' });
  }

  static async generateBlueprintCNF() {
    return this.request('/api/blueprint/config/generate-cnf', { method: 'POST' });
  }
}

export default ConfigurationAPI;