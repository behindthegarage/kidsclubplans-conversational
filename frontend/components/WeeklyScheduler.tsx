'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  ChevronLeft, 
  ChevronRight, 
  Clock,
  Package,
  Printer,
  Plus,
  Trash2,
  Save,
  GripVertical,
  Calendar
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

// Generate time slots in 15-min increments from 7 AM to 6 PM
const generateTimeSlots = () => {
  const slots: string[] = [];
  for (let hour = 7; hour <= 18; hour++) {
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour > 12 ? hour - 12 : hour;
    slots.push(`${displayHour}:00 ${period}`);
    slots.push(`${displayHour}:15 ${period}`);
    slots.push(`${displayHour}:30 ${period}`);
    slots.push(`${displayHour}:45 ${period}`);
  }
  return slots;
};

const TIME_SLOTS = generateTimeSlots();

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
  const [viewMode, setViewMode] = useState<'list' | 'timeline'>('list');
  const [draggedItem, setDraggedItem] = useState<{day: typeof DAYS[number], index: number} | null>(null);

  // Load activities from localStorage when week changes
  useEffect(() => {
    const key = `week-${currentWeek}-activities`;
    const saved = localStorage.getItem(key);
    if (saved) {
      try {
        const activities = JSON.parse(saved);
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
        
        // Sort each day by time
        days.forEach(day => {
          newSchedule[day].sort((a: any, b: any) => 
            TIME_SLOTS.indexOf(a.start_time) - TIME_SLOTS.indexOf(b.start_time)
          );
        });
        
        setSchedule(newSchedule);
      } catch (e) {
        console.error('Failed to load activities:', e);
      }
    } else {
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

  const sortDayByTime = (dayActivities: ScheduledActivity[]) => {
    return [...dayActivities].sort((a, b) => 
      TIME_SLOTS.indexOf(a.start_time) - TIME_SLOTS.indexOf(b.start_time)
    );
  };

  const addActivity = (day: typeof DAYS[number], activity: Partial<ScheduledActivity>) => {
    setSchedule(prev => {
      const updated = {
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
      };
      updated[day] = sortDayByTime(updated[day]);
      return updated;
    });
  };

  const updateActivityTime = (day: typeof DAYS[number], activityId: string, newTime: string) => {
    setSchedule(prev => {
      const updated = {
        ...prev,
        [day]: prev[day].map(a => 
          a.id === activityId ? { ...a, start_time: newTime } : a
        ),
      };
      updated[day] = sortDayByTime(updated[day]);
      return updated;
    });
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
      
      const updated = {
        ...prev,
        [fromDay]: prev[fromDay].filter(a => a.id !== activityId),
        [toDay]: sortDayByTime([...prev[toDay], activity]),
      };
      return updated;
    });
  };

  // Drag and drop reordering
  const handleDragStart = (day: typeof DAYS[number], index: number) => {
    setDraggedItem({ day, index });
  };

  const handleDragOver = (e: React.DragEvent, day: typeof DAYS[number], index: number) => {
    e.preventDefault();
    if (!draggedItem || draggedItem.day !== day) return;
    
    if (draggedItem.index === index) return;
    
    setSchedule(prev => {
      const activities = [...prev[day]];
      const [removed] = activities.splice(draggedItem.index, 1);
      activities.splice(index, 0, removed);
      
      return {
        ...prev,
        [day]: activities,
      };
    });
    
    setDraggedItem({ day, index });
  };

  const handleDragEnd = () => {
    setDraggedItem(null);
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

  const handleSave = async () => {
    onSave?.(schedule);
    
    // Save to API
    try {
      // Convert day-based structure to flat list with day property
      const allActivities = DAYS.flatMap(day => 
        schedule[day].map(act => ({ ...act, day }))
      );
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/schedules/weekly/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          week_number: currentWeek,
          theme: schedule.theme,
          activities: allActivities
        })
      });
      
      if (response.ok) {
        alert(`Week ${currentWeek} saved successfully!`);
      } else {
        throw new Error('Save failed');
      }
    } catch (e) {
      console.error('Failed to save to API, falling back to localStorage:', e);
      // Fallback to localStorage
      const key = `week-${currentWeek}-activities`;
      const allActivities = DAYS.flatMap(day => 
        schedule[day].map(act => ({ ...act, day }))
      );
      localStorage.setItem(key, JSON.stringify(allActivities));
      alert(`Week ${currentWeek} saved locally (API unavailable)`);
    }
  };

  const handleDuplicate = async (targetWeek: number) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/schedules/weekly/duplicate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          from_week: currentWeek,
          to_week: targetWeek
        })
      });
      
      if (response.ok) {
        alert(`Week ${currentWeek} duplicated to Week ${targetWeek}!`);
      } else {
        throw new Error('Duplicate failed');
      }
    } catch (e) {
      console.error('Failed to duplicate:', e);
      alert('Failed to duplicate week. Please try again.');
    }
  };

  // Calculate position for timeline view
  const getTimelinePosition = (startTime: string) => {
    const index = TIME_SLOTS.indexOf(startTime);
    if (index === -1) return 0;
    return (index / TIME_SLOTS.length) * 100;
  };

  const getTimelineHeight = (durationMinutes: number) => {
    // Each 15-min slot is roughly 4% of height
    return (durationMinutes / 15) * 4;
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

            {/* Duplicate Week Dropdown */}
            <select
              className="text-xs px-2 py-1.5 border rounded-md bg-background"
              value=""
              onChange={(e) => {
                if (e.target.value) {
                  handleDuplicate(parseInt(e.target.value));
                  e.target.value = '';
                }
              }}
            >
              <option value="">Duplicate to...</option>
              {[1, 2, 3, 4, 5, 6, 7, 8].filter(w => w !== currentWeek).map(w => (
                <option key={w} value={w}>Week {w}</option>
              ))}
            </select>
          </div>

          <div className="flex gap-1 lg:gap-2 flex-wrap">
            {/* View Toggle */}
            <div className="flex border rounded-md overflow-hidden">
              <Button
                variant={viewMode === 'list' ? 'default' : 'ghost'}
                size="sm"
                className="rounded-none text-xs px-2"
                onClick={() => setViewMode('list')}
              >
                List
              </Button>
              <Button
                variant={viewMode === 'timeline' ? 'default' : 'ghost'}
                size="sm"
                className="rounded-none text-xs px-2"
                onClick={() => setViewMode('timeline')}
              >
                <Clock className="w-3 h-3 mr-1" />
                Timeline
              </Button>
            </div>

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

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        {viewMode === 'list' ? (
          <div className="p-2 lg:p-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2 lg:gap-4">
              {DAYS.map((day) => (
                <DayColumn
                  key={day}
                  day={day}
                  label={DAY_LABELS[day]}
                  activities={schedule[day]}
                  onAddActivity={(activity) => addActivity(day, activity)}
                  onRemoveActivity={(id) => removeActivity(day, id)}
                  onMoveActivity={moveActivity}
                  onUpdateTime={(id, time) => updateActivityTime(day, id, time)}
                  onDragStart={handleDragStart}
                  onDragOver={handleDragOver}
                  onDragEnd={handleDragEnd}
                  draggedItem={draggedItem}
                />
              ))}
            </div>
          </div>
        ) : (
          <TimelineView
            schedule={schedule}
            onUpdateTime={(day, id, time) => updateActivityTime(day, id, time)}
            onRemoveActivity={(day, id) => removeActivity(day, id)}
          />
        )}
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
  onUpdateTime: (id: string, time: string) => void;
  onDragStart: (day: typeof DAYS[number], index: number) => void;
  onDragOver: (e: React.DragEvent, day: typeof DAYS[number], index: number) => void;
  onDragEnd: () => void;
  draggedItem: {day: typeof DAYS[number], index: number} | null;
}

function DayColumn({ 
  day, label, activities, onAddActivity, onRemoveActivity, onMoveActivity, 
  onUpdateTime, onDragStart, onDragOver, onDragEnd, draggedItem 
}: DayColumnProps) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [newActivityTime, setNewActivityTime] = useState('9:00 AM');

  return (
    <div className="flex flex-col h-full">
      <div className="text-center py-1.5 lg:py-2 font-medium border-b mb-1.5 lg:mb-2 text-sm lg:text-base">
        {label}
      </div>
      
      <div className="flex-1 space-y-1.5 lg:space-y-2 min-h-[150px] lg:min-h-[400px]">
        {activities.map((activity, index) => (
          <Card 
            key={activity.id} 
            className={cn(
              "relative group cursor-move",
              draggedItem?.day === day && draggedItem?.index === index && "opacity-50"
            )}
            draggable
            onDragStart={() => onDragStart(day, index)}
            onDragOver={(e) => onDragOver(e, day, index)}
            onDragEnd={onDragEnd}
          >
            <CardContent className="p-2 lg:p-3">
              <div className="flex items-start gap-1">
                {/* Drag Handle */}
                <div className="pt-1 text-muted-foreground">
                  <GripVertical className="w-4 h-4" />
                </div>
                
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{activity.title}</p>
                  
                  {/* Time Picker */}
                  <div className="flex items-center gap-1 mt-0.5 lg:mt-1">
                    <Clock className="w-3 h-3 text-muted-foreground" />
                    <select
                      value={activity.start_time}
                      onChange={(e) => onUpdateTime(activity.id, e.target.value)}
                      className="text-xs px-1 py-0.5 border rounded bg-background"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {TIME_SLOTS.map(slot => (
                        <option key={slot} value={slot}>{slot}</option>
                      ))}
                    </select>
                    <span className="text-xs text-muted-foreground">({activity.duration_minutes}m)</span>
                  </div>
                  
                  <Badge variant="outline" className="text-[10px] lg:text-xs mt-1 px-1 py-0">
                    {activity.type}
                  </Badge>
                </div>
                
                <div className="flex flex-col gap-1">
                  {/* Move dropdown */}
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

        {/* Add Activity Form */}
        {showAddForm ? (
          <Card className="border-dashed">
            <CardContent className="p-2 lg:p-3 space-y-2">
              <input
                type="text"
                placeholder="Activity name..."
                className="w-full px-2 py-1 text-sm border rounded"
                id={`new-activity-${day}`}
              />
              <div className="flex items-center gap-2">
                <Clock className="w-3 h-3 text-muted-foreground" />
                <select
                  value={newActivityTime}
                  onChange={(e) => setNewActivityTime(e.target.value)}
                  className="text-xs px-1 py-0.5 border rounded"
                >
                  {TIME_SLOTS.map(slot => (
                    <option key={slot} value={slot}>{slot}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  className="text-xs"
                  onClick={() => {
                    const input = document.getElementById(`new-activity-${day}`) as HTMLInputElement;
                    if (input.value) {
                      onAddActivity({
                        title: input.value,
                        start_time: newActivityTime,
                        duration_minutes: 60,
                        type: 'Activity',
                      });
                      input.value = '';
                      setShowAddForm(false);
                    }
                  }}
                >
                  Add
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs"
                  onClick={() => setShowAddForm(false)}
                >
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Button
            variant="outline"
            className="w-full h-12 lg:h-20 border-dashed text-xs lg:text-sm"
            onClick={() => setShowAddForm(true)}
          >
            <Plus className="w-3 h-3 lg:w-4 lg:h-4 mr-1 lg:mr-2" />
            Add Activity
          </Button>
        )}
      </div>
    </div>
  );
}

// Timeline View Component
function TimelineView({ 
  schedule, 
  onUpdateTime, 
  onRemoveActivity 
}: { 
  schedule: WeekSchedule;
  onUpdateTime: (day: typeof DAYS[number], id: string, time: string) => void;
  onRemoveActivity: (day: typeof DAYS[number], id: string) => void;
}) {
  const hours = Array.from({ length: 12 }, (_, i) => i + 7); // 7 AM to 6 PM

  return (
    <div className="p-4 min-w-[800px]">
      {/* Time header */}
      <div className="flex border-b mb-4">
        <div className="w-16"></div>
        {hours.map(hour => (
          <div key={hour} className="flex-1 text-center text-xs text-muted-foreground py-2">
            {hour > 12 ? hour - 12 : hour}:00 {hour >= 12 ? 'PM' : 'AM'}
          </div>
        ))}
      </div>

      {/* Days */}
      <div className="space-y-4">
        {DAYS.map(day => (
          <div key={day} className="flex">
            <div className="w-16 font-medium text-sm py-2">{DAY_LABELS[day]}</div>
            <div className="flex-1 relative h-20 border rounded-lg bg-muted/30">
              {/* Hour markers */}
              {hours.map((hour, i) => (
                <div 
                  key={hour} 
                  className="absolute top-0 bottom-0 border-l border-dashed border-muted"
                  style={{ left: `${(i / hours.length) * 100}%` }}
                />
              ))}

              {/* Activities */}
              {schedule[day].map(activity => {
                const [time, period] = activity.start_time.split(' ');
                const [h, m] = time.split(':').map(Number);
                const hour24 = period === 'PM' && h !== 12 ? h + 12 : h;
                const minutePercent = (m / 60) * (100 / hours.length);
                const hourIndex = hours.indexOf(hour24);
                const left = hourIndex >= 0 ? (hourIndex / hours.length) * 100 + minutePercent : 0;
                const width = (activity.duration_minutes / 60) * (100 / hours.length);

                return (
                  <div
                    key={activity.id}
                    className="absolute top-1 bottom-1 bg-primary/20 border border-primary rounded px-2 py-1 overflow-hidden cursor-pointer hover:bg-primary/30"
                    style={{ left: `${left}%`, width: `${Math.max(width, 8)}%` }}
                    onClick={() => onRemoveActivity(day, activity.id)}
                  >
                    <p className="text-xs font-medium truncate">{activity.title}</p>
                    <p className="text-[10px] text-muted-foreground">{activity.start_time}</p>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-muted-foreground mt-4">
        Click an activity in timeline to remove it
      </p>
    </div>
  );
}
