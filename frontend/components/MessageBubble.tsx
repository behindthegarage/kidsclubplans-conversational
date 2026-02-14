'use client';

import React, { useState, useMemo } from 'react';
import { Message, Activity } from '@/lib/api';
import { ActivityCard } from './ActivityCard';
import { GeneratedActivityCard } from './GeneratedActivityCard';
import { ToolCallDisplay } from './ToolCallDisplay';
import { User, Bot, Loader2, Sparkles, Save, CheckSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface MessageBubbleProps {
  message: Message;
  onSaveActivity?: (activity: any) => void;
  onBlendActivity?: (activity: any) => void;
  onSaveMultiple?: (activities: any[]) => void;
}

// Parse activities from AI text responses
function parseActivitiesFromContent(content: string): Activity[] {
  const activities: Activity[] = [];
  
  // Look for activity patterns in the text
  // Pattern: **Title:** or ### Activity Details: or similar headers
  const activityRegex = /(?:###\s*Activity\s*Details:?|(?:^|\n)\s*[-*]\s*\*\*Title:\*\*|\*\*Title:\*\*)/gi;
  const matches = Array.from(content.matchAll(activityRegex));
  
  for (let i = 0; i < matches.length; i++) {
    const start = matches[i].index || 0;
    const end = i < matches.length - 1 ? matches[i + 1].index : content.length;
    const section = content.slice(start, end || undefined);
    
    // Extract fields using regex patterns
    const titleMatch = section.match(/\*\*Title:?\*\*\s*([^\n*]+)/i) || 
                       section.match(/titled\s+["']([^"']+)["']/i) ||
                       section.match(/(?:^|\n)\s*\*\*([^*]+)\*\*\s*(?:\n|$)/);
    
    const durationMatch = section.match(/\*\*Duration:?\*\*\s*([^\n*]+)/i) ||
                          section.match(/(\d+)\s*minutes?/i);
    
    const ageMatch = section.match(/\*\*(?:Target\s+)?Age\s*Group:?\*\*\s*([^\n*]+)/i) ||
                     section.match(/aged?\s+([\d\-\s]+years?\s*old?)/i);
    
    const suppliesMatch = section.match(/\*\*(?:Supplies\s*(?:Needed)?:?)\*\*\s*([^#]+?)(?=\*\*|$|\n\s*\*\*)/i) ||
                          section.match(/(?:supplies|materials):\s*([^#.]+)/i);
    
    const settingMatch = section.match(/\*\*Setting:?\*\*\s*([^\n*]+)/i) ||
                         section.match(/\*\*(Indoor|Outdoor|Indoor\/Outdoor)\*\*/i);
    
    const instructionsMatch = section.match(/\*\*Instructions:?\*\*\s*([\s\S]+?)(?=\*\*|$)/i) ||
                              section.match(/(?:Instructions|Steps):\s*([\s\S]+?)(?=\n\n|\*\*|$)/i);
    
    const descriptionMatch = section.match(/\*\*Description:?\*\*\s*([\s\S]+?)(?=\*\*|$)/i);
    
    if (titleMatch) {
      const title = titleMatch[1].trim();
      const durationText = durationMatch ? durationMatch[1].trim() : '';
      const duration = parseInt(durationText) || 30;
      
      const activity = {
        id: -(Date.now() + i),
        title: title,
        description: descriptionMatch ? descriptionMatch[1].trim() : section.slice(0, 200).trim(),
        type: 'Activity' as string | null,
        duration_minutes: duration,
        target_age_group: ageMatch ? ageMatch[1].trim() : null,
        supplies: suppliesMatch ? suppliesMatch[1].trim() : null,
        indoor_outdoor: settingMatch ? settingMatch[1].toLowerCase() : 'either',
        instructions: instructionsMatch ? instructionsMatch[1].trim() : null,
        source: 'parsed' as string | null,
        generated: true,
      };
      
      activities.push(activity);
    }
  }
  
  return activities;
}

export function MessageBubble({ message, onSaveActivity, onBlendActivity, onSaveMultiple }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [selectedActivities, setSelectedActivities] = useState<Set<string>>(new Set());
  const [isSelectionMode, setIsSelectionMode] = useState(false);

  // Separate generated activities from regular ones
  const regularActivities = message.activities?.filter(
    a => a.source !== 'generated' && a.source !== 'user_generated' && a.source !== 'blended' && !a.generated
  ) || [];
  
  const generatedActivities = message.activities?.filter(
    a => a.source === 'generated' || a.source === 'user_generated' || a.source === 'blended' || a.generated
  ) || [];
  
  // Parse activities from message content if no structured activities exist
  const parsedActivities = useMemo(() => {
    if (!isUser && generatedActivities.length === 0 && regularActivities.length === 0 && message.content) {
      return parseActivitiesFromContent(message.content);
    }
    return [];
  }, [message.content, generatedActivities.length, regularActivities.length, isUser]);
  
  // Combine generated and parsed activities
  const allGeneratedActivities = [...generatedActivities, ...parsedActivities];

  const handleSelectActivity = (activity: Activity, selected: boolean) => {
    const id = activity.id || activity.title;
    if (!id) return;
    setSelectedActivities(prev => {
      const newSet = new Set<string>(prev);
      if (selected) {
        newSet.add(id as string);
      } else {
        newSet.delete(id as string);
      }
      return newSet;
    });
  };

  const handleSaveSelected = async () => {
    const activitiesToSave = allGeneratedActivities.filter(a => 
      selectedActivities.has(String(a.id || a.title))
    );
    
    for (const activity of activitiesToSave) {
      await onSaveActivity?.(activity);
    }
    
    setSelectedActivities(new Set());
    setIsSelectionMode(false);
  };

  const hasGeneratedActivities = allGeneratedActivities.length > 0;
  const selectedCount = selectedActivities.size;

  return (
    <div
      className={cn(
        'flex gap-3 mb-4 animate-fade-in',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center shrink-0',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-secondary text-secondary-foreground'
        )}
      >
        {isUser ? (
          <User className="w-4 h-4" />
        ) : message.isStreaming ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Bot className="w-4 h-4" />
        )}
      </div>

      {/* Message Content */}
      <div
        className={cn(
          'flex flex-col max-w-[80%]',
          isUser ? 'items-end' : 'items-start'
        )}
      >
        {/* Text Bubble */}
        <div
          className={cn(
            'px-4 py-2.5 rounded-2xl text-sm leading-relaxed',
            isUser
              ? 'bg-primary text-primary-foreground rounded-tr-sm'
              : 'bg-muted text-foreground rounded-tl-sm'
          )}
        >
          {message.content}
          {message.isStreaming && (
            <span className="inline-block w-1.5 h-4 ml-1 bg-current animate-pulse-opacity rounded-sm" />
          )}
        </div>

        {/* Tool Calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="w-full mt-2">
            <ToolCallDisplay toolCalls={message.toolCalls} />
          </div>
        )}

        {/* Generated Activities */}
        {allGeneratedActivities.length > 0 && (
          <div className="w-full mt-3 space-y-2">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-purple-500" />
              <p className="text-xs font-medium text-purple-600">
                {parsedActivities.length > 0 && generatedActivities.length === 0 ? 'Activity Details' : 'AI-Generated Activities'}
              </p>
            </div>
            {allGeneratedActivities.map((activity, idx) => (
              <GeneratedActivityCard
                key={`gen-${activity.id || idx}`}
                activity={activity}
                onSave={onSaveActivity}
                onBlend={onBlendActivity}
              />
            ))}
          </div>
        )}

        {/* Regular Activity Cards */}
        {regularActivities.length > 0 && (
          <div className="w-full mt-3 space-y-2">
            <p className="text-xs font-medium text-muted-foreground mb-2">
              Found activities:
            </p>
            {regularActivities.map((activity) => (
              <ActivityCard key={activity.id} activity={activity} />
            ))}
          </div>
        )}

        {/* Timestamp */}
        <span className="text-xs text-muted-foreground mt-1">
          {message.timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>
    </div>
  );
}
