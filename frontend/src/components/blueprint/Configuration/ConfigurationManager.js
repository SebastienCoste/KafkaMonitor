import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../ui/tabs';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { Alert, AlertDescription } from '../../ui/alert';
import { toast } from 'sonner';

// Section components
import MessageConfigurationSection from './sections/MessageConfigurationSection';
import GlobalConfigurationSection from './sections/GlobalConfigurationSection';
import SearchExperienceSection from './sections/SearchExperienceSection';
import BlueprintCNFBuilder from './sections/BlueprintCNFBuilder';
import ConfigurationAPI from './ConfigurationAPI';

// Icons
import { Settings, Database, Search, FileText, RefreshCw, CheckCircle, AlertTriangle, RotateCcw, FlaskConical } from 'lucide-react';

export default function ConfigurationManager() {
  const [entityDefinitions, setEntityDefinitions] = useState(null);
  const [uiConfig, setUiConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [validationResult, setValidationResult] = useState(null);
  const [activeSection, setActiveSection] = useState('message-configs');

  useEffect(() => {
    loadConfiguration();
  }, []);

  const loadConfiguration = async () => {
    setLoading(true);
    try {
      const definitions = await ConfigurationAPI.getEntityDefinitions();
      setEntityDefinitions(definitions);

      // Force parse to ensure Search Experience entities from disk are reflected
      const uiConfigData = await ConfigurationAPI.getUIConfig(true);
      setUiConfig(uiConfigData.config);

      if (uiConfigData.warnings && uiConfigData.warnings.length > 0) {
        uiConfigData.warnings.forEach(warning => toast.warning(warning));
      }

      toast.success('Configuration loaded successfully');
    } catch (error) {
      console.error('Failed to load configuration:', error);
      toast.error(`Failed to load configuration: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // ... rest of file unchanged
}