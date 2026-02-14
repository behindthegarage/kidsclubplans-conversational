'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
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
  ChevronUp,
  Grid3X3,
  List,
  SortAsc,
  SortDesc,
  ArrowUpDown,
  X,
  Star,
  Download,
  Trash2,
  History
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
  onAddMultipleToWeek?: (activities: Activity[], weekNumber: number) => void;
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
const ACTIVITY_TYPES = ['Physical', 'STEM', 'Arts & Crafts', 'Team Building', 'Nature', 'Cooking', 'Music & Movement', 'Science', 'Craft', 'Art'];

// Local storage key for recent searches
const RECENT_SEARCHES_KEY = 'kcp-recent-searches';
const FAVORITES_KEY = 'kcp-favorite-activities';

type SortOption = 'relevance' | 'name' | 'duration' | 'type';
type ViewMode = 'list' | 'grid';

export function ActivityBrowser({ onAddToSchedule, onAddToWeek, onAddMultipleToWeek }: ActivityBrowserProps) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);
  const [selectedActivities, setSelectedActivities] = useState<Set<string>>(new Set());
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [sortBy, setSortBy] = useState<SortOption>('relevance');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const [showRecent, setShowRecent] = useState(false);
  
  const [filters, setFilters] = useState({
    ageGroup: '',
    type: '',
    indoorOutdoor: '',
    maxDuration: 120,
    showFavoritesOnly: false,
  });
  const [showFilters, setShowFilters] = useState(false);
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null);

  // Load recent searches and favorites on mount
  useEffect(() => {
    const saved = localStorage.getItem(RECENT_SEARCHES_KEY);
    if (saved) {
      setRecentSearches(JSON.parse(saved));
    }
    const savedFavorites = localStorage.getItem(FAVORITES_KEY);
    if (savedFavorites) {
      setFavorites(new Set(JSON.parse(savedFavorites)));
    }
  }, []);

  // Save recent searches
  const addRecentSearch = useCallback((query: string) => {
    if (!query.trim()) return;
    setRecentSearches(prev => {
      const updated = [query, ...prev.filter(s => s !== query)].slice(0, 10);
      localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  // Toggle favorite
  const toggleFavorite = useCallback((activityId: string) => {
    setFavorites(prev => {
      const next = new Set(prev);
      if (next.has(activityId)) {
        next.delete(activityId);
      } else {
        next.add(activityId);
      }
      localStorage.setItem(FAVORITES_KEY, JSON.stringify(Array.from(next)));
      return next;
    });
  }, []);

  const searchActivities = useCallback(async (query: string) => {
    if (!query.trim()) {
      setActivities([]);
      return;
    }

    setIsLoading(true);
    addRecentSearch(query);
    
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
          limit: 50,
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
  }, [filters, addRecentSearch]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      if (searchQuery) {
        searchActivities(searchQuery);
      }
    }, 300);
    return () => clearTimeout(timeout);
  }, [searchQuery, searchActivities]);

  // Filter and sort activities
  const filteredAndSortedActivities = useMemo(() => {
    let result = [...activities];
    
    // Filter by favorites
    if (filters.showFavoritesOnly) {
      result = result.filter(a => favorites.has(a.id));
    }
    
    // Sort
    result.sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case 'relevance':
          comparison = (b.score || 0) - (a.score || 0);
          break;
        case 'name':
          comparison = a.title.localeCompare(b.title);
          break;
        case 'duration':
          comparison = (a.duration_minutes || 0) - (b.duration_minutes || 0);
          break;
        case 'type':
          comparison = (a.type || '').localeCompare(b.type || '');
          break;
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });
    
    return result;
  }, [activities, sortBy, sortOrder, filters.showFavoritesOnly, favorites]);

  const handleThemeClick = (theme: string) => {
    setSearchQuery(theme);
    searchActivities(theme);
  };

  const clearFilters = () => {
    setFilters({
      ageGroup: '',
      type: '',
      indoorOutdoor: '',
      maxDuration: 120,
      showFavoritesOnly: false,
    });
  };

  const hasActiveFilters = filters.ageGroup || filters.type || filters.indoorOutdoor || filters.maxDuration !== 120 || filters.showFavoritesOnly;

  const toggleSelection = (activityId: string) => {
    setSelectedActivities(prev => {
      const next = new Set(prev);
      if (next.has(activityId)) {
        next.delete(activityId);
      } else {
        next.add(activityId);
      }
      return next;
    });
  };

  const selectAll = () => {
    setSelectedActivities(new Set(filteredAndSortedActivities.map(a => a.id)));
  };

  const clearSelection = () => {
    setSelectedActivities(new Set());
  };

  const addSelectedToWeek = (week: number) => {
    const selected = filteredAndSortedActivities.filter(a => selectedActivities.has(a.id));
    onAddMultipleToWeek?.(selected, week);
    clearSelection();
    setIsSelectionMode(false);
  };

  const activeFiltersCount = [
    filters.ageGroup,
    filters.type,
    filters.indoorOutdoor,
    filters.maxDuration !== 120 ? 'duration' : null,
    filters.showFavoritesOnly ? 'favorites' : null
  ].filter(Boolean).length;

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
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className={cn(showFilters && 'bg-muted', activeFiltersCount > 0 && 'border-primary')}
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
            {activeFiltersCount > 0 && (
              <Badge variant="secondary" className="ml-2 text-xs">
                {activeFiltersCount}
              </Badge>
            )}
          </Button>
        </div>

        {/* Theme Pills & Recent */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-muted-foreground py-1">Popular themes:</span>
            {THEME_SUGGESTIONS.map((theme) => (
              <button
                key={theme}
                onClick={() => handleThemeClick(theme)}
                className={cn(
                  "text-xs px-3 py-1 rounded-full transition-colors",
                  searchQuery === theme 
                    ? "bg-primary text-primary-foreground" 
                    : "bg-muted hover:bg-muted/80"
                )}
              >
                {theme}
              </button>
            ))}
          </div>
          
          {recentSearches.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={() => setShowRecent(!showRecent)}
                className="text-xs text-muted-foreground flex items-center gap-1 hover:text-foreground"
              >
                <History className="w-3 h-3" />
                {showRecent ? 'Hide' : 'Show'} recent
              </button>
              {showRecent && recentSearches.map((search) => (
                <button
                  key={search}
                  onClick={() => setSearchQuery(search)}
                  className="text-xs px-2 py-0.5 rounded bg-muted/50 hover:bg-muted transition-colors"
                >
                  {search}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="space-y-3 p-3 bg-muted/50 rounded-lg">
            <div className="flex flex-wrap gap-3">
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
              
              <label className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.showFavoritesOnly}
                  onChange={(e) => setFilters({ ...filters, showFavoritesOnly: e.target.checked })}
                  className="rounded border-gray-300"
                />
                <Star className="w-4 h-4" />
                Favorites only
              </label>
            </div>
            
            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={clearFilters} className="text-xs">
                <X className="w-3 h-3 mr-1" />
                Clear all filters
              </Button>
            )}
          </div>
        )}

        {/* Toolbar */}
        {activities.length > 0 && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">
                {filteredAndSortedActivities.length} activities
                {selectedActivities.size > 0 && ` (${selectedActivities.size} selected)`}
              </span>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsSelectionMode(!isSelectionMode)}
              >
                {isSelectionMode ? 'Done' : 'Select'}
              </Button>
              
              {isSelectionMode && (
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm" onClick={selectAll}>
                    Select all
                  </Button>
                  <Button variant="ghost" size="sm" onClick={clearSelection}>
                    Clear
                  </Button>
                  {selectedActivities.size > 0 && (
                    <select
                      onChange={(e) => {
                        if (e.target.value) {
                          addSelectedToWeek(parseInt(e.target.value));
                          e.target.value = '';
                        }
                      }}
                      className="text-sm px-2 py-1 border rounded bg-background text-foreground"
                      style={{ color: 'hsl(var(--foreground))' }}
                    >
                      <option value="" style={{ color: 'hsl(var(--foreground))' }}>Add to week...</option>
                      {[1, 2, 3, 4, 5, 6, 7, 8].map((w) => (
                        <option key={w} value={w} style={{ color: 'hsl(var(--foreground))' }}>Week {w}</option>
                      ))}
                    </select>
                  )}
                </div>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              {/* Sort */}
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className="text-sm px-2 py-1 border rounded-md"
              >
                <option value="relevance">Sort: Relevance</option>
                <option value="name">Sort: Name</option>
                <option value="duration">Sort: Duration</option>
                <option value="type">Sort: Type</option>
              </select>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              >
                {sortOrder === 'asc' ? <SortAsc className="w-4 h-4" /> : <SortDesc className="w-4 h-4" />}
              </Button>
              
              <div className="border-l pl-2 ml-2">
                <Button
                  variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('grid')}
                >
                  <Grid3X3 className="w-4 h-4" />
                </Button>
                <Button
                  variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('list')}
                >
                  <List className="w-4 h-4" />
                </Button>
              </div>
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
          ) : filteredAndSortedActivities.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              {searchQuery ? (
                <>
                  <p>No activities found for &quot;{searchQuery}&quot;</p>
                  <p className="text-sm mt-2">Try a different theme or search term</p>
                  {hasActiveFilters && (
                    <Button variant="outline" size="sm" onClick={clearFilters} className="mt-4">
                      Clear filters
                    </Button>
                  )}
                </>
              ) : (
                <>
                  <Sparkles className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Search for activities by theme or idea</p>
                  <p className="text-sm mt-2">Click a theme above to get started</p>
                </>
              )}
            </div>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-2 gap-3">
              {filteredAndSortedActivities.map((activity) => (
                <ActivityGridItem
                  key={activity.id}
                  activity={activity}
                  isSelected={selectedActivity?.id === activity.id}
                  isChecked={selectedActivities.has(activity.id)}
                  isSelectionMode={isSelectionMode}
                  isFavorite={favorites.has(activity.id)}
                  onClick={() => setSelectedActivity(activity)}
                  onToggleCheck={() => toggleSelection(activity.id)}
                  onToggleFavorite={() => toggleFavorite(activity.id)}
                  onAddToSchedule={() => onAddToSchedule?.(activity)}
                  selectedWeek={selectedWeek}
                  onAddToWeek={onAddToWeek}
                />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {filteredAndSortedActivities.map((activity) => (
                <ActivityListItem
                  key={activity.id}
                  activity={activity}
                  isSelected={selectedActivity?.id === activity.id}
                  isChecked={selectedActivities.has(activity.id)}
                  isSelectionMode={isSelectionMode}
                  isFavorite={favorites.has(activity.id)}
                  onClick={() => setSelectedActivity(activity)}
                  onToggleCheck={() => toggleSelection(activity.id)}
                  onToggleFavorite={() => toggleFavorite(activity.id)}
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
              isFavorite={favorites.has(selectedActivity.id)}
              onToggleFavorite={() => toggleFavorite(selectedActivity.id)}
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
  isChecked,
  isSelectionMode,
  isFavorite,
  onClick,
  onToggleCheck,
  onToggleFavorite,
  onAddToSchedule,
  selectedWeek,
  onAddToWeek,
}: {
  activity: Activity;
  isSelected: boolean;
  isChecked: boolean;
  isSelectionMode: boolean;
  isFavorite: boolean;
  onClick: () => void;
  onToggleCheck: () => void;
  onToggleFavorite: (e: React.MouseEvent) => void;
  onAddToSchedule: () => void;
  selectedWeek: number | null;
  onAddToWeek?: (activity: Activity, week: number) => void;
}) {
  const [showAddMenu, setShowAddMenu] = useState(false);
  
  return (
    <Card
      className={cn(
        'cursor-pointer transition-all hover:shadow-md',
        isSelected && 'ring-2 ring-primary'
      )}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {isSelectionMode && (
            <div className="pt-1" onClick={(e) => e.stopPropagation()}>
              <Checkbox checked={isChecked} onCheckedChange={onToggleCheck} />
            </div>
          )}
          
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-medium truncate">{activity.title}</h3>
              <div className="flex items-center gap-1">
                <button
                  onClick={onToggleFavorite}
                  className={cn(
                    "p-1 rounded hover:bg-muted transition-colors",
                    isFavorite ? "text-yellow-500" : "text-muted-foreground"
                  )}
                >
                  <Star className={cn("w-4 h-4", isFavorite && "fill-current")} />
                </button>
              </div>
            </div>
            
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
                  <Clock className="w-3 h-3 mr-1" />
                  {activity.duration_minutes}min
                </Badge>
              )}
              {activity.score && activity.score > 0.7 && (
                <Badge variant="secondary" className="text-xs">
                  {Math.round(activity.score * 100)}% match
                </Badge>
              )}
            </div>
          </div>
          
          {!isSelectionMode && (
            <div className="flex flex-col gap-1">
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
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function ActivityGridItem({
  activity,
  isSelected,
  isChecked,
  isSelectionMode,
  isFavorite,
  onClick,
  onToggleCheck,
  onToggleFavorite,
  onAddToSchedule,
  selectedWeek,
  onAddToWeek,
}: {
  activity: Activity;
  isSelected: boolean;
  isChecked: boolean;
  isSelectionMode: boolean;
  isFavorite: boolean;
  onClick: () => void;
  onToggleCheck: () => void;
  onToggleFavorite: (e: React.MouseEvent) => void;
  onAddToSchedule: () => void;
  selectedWeek: number | null;
  onAddToWeek?: (activity: Activity, week: number) => void;
}) {
  return (
    <Card
      className={cn(
        'cursor-pointer transition-all hover:shadow-md overflow-hidden',
        isSelected && 'ring-2 ring-primary'
      )}
      onClick={onClick}
    >
      <CardContent className="p-3">
        <div className="flex items-start gap-2">
          {isSelectionMode && (
            <div onClick={(e) => e.stopPropagation()}>
              <Checkbox checked={isChecked} onCheckedChange={onToggleCheck} />
            </div>
          )}
          
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-1">
              <h3 className="font-medium text-sm line-clamp-2">{activity.title}</h3>
              <button
                onClick={onToggleFavorite}
                className={cn(
                  "p-0.5 shrink-0",
                  isFavorite ? "text-yellow-500" : "text-muted-foreground"
                )}
              >
                <Star className={cn("w-3 h-3", isFavorite && "fill-current")} />
              </button>
            </div>
            
            <div className="flex flex-wrap gap-1 mt-2">
              <Badge variant="outline" className="text-[10px] px-1.5">
                {activity.type}
              </Badge>
              {activity.duration_minutes && (
                <Badge variant="outline" className="text-[10px] px-1.5">
                  {activity.duration_minutes}m
                </Badge>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ActivityDetailPanel({
  activity,
  isFavorite,
  onToggleFavorite,
  onClose,
  onAddToSchedule,
  selectedWeek,
  onAddToWeek,
  onSelectWeek,
}: {
  activity: Activity;
  isFavorite: boolean;
  onToggleFavorite: () => void;
  onClose: () => void;
  onAddToSchedule: () => void;
  selectedWeek: number | null;
  onAddToWeek?: (activity: Activity, week: number) => void;
  onSelectWeek: (week: number | null) => void;
}) {
  const [weekSelectionOpen, setWeekSelectionOpen] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-2">
        <h2 className="text-lg font-semibold">{activity.title}</h2>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={onToggleFavorite}>
            <Star className={cn("w-5 h-5", isFavorite ? "fill-yellow-500 text-yellow-500" : "text-muted-foreground")} />
          </Button>
          <Button variant="ghost" size="sm" onClick={onClose}>
            ×
          </Button>
        </div>
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
          <ul className="text-sm text-muted-foreground pl-4 space-y-1 list-disc list-outside">
            {activity.supplies
              .split(/[,;]/)
              .map(s => s.trim())
              .filter(s => s.length > 0)
              .map((supply, index) => (
                <li key={index}>{supply}</li>
              ))}
          </ul>
        </div>
      )}

      {activity.instructions && (
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm font-medium">
            <ClipboardList className="w-4 h-4" />
            Instructions
          </div>
          <ol className="text-sm text-muted-foreground pl-4 space-y-2 list-decimal list-outside max-h-64 overflow-y-auto">
            {activity.instructions
              .split(/\d+\.|\n+/)
              .map(step => step.trim())
              .filter(step => step.length > 0)
              .map((step, index) => (
                <li key={index} className="leading-relaxed">
                  {step.replace(/^[.\s]+|[.\s]+$/g, '')}
                </li>
              ))}
          </ol>
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
