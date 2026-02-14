'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { 
  Database, AlertTriangle, CheckCircle2, 
  Plus, Loader2, TrendingUp, Users, Palette
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface Gap {
  type: string;
  area: string;
  current_count: number;
  severity: 'high' | 'medium' | 'low';
  suggestion: string;
}

interface GapAnalysis {
  gaps_found: number;
  gaps: Gap[];
  coverage_summary: {
    age_groups: Record<string, number>;
    themes: Record<string, number>;
    low_prep: number;
  };
  recommendations: string[];
}

interface GapAnalysisViewProps {
  analysis?: GapAnalysis;
  isLoading?: boolean;
  onRefresh?: () => void;
  onGenerateSuggestion?: (suggestion: string) => void;
  className?: string;
}

const severityColors = {
  high: 'bg-red-100 text-red-800 border-red-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-blue-100 text-blue-800 border-blue-200',
};

const severityIcons = {
  high: <AlertTriangle className="w-4 h-4 text-red-500" />,
  medium: <TrendingUp className="w-4 h-4 text-yellow-500" />,
  low: <CheckCircle2 className="w-4 h-4 text-blue-500" />,
};

export function GapAnalysisView({ 
  analysis, 
  isLoading = false,
  onRefresh,
  onGenerateSuggestion,
  className
}: GapAnalysisViewProps) {
  if (isLoading) {
    return (
      <Card className={cn("w-full", className)}>
        <CardContent className="py-12">
          <div className="flex flex-col items-center justify-center text-center space-y-4">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
            <p className="text-muted-foreground">Analyzing your activity database...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!analysis) {
    return (
      <Card className={cn("w-full", className)}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5 text-primary" />
            Database Gap Analysis
          </CardTitle>
        </CardHeader>
        <CardContent className="py-8 text-center">
          <p className="text-muted-foreground mb-4">
            Discover what's missing from your activity database
          </p>
          {onRefresh && (
            <Button onClick={onRefresh}>
              <Database className="w-4 h-4 mr-2" />
              Analyze Database
            </Button>
          )}
        </CardContent>
      </Card>
    );
  }

  const { gaps_found, gaps, coverage_summary, recommendations } = analysis;

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5 text-primary" />
            Database Gap Analysis
          </CardTitle>
          {onRefresh && (
            <Button variant="outline" size="sm" onClick={onRefresh}>
              Refresh
            </Button>
          )}
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          Found {gaps_found} gaps in your activity coverage
        </p>
      </CardHeader>

      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Users className="w-4 h-4" />
                Age Group Coverage
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {Object.entries(coverage_summary.age_groups).map(([age, count]) => (
                <div key={age} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>{age}</span>
                    <span className={cn(
                      count < 5 ? "text-red-600" : "text-green-600"
                    )}>{count} activities</span>
                  </div>
                  <Progress value={Math.min(count * 10, 100)} className="h-2" />
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Palette className="w-4 h-4" />
                Theme Coverage
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {Object.entries(coverage_summary.themes)
                .slice(0, 6)
                .map(([theme, count]) => (
                <div key={theme} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="capitalize">{theme}</span>
                    <span className={cn(
                      count < 3 ? "text-red-600" : "text-green-600"
                    )}>{count}</span>
                  </div>
                  <Progress value={Math.min(count * 20, 100)} className="h-2" />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-3">
          <h4 className="font-medium flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            Priority Gaps
          </h4>
          
          <div className="space-y-2">
            {gaps.slice(0, 5).map((gap, index) => (
              <Card key={index} className="border-l-4 border-l-transparent">
                <CardContent className="p-3 flex items-start gap-3">
                  {severityIcons[gap.severity]}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Badge 
                        variant="outline" 
                        className={cn("text-xs", severityColors[gap.severity])}
                      >
                        {gap.severity}
                      </Badge>
                      <span className="text-sm font-medium capitalize">
                        {gap.type.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {gap.suggestion}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Current: {gap.current_count} activities
                    </p>
                  </div>
                  
                  {onGenerateSuggestion && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onGenerateSuggestion(gap.suggestion)}
                      className="shrink-0"
                    >
                      <Plus className="w-4 h-4" />
                    </Button>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {recommendations.length > 0 && (
          <div className="bg-muted rounded-lg p-4">
            <h4 className="font-medium mb-2">Quick Actions</h4>
            <div className="flex flex-wrap gap-2">
              {recommendations.slice(0, 3).map((rec, index) => (
                <Button
                  key={index}
                  variant="secondary"
                  size="sm"
                  onClick={() => onGenerateSuggestion?.(rec)}
                  className="text-xs"
                >
                  <Plus className="w-3 h-3 mr-1" />
                  {rec.replace('Priority: ', '')}
                </Button>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
