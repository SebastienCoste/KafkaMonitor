import React from 'react';
import { useBlueprintContext } from '../Common/BlueprintContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { Label } from '../../ui/label';
import { Badge } from '../../ui/badge';
import { RadioGroup, RadioGroupItem } from '../../ui/radio-group';
import { Globe } from 'lucide-react';

export default function EnvironmentSelector() {
  const { 
    environments, 
    selectedEnvironment, 
    setSelectedEnvironment 
  } = useBlueprintContext();

  const getEnvironmentDescription = (env) => {
    switch (env.toLowerCase()) {
      case 'dev':
        return 'Development environment for testing';
      case 'test':
        return 'Automated testing environment';
      case 'int':
        return 'Integration testing environment';
      case 'load':
        return 'Load testing environment';
      case 'prod':
        return 'Production environment';
      default:
        return 'Environment for blueprint deployment';
    }
  };

  const getEnvironmentColor = (env) => {
    switch (env.toLowerCase()) {
      case 'dev':
        return 'bg-blue-100 text-blue-800';
      case 'test':
        return 'bg-yellow-100 text-yellow-800';
      case 'int':
        return 'bg-purple-100 text-purple-800';
      case 'load':
        return 'bg-orange-100 text-orange-800';
      case 'prod':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Globe className="h-5 w-5" />
          <span>Target Environment</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <Label className="text-sm font-medium">
            Select the environment where you want to deploy your blueprint:
          </Label>
          
          <RadioGroup
            value={selectedEnvironment}
            onValueChange={setSelectedEnvironment}
            className="space-y-3"
          >
            {environments.map((env) => (
              <div key={env} className="flex items-start space-x-3">
                <RadioGroupItem 
                  value={env} 
                  id={env}
                  className="mt-1"
                />
                <div className="flex-1">
                  <Label 
                    htmlFor={env}
                    className="flex items-center space-x-2 cursor-pointer"
                  >
                    <span className="font-medium">{env}</span>
                    <Badge className={getEnvironmentColor(env)}>
                      {env.toUpperCase()}
                    </Badge>
                  </Label>
                  <p className="text-sm text-gray-600 mt-1">
                    {getEnvironmentDescription(env)}
                  </p>
                </div>
              </div>
            ))}
          </RadioGroup>
          
          {environments.length === 0 && (
            <p className="text-sm text-gray-500 text-center py-4">
              No environments available. Check your configuration.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}