'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  Package, Plus, X, Sparkles, Loader2
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface SupplyPickerProps {
  onGenerate: (supplies: string[], ageGroup: string) => void;
  isGenerating?: boolean;
  className?: string;
}

const COMMON_SUPPLIES = [
  'paper plates', 'string', 'balloons', 'markers', 'crayons',
  'scissors', 'glue', 'tape', 'paper', 'cardboard',
  'paint', 'brushes', 'playdough', 'blocks', 'balls'
];

const AGE_GROUPS = [
  '5-6 years', '7-8 years', '9-10 years', '11-12 years'
];

export function SupplyPicker({ 
  onGenerate, 
  isGenerating = false,
  className 
}: SupplyPickerProps) {
  const [supplies, setSupplies] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [ageGroup, setAgeGroup] = useState('5-6 years');

  const addSupply = () => {
    if (inputValue.trim() && !supplies.includes(inputValue.trim())) {
      setSupplies([...supplies, inputValue.trim()]);
      setInputValue('');
    }
  };

  const removeSupply = (supply: string) => {
    setSupplies(supplies.filter(s => s !== supply));
  };

  const addCommonSupply = (supply: string) => {
    if (!supplies.includes(supply)) {
      setSupplies([...supplies, supply]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addSupply();
    }
  };

  const handleGenerate = () => {
    if (supplies.length > 0) {
      onGenerate(supplies, ageGroup);
    }
  };

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Package className="w-5 h-5 text-primary" />
          What supplies do you have?
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder="Type a supply and press Enter..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1"
            disabled={isGenerating}
          />
          <Button 
            onClick={addSupply}
            disabled={!inputValue.trim() || isGenerating}
            variant="outline"
          >
            <Plus className="w-4 h-4" />
          </Button>
        </div>

        <div className="flex flex-wrap gap-2">
          {supplies.map((supply) => (
            <Badge 
              key={supply}
              variant="secondary"
              className="px-2 py-1 text-sm"
            >
              {supply}
              <button
                onClick={() => removeSupply(supply)}
                className="ml-1 hover:text-destructive"
                disabled={isGenerating}
              >
                <X className="w-3 h-3 inline" />
              </button>
            </Badge>
          ))}
        </div>

        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">Common supplies:</p>
          <div className="flex flex-wrap gap-1">
            {COMMON_SUPPLIES.map((supply) => (
              <Button
                key={supply}
                variant="ghost"
                size="sm"
                onClick={() => addCommonSupply(supply)}
                disabled={supplies.includes(supply) || isGenerating}
                className={cn(
                  "text-xs h-7",
                  supplies.includes(supply) && "opacity-50 cursor-not-allowed"
                )}
              >
                {supply}
              </Button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">Age group:</p>
          <div className="flex flex-wrap gap-1">
            {AGE_GROUPS.map((age) => (
              <Button
                key={age}
                variant={ageGroup === age ? "default" : "outline"}
                size="sm"
                onClick={() => setAgeGroup(age)}
                disabled={isGenerating}
                className="text-xs"
              >
                {age}
              </Button>
            ))}
          </div>
        </div>

        <Button
          onClick={handleGenerate}
          disabled={supplies.length === 0 || isGenerating}
          className="w-full"
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Generating activities...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 mr-2" />
              Generate Activities from Supplies
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
