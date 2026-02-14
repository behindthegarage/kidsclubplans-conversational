'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  ChevronLeft, 
  ChevronRight, 
  Calendar,
  Clock,
  Package,
  Printer,
  Plus,
  Trash2,
  Save
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ScheduledActivity {
  id: string;
  activity_id: string;
  title: string;
  description: string;
  start_time: string;
  duration_minutes: number;
  type: string;
  supplies?: string;
}

interface WeekSchedule {
  weekNumber: number;
  theme: string;
  monday: ScheduledActivity[];
  tuesday: ScheduledActivity[];
  wednesday: ScheduledActivity[];
  thursday: ScheduledActivity[];
  friday: ScheduledActivity[];
}

const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'] as const;
const DAY_LABELS = { monday: 'Mon', tuesday: 'Tue', wednesday: 'Wed', thursday: 'Thu', friday: 'Fri' };

const TIME_SLOTS = [
  '7:00 AM', '8:00 AM', '9:00 AM', '10:00 AM', '11:00 AM',
  '12:00 PM', '1:00 PM', '2:00 PM', '3:00 PM', '4:00 PM', '5:00 PM', '6:00 PM'
];

interface WeeklySchedulerProps {
  initialWeek?: number;
  onSave?: (schedule: WeekSchedule) => void;
}

export function WeeklyScheduler({ initialWeek = 1, onSave }: WeeklySchedulerProps) {
  const [currentWeek, setCurrentWeek] = useState(initialWeek);
  const [schedule, setSchedule] = useState<WeekSchedule>({
    weekNumber: initialWeek,
    theme: '',
    monday: [],
    tuesday: [],
    wednesday: [],
    thursday: [],
    friday: [],
  });
  const [showSupplyList, setShowSupplyList] = useState(false);

  // Load activities from localStorage when week changes
  useEffect(() => {
    const key = `week-${currentWeek}-activities`;
    const saved = localStorage.getItem(key);
    if (saved) {
      try {
        const activities = JSON.parse(saved);
        // Distribute activities across days
        const days: typeof DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'];
        const newSchedule: any = {
          weekNumber: currentWeek,
          theme: '',
          monday: [],
          tuesday: [],
          wednesday: [],
          thursday: [],
          friday: [],
        };
        
        activities.forEach((act: any, index: number) => {
          const day = days[index % days.length];
          newSchedule[day].push({
            id: act.id || Math.random().toString(36).substr(2, 9),
            activity_id: act.id || '',
            title: act.title || 'Activity',
            description: act.description || '',
            start_time: act.start_time || '9:00 AM',
            duration_minutes: act.duration_minutes || 30,
            type: act.type || act.activity_type || 'Other',
            supplies: act.supplies || '',
          });
        });
        
        setSchedule(newSchedule);
      } catch (e) {
        console.error('Failed to load activities:', e);
      }
    } else {
      // Reset if no saved activities
      setSchedule({
        weekNumber: currentWeek,
        theme: '',
        monday: [],
        tuesday: [],
        wednesday: [],
        thursday: [],
        friday: [],
      });
    }
  }, [currentWeek]);

  const addActivity = (day: typeof DAYS[number], activity: Partial<ScheduledActivity>) => {
    setSchedule(prev => ({
      ...prev,
      [day]: [...prev[day], {
        id: Math.random().toString(36).substr(2, 9),
        activity_id: activity.activity_id || '',
        title: activity.title || 'New Activity',
        description: activity.description || '',
        start_time: activity.start_time || '9:00 AM',
        duration_minutes: activity.duration_minutes || 60,
        type: activity.type || 'Other',
        supplies: activity.supplies || '',
      }],
    }));
  };

  const removeActivity = (day: typeof DAYS[number], activityId: string) => {
    setSchedule(prev => ({
      ...prev,
      [day]: prev[day].filter(a => a.id !== activityId),
    }));
  };

  const moveActivity = (fromDay: typeof DAYS[number], toDay: typeof DAYS[number], activityId: string) => {
    if (fromDay === toDay) return;
    
    setSchedule(prev => {
      const activity = prev[fromDay].find(a => a.id === activityId);
      if (!activity) return prev;
      
      return {
        ...prev,
        [fromDay]: prev[fromDay].filter(a => a.id !== activityId),
        [toDay]: [...prev[toDay], activity],
      };
    });
  };

  const getAllSupplies = () => {
    const allSupplies: string[] = [];
    DAYS.forEach(day => {
      schedule[day].forEach(activity => {
        if (activity.supplies) {
          allSupplies.push(...activity.supplies.split(',').map(s => s.trim()));
        }
      });
    });
    return Array.from(new Set(allSupplies)).filter(Boolean).sort();
  };

  const handlePrint = () => {
    window.print();
  };

  const handleSave = () => {
    onSave?.(schedule);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b p-2 lg:p-4 space-y-2 lg:space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-2">
          <div className="flex flex-col sm:flex-row sm:items-center gap-2">
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setCurrentWeek(prev => Math.max(1, prev - 1))}
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <span className="font-semibold text-sm lg:text-base w-16 text-center">Week {currentWeek}</span>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setCurrentWeek(prev => prev + 1)}
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
            
            <input
              type="text"
              placeholder="Week theme (e.g., Space)..."
              value={schedule.theme}
              onChange={(e) => setSchedule(prev => ({ ...prev, theme: e.target.value }))}
              className="px-3 py-1.5 text-sm border rounded-md bg-background w-full sm:w-48 lg:w-64"
            />
          </div>

          <div className="flex gap-1 lg:gap-2">
            <Button
              variant="outline"
              size="sm"
              className="text-xs lg:text-sm px-2 lg:px-3"
              onClick={() => setShowSupplyList(!showSupplyList)}
            >
              <Package className="w-3 h-3 lg:w-4 lg:h-4 mr-1 lg:mr-2" />
              <span className="hidden sm:inline">Supplies</span>
              <span className="sm:hidden">Supp.</span>
              <span className="ml-1">({getAllSupplies().length})</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-xs lg:text-sm px-2 lg:px-3"
              onClick={handlePrint}
            >
              <Printer className="w-3 h-3 lg:w-4 lg:h-4 mr-1 lg:mr-2" />
              <span className="hidden sm:inline">Print</span>
            </Button>
            
            <Button
              size="sm"
              className="text-xs lg:text-sm px-2 lg:px-3"
              onClick={handleSave}
            >
              <Save className="w-3 h-3 lg:w-4 lg:h-4 mr-1 lg:mr-2" />
              <span className="hidden sm:inline">Save</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Main Schedule Grid - Mobile: vertical scroll, Desktop: horizontal */}
      <div className="flex-1 overflow-auto">
        <div className="p-4 min-w-full lg:min-w-[800px]">
          {/* Mobile: Stack days vertically, Desktop: 5 columns */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {DAYS.map((day) => (
              <DayColumn
                key={day}
                day={day}
                label={DAY_LABELS[day]}
                activities={schedule[day]}
                onAddActivity={(activity) => addActivity(day, activity)}
                onRemoveActivity={(id) => removeActivity(day, id)}
                onMoveActivity={moveActivity}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Supply List Sidebar */}
      {showSupplyList && (
        <div className="w-full lg:w-80 border-t lg:border-t-0 lg:border-l bg-muted/30 p-4">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Package className="w-4 h-4" />
            Supply List
          </h3>
          <div className="space-y-2">
            {getAllSupplies().length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Add activities to see supplies needed
              </p>
            ) : (
              getAllSupplies().map((supply, i) => (
                <label key={i} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" className="rounded" />
                  <span>{supply}</span>
                </label>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

interface DayColumnProps {
  day: typeof DAYS[number];
  label: string;
  activities: ScheduledActivity[];
  onAddActivity: (activity: Partial<ScheduledActivity>) => void;
  onRemoveActivity: (id: string) => void;
  onMoveActivity: (fromDay: typeof DAYS[number], toDay: typeof DAYS[number], id: string) => void;
}

function DayColumn({ day, label, activities, onAddActivity, onRemoveActivity, onMoveActivity }: DayColumnProps) {
  const [showAddForm, setShowAddForm] = useState(false);

  return (
    <div className="flex flex-col h-full">
      <div className="text-center py-1.5 lg:py-2 font-medium border-b mb-1.5 lg:mb-2 text-sm lg:text-base">
        {label}
      </div>
      
      <div className="flex-1 space-y-1.5 lg:space-y-2 min-h-[150px] lg:min-h-[400px]">
        {activities.map((activity) => (
          <Card key={activity.id} className="relative group">
            <CardContent className="p-2 lg:p-3">
              <div className="flex items-start justify-between gap-1">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{activity.title}</p>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5 lg:mt-1">
                    <Clock className="w-3 h-3" />
                    {activity.start_time} ({activity.duration_minutes}min)
                  </div>
                  <Badge variant="outline" className="text-[10px] lg:text-xs mt-1 lg:mt-2 px-1 py-0">
                    {activity.type}
                  </Badge>
                </div>
                <div className="flex flex-col gap-1">
                  {/* Move dropdown - always visible on mobile, hover on desktop */}
                  <select
                    className="text-[10px] lg:text-xs px-1 py-0.5 border rounded bg-background lg:opacity-0 lg:group-hover:opacity-100 transition-opacity"
                    value=""
                    onChange={(e) => {
                      if (e.target.value) {
                        onMoveActivity(day, e.target.value as typeof DAYS[number], activity.id);
                        e.target.value = '';
                      }
                    }}
                  >
                    <option value="">Move to...</option>
                    {DAYS.filter(d => d !== day).map(d => (
                      <option key={d} value={d}>{DAY_LABELS[d]}</option>
                    ))}
                  </select>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-5 w-5 lg:h-6 lg:w-6 p-0 lg:opacity-0 lg:group-hover:opacity-100"
                    onClick={() => onRemoveActivity(activity.id)}
                  >
                    <Trash2 className="w-3 h-3 text-destructive" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}

        <Button
          variant="outline"
          className="w-full h-12 lg:h-20 border-dashed text-xs lg:text-sm"
          onClick={() => setShowAddForm(true)}
        >
          <Plus className="w-3 h-3 lg:w-4 lg:h-4 mr-1 lg:mr-2" />
          Add Activity
        </Button>
      </div>
    </div>
  );
}
