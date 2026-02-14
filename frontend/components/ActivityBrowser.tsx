'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Search, 
  Filter, 
  Plus, 
  Calendar, 
  Clock, 
  Users, 
  Package,
  ClipboardList,
  Sparkles,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface Activity {
  id: string;
  title: string;
  description: string;
  type: string;
  development_age_group: string;
  supplies: string;
  instructions?: string;
  duration_minutes?: number;
  indoor_outdoor?: string;
  score?: number;
}

interface ActivityBrowserProps {
  onAddToSchedule?: (activity: Activity) => void;
  onAddToWeek?: (activity: Activity, weekNumber: number) => void;
}

const THEME_SUGGESTIONS = [
  'Space Exploration',
  'Under the Sea',
  'Superheroes',
  'Dinosaurs',
  'Sports Week',
  'Arts & Crafts',
  'Science Lab',
  'Nature Week',
  'Around the World',
  'Cooking Week',
];

const AGE_GROUPS = ['5-6 years', '7-8 years', '9-10 years', '11-12 years'];
const ACTIVITY_TYPES = ['Physical', 'STEM', 'Arts & Crafts', 'Team Building', 'Nature', 'Cooking', 'Music & Movement'];

export function ActivityBrowser({ onAddToSchedule, onAddToWeek }: ActivityBrowserProps) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);
  const [filters, setFilters] = useState({
    ageGroup: '',
    type: '',
    indoorOutdoor: '',
    maxDuration: 120,
  });
  const [showFilters, setShowFilters] = useState(false);
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null);

  const searchActivities = useCallback(async (query: string) => {
    if (!query.trim()) {
      setActivities([]);
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/activities/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          query,
          age_group: filters.ageGroup || undefined,
          activity_type: filters.type || undefined,
          indoor_outdoor: filters.indoorOutdoor || undefined,
          max_duration: filters.maxDuration,
          limit: 20,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setActivities(data.activities || []);
      }
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      if (searchQuery) {
        searchActivities(searchQuery);
      }
    }, 300);
    return () => clearTimeout(timeout);
  }, [searchQuery, searchActivities]);

  const handleThemeClick = (theme: string) => {
    setSearchQuery(theme);
    searchActivities(theme);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b p-4 space-y-4">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search by theme, activity name, or supplies..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className={cn(showFilters && 'bg-muted')}
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
          </Button>
        </div>

        {/* Theme Pills */}
        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-muted-foreground py-1">Popular themes:</span>
          {THEME_SUGGESTIONS.map((theme) => (
            <button
              key={theme}
              onClick={() => handleThemeClick(theme)}
              className="text-xs px-3 py-1 rounded-full bg-muted hover:bg-muted/80 transition-colors"
            >
              {theme}
            </button>
          ))}
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="flex flex-wrap gap-3 p-3 bg-muted/50 rounded-lg">
            <select
              value={filters.ageGroup}
              onChange={(e) => setFilters({ ...filters, ageGroup: e.target.value })}
              className="px-3 py-2 text-sm border rounded-md bg-background"
            >
              <option value="">Any Age</option>
              {AGE_GROUPS.map((age) => (
                <option key={age} value={age}>{age}</option>
              ))}
            </select>

            <select
              value={filters.type}
              onChange={(e) => setFilters({ ...filters, type: e.target.value })}
              className="px-3 py-2 text-sm border rounded-md bg-background"
            >
              <option value="">Any Type</option>
              {ACTIVITY_TYPES.map((type) => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>

            <select
              value={filters.indoorOutdoor}
              onChange={(e) => setFilters({ ...filters, indoorOutdoor: e.target.value })}
              className="px-3 py-2 text-sm border rounded-md bg-background"
            >
              <option value="">Any Location</option>
              <option value="indoor">Indoor</option>
              <option value="outdoor">Outdoor</option>
              <option value="either">Either</option>
            </select>

            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Max duration:</span>
              <input
                type="range"
                min="15"
                max="120"
                step="15"
                value={filters.maxDuration}
                onChange={(e) => setFilters({ ...filters, maxDuration: parseInt(e.target.value) })}
                className="w-32"
              />
              <span className="text-sm">{filters.maxDuration}min</span>
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      <div className="flex-1 flex overflow-hidden">
        <ScrollArea className="flex-1 p-4">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
            </div>
          ) : activities.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              {searchQuery ? (
                <>
                  <p>No activities found for &quot;{searchQuery}&quot;</p>
                  <p className="text-sm mt-2">Try a different theme or search term</p>
                </>
              ) : (
                <>
                  <Sparkles className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Search for activities by theme or idea</p>
                  <p className="text-sm mt-2">Click a theme above to get started</p>
                </>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {activities.map((activity) => (
                <ActivityListItem
                  key={activity.id}
                  activity={activity}
                  isSelected={selectedActivity?.id === activity.id}
                  onClick={() => setSelectedActivity(activity)}
                  onAddToSchedule={() => onAddToSchedule?.(activity)}
                  selectedWeek={selectedWeek}
                  onAddToWeek={onAddToWeek}
                />
              ))}
            </div>
          )}
        </ScrollArea>

        {/* Detail Panel */}
        {selectedActivity && (
          <div className="w-96 border-l bg-muted/30 p-4 overflow-y-auto">
            <ActivityDetailPanel
              activity={selectedActivity}
              onClose={() => setSelectedActivity(null)}
              onAddToSchedule={() => onAddToSchedule?.(selectedActivity)}
              selectedWeek={selectedWeek}
              onAddToWeek={onAddToWeek}
              onSelectWeek={setSelectedWeek}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function ActivityListItem({
  activity,
  isSelected,
  onClick,
  onAddToSchedule,
  selectedWeek,
  onAddToWeek,
}: {
  activity: Activity;
  isSelected: boolean;
  onClick: () => void;
  onAddToSchedule: () => void;
  selectedWeek: number | null;
  onAddToWeek?: (activity: Activity, week: number) => void;
}) {
  return (
    <Card
      className={cn(
        'cursor-pointer transition-all hover:shadow-md',
        isSelected && 'ring-2 ring-primary'
      )}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h3 className="font-medium truncate">{activity.title}</h3>
            <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
              {activity.description}
            </p>
            <div className="flex flex-wrap gap-2 mt-2">
              <Badge variant="outline" className="text-xs">
                {activity.type}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {activity.development_age_group}
              </Badge>
              {activity.duration_minutes && (
                <Badge variant="outline" className="text-xs">
                  {activity.duration_minutes}min
                </Badge>
              )}
            </div>
          </div>
          <div className="flex gap-1">
            <Button
              size="sm"
              variant="ghost"
              onClick={(e) => {
                e.stopPropagation();
                onAddToSchedule();
              }}
            >
              <Plus className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ActivityDetailPanel({
  activity,
  onClose,
  onAddToSchedule,
  selectedWeek,
  onAddToWeek,
  onSelectWeek,
}: {
  activity: Activity;
  onClose: () => void;
  onAddToSchedule: () => void;
  selectedWeek: number | null;
  onAddToWeek?: (activity: Activity, week: number) => void;
  onSelectWeek: (week: number | null) => void;
}) {
  const [weekSelectionOpen, setWeekSelectionOpen] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{activity.title}</h2>
        <Button variant="ghost" size="sm" onClick={onClose}>
          ×
        </Button>
      </div>

      <Badge className="text-xs">{activity.type}</Badge>

      <p className="text-sm">{activity.description}</p>

      <div className="space-y-2 text-sm">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Users className="w-4 h-4" />
          {activity.development_age_group}
        </div>
        {activity.duration_minutes && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="w-4 h-4" />
            {activity.duration_minutes} minutes
          </div>
        )}
        {activity.indoor_outdoor && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Calendar className="w-4 h-4" />
            {activity.indoor_outdoor}
          </div>
        )}
      </div>

      {activity.supplies && (
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Package className="w-4 h-4" />
            Supplies
          </div>
          <p className="text-sm text-muted-foreground">{activity.supplies}</p>
        </div>
      )}

      {activity.instructions && (
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm font-medium">
            <ClipboardList className="w-4 h-4" />
            Instructions
          </div>
          <div className="text-sm text-muted-foreground whitespace-pre-wrap max-h-64 overflow-y-auto">
            {activity.instructions}
          </div>
        </div>
      )}

      <div className="pt-4 space-y-2">
        <Button onClick={onAddToSchedule} className="w-full">
          <Plus className="w-4 h-4 mr-2" />
          Add to Schedule
        </Button>

        <div className="relative">
          <Button
            variant="outline"
            className="w-full"
            onClick={() => setWeekSelectionOpen(!weekSelectionOpen)}
          >
            <Calendar className="w-4 h-4 mr-2" />
            {selectedWeek ? `Add to Week ${selectedWeek}` : 'Add to Summer Camp Week'}
            {weekSelectionOpen ? (
              <ChevronUp className="w-4 h-4 ml-auto" />
            ) : (
              <ChevronDown className="w-4 h-4 ml-auto" />
            )}
          </Button>

          {weekSelectionOpen && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-popover border rounded-md shadow-lg z-10">
              {[1, 2, 3, 4, 5, 6, 7, 8].map((week) => (
                <button
                  key={week}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-muted first:rounded-t-md last:rounded-b-md"
                  onClick={() => {
                    onSelectWeek(week);
                    onAddToWeek?.(activity, week);
                    setWeekSelectionOpen(false);
                  }}
                >
                  Week {week}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
