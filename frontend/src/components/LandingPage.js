import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';

// Icons
import { 
  Activity, 
  Server, 
  FolderOpen, 
  ArrowRight, 
  Zap, 
  Shield, 
  BarChart3,
  Map,
  MapPin,
  Settings,
  Eye,
  Route,
  Compass
} from 'lucide-react';

const LandingPage = ({ onNavigate, availableTabs }) => {
  const features = [
    {
      id: 'traces',
      icon: Route,
      title: 'Trace Viewer',
      description: 'Follow the footsteps through Kafka corridors and reveal every message\'s journey',
      features: ['Footstep Tracking', 'Corridor Statistics', 'Movement Patterns', 'Live Surveillance'],
      color: 'bg-amber-600',
      enabled: availableTabs?.trace_viewer?.enabled
    },
    {
      id: 'grpc',
      icon: Eye,
      title: 'gRPC Integration',
      description: 'Unlock secret passages and discover hidden gRPC service entrances',
      features: ['Passage Discovery', 'Secret Testing', 'Map Updates', 'Portal Switching'],
      color: 'bg-emerald-600',
      enabled: availableTabs?.grpc_integration?.enabled
    },
    {
      id: 'blueprint',
      icon: Compass,
      title: 'Blueprint Creator',
      description: 'Chart new territories and guard the Redis chamber secrets',
      features: ['Territory Mapping', 'Chamber Verification', 'Multiple Maps', 'Enchanted Syntax'],
      color: 'bg-indigo-600',
      enabled: availableTabs?.blueprint_creator?.enabled
    }
  ];

  const stats = [
    { label: 'Active Spells', value: features.filter(f => f.enabled).length, icon: Zap },
    { label: 'Territories', value: 'Multi', icon: MapPin },
    { label: 'Protection', value: 'Enchanted', icon: Shield },
    { label: 'Tracking', value: 'Live', icon: Eye },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Hero Section */}
      <div className="relative overflow-hidden bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center">
            <div className="flex justify-center mb-6">
              <div className="p-4 bg-amber-700 rounded-full shadow-lg border-2 border-amber-600">
                <Map className="h-12 w-12 text-amber-100" />
              </div>
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl md:text-6xl">
              <span className="block text-amber-800">Marauder's</span>
              <span className="block text-amber-700">Map</span>
            </h1>
            <p className="mt-4 text-lg font-medium text-amber-700 italic">
              "I solemnly swear I am up to no good"
            </p>
            <p className="mt-6 max-w-md mx-auto text-lg text-gray-600 sm:text-xl md:mt-8 md:max-w-3xl">
              Reveal the hidden paths of Kafka traces, gRPC integrations, and blueprint secrets. Track every movement, discover every connection.
            </p>
            
            {/* Quick Stats */}
            <div className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-4">
              {stats.map((stat, index) => (
                <div key={index} className="bg-white rounded-lg shadow p-4 border">
                  <div className="flex items-center justify-center mb-2">
                    <stat.icon className="h-6 w-6 text-blue-600" />
                  </div>
                  <div className="text-2xl font-bold text-gray-900">{stat.value}</div>
                  <div className="text-sm text-gray-500">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            Enchanted Tools
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Master the magical arts of system monitoring and service discovery with these powerful enchantments
          </p>
        </div>

        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
          {features.map((feature) => {
            const IconComponent = feature.icon;
            
            if (!feature.enabled) {
              return null; // Don't show disabled features
            }
            
            return (
              <Card key={feature.id} className="relative overflow-hidden group hover:shadow-lg transition-shadow duration-300">
                <div className={`absolute top-0 left-0 w-full h-1 ${feature.color}`}></div>
                <CardHeader className="pb-4">
                  <div className="flex items-center space-x-3">
                    <div className={`p-2 rounded-lg ${feature.color} bg-opacity-10`}>
                      <IconComponent className={`h-6 w-6 text-current`} />
                    </div>
                    <div>
                      <CardTitle className="text-xl">{feature.title}</CardTitle>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-gray-600 mb-4 leading-relaxed">
                    {feature.description}
                  </CardDescription>
                  
                  <div className="space-y-2 mb-6">
                    {feature.features.map((item, index) => (
                      <div key={index} className="flex items-center text-sm text-gray-600">
                        <div className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-2"></div>
                        {item}
                      </div>
                    ))}
                  </div>
                  
                  <Button 
                    onClick={() => onNavigate(feature.id)}
                    className="w-full group-hover:shadow-md transition-shadow"
                    variant="outline"
                  >
                    Get Started
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Call to Action Section */}
      <div className="bg-gradient-to-r from-amber-800 to-amber-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center">
            <h2 className="text-3xl font-bold mb-4">
              Ready to Explore?
            </h2>
            <p className="text-xl text-amber-100 mb-8 max-w-2xl mx-auto">
              Choose your path and begin your journey through the hidden corridors of your systems
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              {features.filter(f => f.enabled).map((feature) => (
                <Button
                  key={feature.id}
                  onClick={() => onNavigate(feature.id)}
                  variant="secondary"
                  size="lg"
                  className="bg-white text-amber-800 hover:bg-amber-50"
                >
                  <feature.icon className="mr-2 h-5 w-5" />
                  {feature.title}
                </Button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-gray-50 border-t">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-500">
            <div className="flex items-center justify-center mb-2">
              <Database className="h-5 w-5 mr-2" />
              <span className="font-medium">Kafka Monitor Dashboard</span>
            </div>
            <p className="text-sm">
              Comprehensive platform for Kafka monitoring, gRPC integration, and blueprint management
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;