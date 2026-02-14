'use client';

import React from 'react';
import { Activity } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ChevronDown, Lightbulb, Package, Users, Star } from 'lucide-react';

interface ActivityCardProps {
  activity: Activity;
}

export function ActivityCard({ activity }: ActivityCardProps) {
  const [isOpen, setIsOpen] = React.useState(false);

  const getTypeColor = (type: string | null) => {
    const colors: Record<string, string> = {
      'Physical': 'bg-orange-100 text-orange-800 border-orange-200',
      'STEM': 'bg-blue-100 text-blue-800 border-blue-200',
      'Arts & Crafts': 'bg-purple-100 text-purple-800 border-purple-200',
      'Team Building': 'bg-green-100 text-green-800 border-green-200',
      'Nature': 'bg-emerald-100 text-emerald-800 border-emerald-200',
      'Indoor Game': 'bg-indigo-100 text-indigo-800 border-indigo-200',
      'Outdoor Game': 'bg-sky-100 text-sky-800 border-sky-200',
      'Field Trip': 'bg-amber-100 text-amber-800 border-amber-200',
      'Puzzle': 'bg-pink-100 text-pink-800 border-pink-200',
      'Social-Emotional': 'bg-rose-100 text-rose-800 border-rose-200',
      'Cooking': 'bg-yellow-100 text-yellow-800 border-yellow-200',
      'Music & Movement': 'bg-cyan-100 text-cyan-800 border-cyan-200',
    };
    return colors[type || ''] || 'bg-gray-100 text-gray-800 border-gray-200';
  };

  return (
    <Card className="mb-3 overflow-hidden border-l-4 border-l-primary shadow-sm hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <CardTitle className="text-base font-semibold leading-tight">
              {activity.title}
            </CardTitle>
            <div className="flex flex-wrap items-center gap-2 mt-2">
              {activity.type && (
                <Badge 
                  variant="outline" 
                  className={`text-xs ${getTypeColor(activity.type)}`}
                >
                  {activity.type}
                </Badge>
              )}
              {activity.score && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                  <span>{Math.round(activity.score * 100)}% match</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        {activity.description && (
          <p className="text-sm text-muted-foreground mb-3">{activity.description}</p>
        )}

        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
          <CollapsibleTrigger className="flex items-center gap-1 text-sm text-primary hover:underline w-full">
            <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            {isOpen ? 'Show less' : 'Show more details'}
          </CollapsibleTrigger>

          <CollapsibleContent className="mt-3 space-y-3">
            {activity.development_age_group && (
              <div className="flex items-start gap-2">
                <Users className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium">Age Group</p>
                  <p className="text-sm text-muted-foreground">{activity.development_age_group}</p>
                </div>
              </div>
            )}

            {activity.supplies && (
              <div className="flex items-start gap-2">
                <Package className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium">Supplies Needed</p>
                  <p className="text-sm text-muted-foreground">{activity.supplies}</p>
                </div>
              </div>
            )}

            {activity.instructions && (
              <div className="flex items-start gap-2">
                <Lightbulb className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium">Instructions</p>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{activity.instructions}</p>
                </div>
              </div>
            )}

            {activity.adaptations && (
              <div className="flex items-start gap-2">
                <Users className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium">Adaptations for Different Ages</p>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{activity.adaptations}</p>
                </div>
              </div>
            )}
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
}
