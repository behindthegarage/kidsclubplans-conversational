'use client';

import React, { useState } from 'react';
import { Activity } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Sparkles, Blend, Save, Package, Users, 
  Clock, Lightbulb, Wand2, Loader2, CheckCircle2
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
  const [isSaving, setIsSaving] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    await onSave?.(activity);
    setIsSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleAddToSchedule = async () => {
    setIsAdding(true);
    await onAddToSchedule?.(activity);
    setIsAdding(false);
  };

  const isGenerated = activity.source === 'generated' || activity.source === 'user_generated';
  const isBlended = activity.source === 'blended';

  return (
    <Card className={cn(
      "mb-3 overflow-hidden border-l-4 shadow-md hover:shadow-lg transition-all",
      isGenerated ? "border-l-purple-500 bg-purple-50/30" : "border-l-primary",
      className
    )}>
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
        </div>
      </CardHeader>

      <CardContent className="pt-0 space-y-3">
        {activity.description && (
          <p className="text-sm text-muted-foreground">{activity.description}</p>
        )}

        <div className="flex flex-wrap gap-4 text-sm">
          {activity.development_age_group && (
            <div className="flex items-center gap-1 text-muted-foreground">
              <Users className="w-4 h-4" />
              {activity.development_age_group}
            </div>
          )}
          {(activity as any).duration_minutes && (
            <div className="flex items-center gap-1 text-muted-foreground">
              <Clock className="w-4 h-4" />
              {(activity as any).duration_minutes} min
            </div>
          )}
        </div>

        {activity.supplies && (
          <div className="flex items-start gap-2"
          >
            <Package className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
            <p className="text-sm text-muted-foreground">{activity.supplies}</p>
          </div>
        )}

        {activity.instructions && (
          <div className="flex items-start gap-2"
          >
            <Lightbulb className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">
              {activity.instructions}
            </p>
          </div>
        )}

        <div className="flex flex-wrap gap-2 pt-2"
        >
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

          {onSave && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleSave}
              disabled={isSaving || saved}
              className={cn(
                "text-xs",
                saved && "bg-green-100 text-green-800 border-green-200"
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
              onClick={() => onBlend(activity)}
              className="text-xs"
            >
              <Blend className="w-3 h-3 mr-1" />
              Blend with Another
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
