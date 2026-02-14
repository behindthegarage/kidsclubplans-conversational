'use client';

import React, { useState } from 'react';
import { ScheduleActivity, WeatherData } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Clock, 
  Sun, 
  Cloud, 
  CloudRain, 
  Snowflake, 
  Wind,
  Thermometer,
  MapPin,
  Save,
  Download,
  Plus,
  ArrowRightLeft
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ScheduleViewProps {
  schedule: {
    date: string;
    age_group: string;
    duration_hours: number;
    location?: string;
    weather?: WeatherData;
    activities: ScheduleActivity[];
    outdoor_suitable?: boolean;
  };
  onSave?: () => void;
  onSwapActivity?: (index: number) => void;
  onAddActivity?: (afterIndex: number) => void;
}

export function ScheduleView({ 
  schedule, 
  onSave, 
  onSwapActivity, 
  onAddActivity 
}: ScheduleViewProps) {
  const [expandedActivity, setExpandedActivity] = useState<number | null>(null);

  const getWeatherIcon = (condition?: string) => {
    switch (condition?.toLowerCase()) {
      case 'sunny':
      case 'clear':
        return <Sun className="w-5 h-5 text-yellow-500" />;
      case 'cloudy':
      case 'partly cloudy':
        return <Cloud className="w-5 h-5 text-gray-500" />;
      case 'rain':
      case 'drizzle':
        return <CloudRain className="w-5 h-5 text-blue-500" />;
      case 'snow':
        return <Snowflake className="w-5 h-5 text-blue-300" />;
      case 'windy':
        return <Wind className="w-5 h-5 text-gray-400" />;
      default:
        return <Sun className="w-5 h-5 text-yellow-500" />;
    }
  };

  const getActivityTypeColor = (type?: string) => {
    const colors: Record<string, string> = {
      'Physical': 'bg-orange-100 text-orange-800',
      'STEM': 'bg-blue-100 text-blue-800',
      'Arts & Crafts': 'bg-purple-100 text-purple-800',
      'Art': 'bg-purple-100 text-purple-800',
      'Team Building': 'bg-green-100 text-green-800',
      'Nature': 'bg-emerald-100 text-emerald-800',
      'Indoor Game': 'bg-indigo-100 text-indigo-800',
      'Outdoor Game': 'bg-sky-100 text-sky-800',
      'Social-Emotional': 'bg-rose-100 text-rose-800',
      'Break': 'bg-gray-100 text-gray-800',
      'Free Play': 'bg-amber-100 text-amber-800',
    };
    return colors[type || ''] || 'bg-gray-100 text-gray-800';
  };

  const formatTime = (time: string) => {
    try {
      const [hours, minutes] = time.split(':');
      const hour = parseInt(hours);
      const ampm = hour >= 12 ? 'PM' : 'AM';
      const displayHour = hour % 12 || 12;
      return `${displayHour}:${minutes} ${ampm}`;
    } catch {
      return time;
    }
  };

  const handleExport = () => {
    const scheduleText = generateScheduleText(schedule);
    const blob = new Blob([scheduleText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `schedule-${schedule.date}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-xl flex items-center gap-2">
              <Clock className="w-5 h-5 text-primary" />
              Daily Schedule
            </CardTitle>
            <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                {schedule.date}
              </span>
              <Badge variant="secondary">{schedule.age_group}</Badge>
              <Badge variant="outline">{schedule.duration_hours} hours</Badge>
              {schedule.location && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-4 h-4" />
                  {schedule.location}
                </span>
              )}
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {onSave && (
              <Button variant="outline" size="sm" onClick={onSave}>
                <Save className="w-4 h-4 mr-1" />
                Save
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="w-4 h-4 mr-1" />
              Export
            </Button>
          </div>
        </div>

        {/* Weather Banner */}
        {schedule.weather && (
          <div className={cn(
            "mt-4 p-3 rounded-lg flex items-center gap-4",
            schedule.weather.outdoor_suitable 
              ? "bg-green-50 border border-green-200" 
              : "bg-amber-50 border border-amber-200"
          )}>
            <div className="flex items-center gap-2">
              {getWeatherIcon(schedule.weather.conditions)}
              <span className="font-medium capitalize">
                {schedule.weather.conditions}
              </span>
            </div>
            
            {schedule.weather.temperature_f && (
              <div className="flex items-center gap-1 text-sm">
                <Thermometer className="w-4 h-4" />
                {Math.round(schedule.weather.temperature_f)}°F
              </div>
            )}
            
            {schedule.weather.precipitation_chance !== undefined && (
              <div className="text-sm text-muted-foreground">
                {schedule.weather.precipitation_chance}% rain
              </div>
            )}
            
            <div className="ml-auto text-sm">
              {schedule.weather.outdoor_suitable ? (
                <span className="text-green-700">✓ Outdoor activities suitable</span>
              ) : (
                <span className="text-amber-700">⚠ Indoor activities recommended</span>
              )}
            </div>
          </div>
        )}
      </CardHeader>

      <CardContent>
        <div className="space-y-3">
          {schedule.activities.map((activity, index) => (
            <div
              key={index}
              className={cn(
                "relative pl-6 pb-4 border-l-2",
                index === schedule.activities.length - 1 ? "" : "border-muted",
                activity.indoor_outdoor === 'outdoor' && schedule.weather?.outdoor_suitable === false
                  ? "opacity-60"
                  : ""
              )}
            >
              {/* Timeline dot */}
              <div className={cn(
                "absolute -left-[5px] top-1 w-2.5 h-2.5 rounded-full border-2 border-background",
                activity.activity_type === 'Break' 
                  ? "bg-gray-400" 
                  : activity.indoor_outdoor === 'outdoor'
                    ? "bg-green-500"
                    : "bg-blue-500"
              )} />
              
              <div 
                className={cn(
                  "p-3 rounded-lg border cursor-pointer transition-colors",
                  expandedActivity === index 
                    ? "bg-muted/50 border-primary/50" 
                    : "bg-card hover:bg-muted/30"
                )}
                onClick={() => setExpandedActivity(
                  expandedActivity === index ? null : index
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-sm text-muted-foreground">
                        {formatTime(activity.start_time)} - {formatTime(activity.end_time)}
                      </span>
                      
                      {activity.activity_type && (
                        <Badge 
                          variant="secondary" 
                          className={`text-xs ${getActivityTypeColor(activity.activity_type)}`}
                        >
                          {activity.activity_type}
                        </Badge>
                      )}
                      
                      {activity.indoor_outdoor && (
                        <Badge variant="outline" className="text-xs">
                          {activity.indoor_outdoor === 'indoor' && '🏠 Indoor'}
                          {activity.indoor_outdoor === 'outdoor' && '🌳 Outdoor'}
                          {activity.indoor_outdoor === 'either' && '🏠/🌳 Either'}
                        </Badge>
                      )}
                    </div>
                    
                    <h4 className="font-medium mt-1">{activity.title}</h4>
                    
                    {activity.description && (
                      <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                        {activity.description}
                      </p>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-1">
                    {onSwapActivity && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSwapActivity(index);
                        }}
                        title="Swap activity"
                      >
                        <ArrowRightLeft className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>

                {/* Expanded details */}
                {expandedActivity === index && (
                  <div className="mt-3 pt-3 border-t space-y-2">
                    {activity.supplies_needed && activity.supplies_needed.length > 0 && (
                      <div>
                        <span className="text-sm font-medium">Supplies: </span>
                        <span className="text-sm text-muted-foreground">
                          {activity.supplies_needed.join(', ')}
                        </span>
                      </div>
                    )}
                    
                    {activity.notes && (
                      <div className="text-sm text-muted-foreground">
                        <span className="font-medium">Notes: </span>
                        {activity.notes}
                      </div>
                    )}
                    
                    {onAddActivity && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="mt-2"
                        onClick={(e) => {
                          e.stopPropagation();
                          onAddActivity(index);
                        }}
                      >
                        <Plus className="w-4 h-4 mr-1" />
                        Add activity after this
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function generateScheduleText(schedule: ScheduleViewProps['schedule']): string {
  const lines = [
    `DAILY SCHEDULE - ${schedule.date}`,
    `Age Group: ${schedule.age_group}`,
    `Duration: ${schedule.duration_hours} hours`,
    ''
  ];

  if (schedule.weather) {
    lines.push(
      'WEATHER:',
      `  Conditions: ${schedule.weather.conditions}`,
      `  Temperature: ${Math.round(schedule.weather.temperature_f || 0)}°F`,
      `  Outdoor Suitable: ${schedule.weather.outdoor_suitable ? 'Yes' : 'No'}`,
      ''
    );
  }

  lines.push('ACTIVITIES:');
  lines.push('');

  schedule.activities.forEach((activity, i) => {
    lines.push(`${i + 1}. ${activity.title}`);
    lines.push(`   Time: ${activity.start_time} - ${activity.end_time}`);
    lines.push(`   Duration: ${activity.duration_minutes} minutes`);
    if (activity.activity_type) {
      lines.push(`   Type: ${activity.activity_type}`);
    }
    if (activity.indoor_outdoor) {
      lines.push(`   Location: ${activity.indoor_outdoor}`);
    }
    if (activity.description) {
      lines.push(`   Description: ${activity.description}`);
    }
    lines.push('');
  });

  return lines.join('\n');
}
