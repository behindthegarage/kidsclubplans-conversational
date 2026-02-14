'use client';

import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { SupplyPicker } from './SupplyPicker';
import { BlendInterface } from './BlendInterface';
import { GapAnalysisView } from './GapAnalysisView';
import { Sparkles, Blend, Database, Wand2 } from 'lucide-react';

interface Phase4ToolsPanelProps {
  onSupplyGenerate: (supplies: string[], ageGroup: string) => void;
  onBlend: (activities: string[], focus: string) => void;
  onGapAnalysis: () => void;
  onGenerateFromSuggestion: (suggestion: string) => void;
  gapAnalysis?: {
    gaps_found: number;
    gaps: any[];
    coverage_summary: any;
    recommendations: string[];
  };
  isLoading?: {
    supply?: boolean;
    blend?: boolean;
    gap?: boolean;
  };
  className?: string;
}

export function Phase4ToolsPanel({
  onSupplyGenerate,
  onBlend,
  onGapAnalysis,
  onGenerateFromSuggestion,
  gapAnalysis,
  isLoading = {},
  className
}: Phase4ToolsPanelProps) {
  const [activeTab, setActiveTab] = useState('supplies');

  return (
    <div className={className}>
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="supplies" className="text-xs">
            <Wand2 className="w-3 h-3 mr-1" />
            Supplies
          </TabsTrigger>
          <TabsTrigger value="blend" className="text-xs">
            <Blend className="w-3 h-3 mr-1" />
            Blend
          </TabsTrigger>
          <TabsTrigger value="gaps" className="text-xs">
            <Database className="w-3 h-3 mr-1" />
            Gaps
          </TabsTrigger>
        </TabsList>

        <TabsContent value="supplies" className="mt-4">
          <SupplyPicker
            onGenerate={onSupplyGenerate}
            isGenerating={isLoading.supply}
          />
        </TabsContent>

        <TabsContent value="blend" className="mt-4">
          <BlendInterface
            onBlend={onBlend}
            isBlending={isLoading.blend}
          />
        </TabsContent>

        <TabsContent value="gaps" className="mt-4">
          <GapAnalysisView
            analysis={gapAnalysis}
            isLoading={isLoading.gap}
            onRefresh={onGapAnalysis}
            onGenerateSuggestion={onGenerateFromSuggestion}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
