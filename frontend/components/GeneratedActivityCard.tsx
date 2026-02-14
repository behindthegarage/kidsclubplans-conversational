'use client';

import React, { useState } from 'react';
import { Activity } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Sparkles, Blend, Save, Package, Users, 
  Clock, Lightbulb, Wand2, Loader2, CheckCircle2,
  ChevronDown, ChevronUp
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface GeneratedActivityCardProps {
  activity: Activity;
  onSave?: (activity: Activity) => void;
  onBlend?: (activity: Activity) => void;
  onAddToSchedule?: (activity: Activity) => void;
  className?: string;
}

export function GeneratedActivityCard({ 
  activity, 
  onSave, 
  onBlend, 
  onAddToSchedule,
  className 
}: GeneratedActivityCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSave = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsSaving(true);
    setSaveError(null);
    try {
      await onSave?.(activity);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save');
      setTimeout(() => setSaveError(null), 5000);
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddToSchedule = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsAdding(true);
    await onAddToSchedule?.(activity);
    setIsAdding(false);
  };

  const handleBlend = (e: React.MouseEvent) => {
    e.stopPropagation();
    onBlend?.(activity);
  };

  const isGenerated = activity.source === 'generated' || activity.source === 'user_generated';
  const isBlended = activity.source === 'blended';

  return (
    <Card 
      className={cn(
        "mb-3 overflow-hidden border-l-4 shadow-md hover:shadow-lg transition-all cursor-pointer",
        isGenerated ? "border-l-purple-500" : "border-l-primary",
        className
      )}
      onClick={() => setIsExpanded(!isExpanded)}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              {isGenerated && (
                <Sparkles className="w-4 h-4 text-purple-500" />
              )}
              {isBlended && (
                <Blend className="w-4 h-4 text-blue-500" />
              )}
              <CardTitle className="text-base font-semibold leading-tight">
                {activity.title}
              </CardTitle>
            </div>
            
            <div className="flex flex-wrap items-center gap-2 mt-2">
              {isGenerated && (
                <Badge 
                  variant="outline" 
                  className="text-xs bg-purple-100 text-purple-800 border-purple-200"
                >
                  <Wand2 className="w-3 h-3 mr-1" />
                  AI Generated
                </Badge>
              )}
              {isBlended && (
                <Badge 
                  variant="outline" 
                  className="text-xs bg-blue-100 text-blue-800 border-blue-200"
                >
                  <Blend className="w-3 h-3 mr-1" />
                  Blended
                </Badge>
              )}
              {activity.type && (
                <Badge variant="outline" className="text-xs">
                  {activity.type}
                </Badge>
              )}
              {(activity as any).novelty_score && (
                <Badge 
                  variant="outline" 
                  className="text-xs bg-green-100 text-green-800 border-green-200"
                >
                  Novelty: {Math.round((activity as any).novelty_score * 100)}%
                </Badge>
              )}
            </div>
          </div>
          
          <div className="text-muted-foreground">
            {isExpanded ? (
              <ChevronUp className="w-5 h-5" />
            ) : (
              <ChevronDown className="w-5 h-5" />
            )}
          </div>
        </div>
      </CardHeader>

      {/* Always show brief description */}
      <CardContent className="pt-0 pb-3">
        <p className="text-sm text-muted-foreground line-clamp-2">
          {activity.description}
        </p>
        
        {/* Quick info row */}
        <div className="flex flex-wrap gap-4 text-sm mt-2">
          {(activity as any).duration_minutes && (
            <div className="flex items-center gap-1 text-muted-foreground">
              <Clock className="w-4 h-4" />
              {(activity as any).duration_minutes} min
            </div>
          )}
          {activity.target_age && (
            <div className="flex items-center gap-1 text-muted-foreground">
              <Users className="w-4 h-4" />
              {activity.target_age}
            </div>
          )}
        </div>
      </CardContent>

      {/* Expanded details */}
      {isExpanded && (
        <CardContent 
          className="pt-0 space-y-4 border-t bg-muted/30 max-h-[500px] overflow-y-auto" 
          onClick={(e) => e.stopPropagation()}
        >
          {/* Full description */}
          {activity.description && (
            <div className="pt-2">
              <p className="text-sm text-foreground">{activity.description}</p>
            </div>
          )}

          {/* Supplies */}
          {activity.supplies && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Package className="w-4 h-4 text-primary" />
                Supplies Needed
              </div>
              <ul className="text-sm text-muted-foreground pl-6 space-y-1 list-disc list-outside">
                {activity.supplies
                  .split(/[,;]/)
                  .map(s => s.trim())
                  .filter(s => s.length > 0)
                  .map((supply, index) => (
                    <li key={index} className="pl-1">{supply}</li>
                  ))}
              </ul>
            </div>
          )}

          {/* Instructions */}
          {activity.instructions && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Lightbulb className="w-4 h-4 text-primary" />
                Instructions
              </div>
              <ol className="text-sm text-muted-foreground pl-6 space-y-2 list-decimal list-outside">
                {activity.instructions
                  .split(/\d+\./)
                  .map(step => step.trim())
                  .filter(step => step.length > 0)
                  .map((step, index) => (
                    <li key={index} className="pl-1 leading-relaxed">
                      {step.replace(/\.$/, '')}
                    </li>
                  ))}
              </ol>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-2 pt-2">
            {onSave && (
              <Button
                variant="default"
                size="sm"
                onClick={handleSave}
                disabled={isSaving || saved}
                className={cn(
                  "text-xs",
                  saved && "bg-green-600 hover:bg-green-600"
                )}
              >
                {isSaving ? (
                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                ) : saved ? (
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                ) : (
                  <Save className="w-3 h-3 mr-1" />
                )}
                {saved ? 'Saved!' : 'Save to Database'}
              </Button>
            )}

            {onBlend && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleBlend}
                className="text-xs"
              >
                <Blend className="w-3 h-3 mr-1" />
                Blend with Another
              </Button>
            )}

            {onAddToSchedule && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleAddToSchedule}
                disabled={isAdding}
                className="text-xs"
              >
                {isAdding ? (
                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                ) : (
                  <Clock className="w-3 h-3 mr-1" />
                )}
                Add to Schedule
              </Button>
            )}
          </div>

          {/* Error Message */}
          {saveError && (
            <div className="text-xs text-red-500 mt-2 bg-red-50 p-2 rounded">
              ⚠️ {saveError}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
