'use client';

import React from 'react';
import { ToolCall } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { 
  Cloud, Search, Sparkles, Calendar, 
  Blend, Package, Database, Save, 
  Loader2, CheckCircle2 
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ToolCallDisplayProps {
  toolCalls: ToolCall[];
  className?: string;
}

const toolIcons: Record<string, React.ReactNode> = {
  check_weather: <Cloud className="w-4 h-4" />,
  search_activities: <Search className="w-4 h-4" />,
  search_activities_with_constraints: <Search className="w-4 h-4" />,
  generate_activity: <Sparkles className="w-4 h-4" />,
  generate_schedule: <Calendar className="w-4 h-4" />,
  get_user_preferences: <CheckCircle2 className="w-4 h-4" />,
  blend_activities: <Blend className="w-4 h-4" />,
  analyze_database_gaps: <Database className="w-4 h-4" />,
  generate_from_supplies: <Package className="w-4 h-4" />,
  save_activity: <Save className="w-4 h-4" />,
};

const toolLabels: Record<string, string> = {
  check_weather: 'Checking weather',
  search_activities: 'Searching activities',
  search_activities_with_constraints: 'Searching with filters',
  generate_activity: 'Generating activity',
  generate_schedule: 'Building schedule',
  get_user_preferences: 'Loading your preferences',
  blend_activities: 'Blending activities',
  analyze_database_gaps: 'Analyzing database',
  generate_from_supplies: 'Creating from supplies',
  save_activity: 'Saving activity',
};

export function ToolCallDisplay({ toolCalls, className }: ToolCallDisplayProps) {
  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className={cn("space-y-2", className)}>
      {toolCalls.map((toolCall, index) => {
        const icon = toolIcons[toolCall.name] || <Loader2 className="w-4 h-4" />;
        const label = toolLabels[toolCall.name] || toolCall.name;

        return (
          <Card 
            key={`${toolCall.name}-${index}`}
            className="p-2 bg-muted/50 border-muted flex items-center gap-2 animate-in fade-in slide-in-from-left-2 duration-300"
          >
            <div className="text-primary">
              {icon}
            </div>
            <span className="text-sm text-muted-foreground">
              {label}
            </span>
            {toolCall.result !== undefined && (
              <CheckCircle2 className="w-4 h-4 text-green-500 ml-auto" />
            )}
          </Card>
        );
      })}
    </div>
  );
}
