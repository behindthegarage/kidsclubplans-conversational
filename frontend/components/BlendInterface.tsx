'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  Blend, Plus, X, Sparkles, Loader2,
  Target, Lightbulb
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface BlendInterfaceProps {
  onBlend: (activities: string[], focus: string) => void;
  isBlending?: boolean;
  className?: string;
}

const BLEND_FOCUSES = [
  { value: 'balanced', label: 'Balanced', description: 'Best of both worlds' },
  { value: 'physical', label: 'Physical', description: 'Emphasize movement' },
  { value: 'creative', label: 'Creative', description: 'Artistic expression' },
  { value: 'educational', label: 'Educational', description: 'Learning focus' },
  { value: 'social', label: 'Social', description: 'Collaboration' },
];

const EXAMPLE_BLENDS = [
  ['dodgeball', 'storytelling'],
  ['art project', 'science experiment'],
  ['tag', 'memory game'],
  ['building blocks', 'treasure hunt']
];

export function BlendInterface({ 
  onBlend, 
  isBlending = false,
  className 
}: BlendInterfaceProps) {
  const [activities, setActivities] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [focus, setFocus] = useState('balanced');

  const addActivity = () => {
    if (inputValue.trim() && !activities.includes(inputValue.trim())) {
      setActivities([...activities, inputValue.trim()]);
      setInputValue('');
    }
  };

  const removeActivity = (activity: string) => {
    setActivities(activities.filter(a => a !== activity));
  };

  const useExample = (example: string[]) => {
    setActivities(example);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addActivity();
    }
  };

  const handleBlend = () => {
    if (activities.length >= 2) {
      onBlend(activities, focus);
    }
  };

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Blend className="w-5 h-5 text-primary" />
          Blend Activities
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder="Enter activity name and press Enter..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1"
            disabled={isBlending}
          />
          <Button 
            onClick={addActivity}
            disabled={!inputValue.trim() || isBlending}
            variant="outline"
          >
            <Plus className="w-4 h-4" />
          </Button>
        </div>

        <div className="flex flex-wrap gap-2">
          {activities.map((activity, index) => (
            <React.Fragment key={activity}>
              {index > 0 && (
                <span className="text-muted-foreground self-center">+</span>
              )}
              <Badge 
                variant="secondary"
                className="px-3 py-1.5 text-sm"
              >
                {activity}
                <button
                  onClick={() => removeActivity(activity)}
                  className="ml-2 hover:text-destructive"
                  disabled={isBlending}
                >
                  <X className="w-3 h-3 inline" />
                </button>
              </Badge>
            </React.Fragment>
          ))}
        </div>

        {activities.length < 2 && (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">Try these examples:</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_BLENDS.map((example) => (
                <Button
                  key={example.join('+')}
                  variant="ghost"
                  size="sm"
                  onClick={() => useExample(example)}
                  disabled={isBlending}
                  className="text-xs h-auto py-1"
                >
                  {example[0]} + {example[1]}
                </Button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-2">
          <p className="text-sm text-muted-foreground flex items-center gap-1">
            <Target className="w-4 h-4" />
            Blend focus:
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
            {BLEND_FOCUSES.map((f) => (
              <Button
                key={f.value}
                variant={focus === f.value ? "default" : "outline"}
                size="sm"
                onClick={() => setFocus(f.value)}
                disabled={isBlending}
                className={cn(
                  "text-xs h-auto py-2 flex flex-col items-center",
                  focus === f.value && "ring-2 ring-primary"
                )}
              >
                <span className="font-medium">{f.label}</span>
                <span className="text-[10px] opacity-70">{f.description}</span>
              </Button>
            ))}
          </div>
        </div>

        <Button
          onClick={handleBlend}
          disabled={activities.length < 2 || isBlending}
          className="w-full"
        >
          {isBlending ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Blending activities...
            </>
          ) : (
            <>
              <Blend className="w-4 h-4 mr-2" />
              Blend {activities.length} Activity{activities.length !== 1 ? 'ies' : 'y'}
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
