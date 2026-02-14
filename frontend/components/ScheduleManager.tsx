'use client';

import React, { useState, useEffect } from 'react';
import { Schedule, listSchedules, deleteSchedule, getSchedule } from '@/lib/api';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import {
  Calendar,
  Clock,
  Users,
  Trash2,
  ChevronRight,
  Loader2,
  CalendarDays,
  X,
  Printer,
  Package,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ScheduleManagerProps {
  onSelectSchedule?: (schedule: Schedule) => void;
  trigger?: React.ReactNode;
}

export function ScheduleManager({ onSelectSchedule, trigger }: ScheduleManagerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState<Schedule | null>(null);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSchedules = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await listSchedules(20, 0);
      setSchedules(response.schedules);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load schedules');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadSchedules();
    }
  }, [isOpen]);

  const handleDelete = async (scheduleId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setIsDeleting(scheduleId);
    try {
      await deleteSchedule(scheduleId);
      setSchedules((prev) => prev.filter((s) => s.id !== scheduleId));
      if (selectedSchedule?.id === scheduleId) {
        setSelectedSchedule(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete schedule');
    } finally {
      setIsDeleting(null);
    }
  };

  const handleView = async (schedule: Schedule) => {
    if (!schedule.id) {
      setError('Schedule ID is missing');
      return;
    }
    try {
      const fullSchedule = await getSchedule(schedule.id);
      setSelectedSchedule(fullSchedule);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load schedule');
    }
  };

  const handlePrint = () => {
    if (!selectedSchedule) return;
    
    // Create a printable window
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      setError('Popup blocked. Please allow popups to print.');
      return;
    }
    
    const activities = selectedSchedule.activities || [];
    const activitiesHtml = activities.map((a, i) => `
      <div style="margin-bottom: 15px; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
        <div style="font-weight: bold; color: #333;">${a.start_time} - ${a.title}</div>
        <div style="color: #666; font-size: 14px; margin-top: 5px;">${a.description || ''}</div>
        <div style="color: #999; font-size: 12px; margin-top: 5px;">${a.duration_minutes} minutes</div>
      </div>
    `).join('');
    
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>Schedule - ${selectedSchedule.date}</title>
        <style>
          body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
          h1 { color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }
          .meta { color: #666; margin-bottom: 20px; }
          @media print { body { padding: 0; } }
        </style>
      </head>
      <body>
        <h1>Schedule for ${formatDate(selectedSchedule.date)}</h1>
        <div class="meta">
          Age Group: ${selectedSchedule.age_group} | Duration: ${selectedSchedule.duration_hours} hours
        </div>
        ${activitiesHtml}
      </body>
      </html>
    `);
    
    printWindow.document.close();
    setTimeout(() => printWindow.print(), 100);
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr || dateStr === 'schedule_generated') return 'Generated Schedule';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const formatTime = (timeStr: string) => {
    if (!timeStr) return '';
    return timeStr;
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm">
            <CalendarDays className="w-4 h-4 mr-2" />
            My Schedules
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[80vh] p-0">
        <DialogHeader className="p-6 pb-0">
          <DialogTitle className="flex items-center gap-2">
            <CalendarDays className="w-5 h-5" />
            Saved Schedules
          </DialogTitle>
        </DialogHeader>

        {error && (
          <div className="mx-6 p-3 bg-red-50 text-red-600 text-sm rounded">
            {error}
          </div>
        )}

        {selectedSchedule ? (
          <div className="flex flex-col h-full">
            <div className="px-6 py-3 border-b flex items-center justify-between bg-muted/30">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedSchedule(null)}
              >
                ← Back to list
              </Button>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handlePrint}
                >
                  <Printer className="w-4 h-4 mr-1" />
                  Print
                </Button>
                {onSelectSchedule && (
                  <Button
                    size="sm"
                    onClick={() => {
                      onSelectSchedule(selectedSchedule);
                      setIsOpen(false);
                    }}
                  >
                    Load in Chat
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsOpen(false)}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>

            <ScrollArea className="flex-1 p-6">
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold">
                    Schedule for {formatDate(selectedSchedule.date)}
                  </h3>
                  <div className="flex flex-wrap gap-3 text-sm text-muted-foreground mt-2">
                    {selectedSchedule.date && (
                      <span className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {formatDate(selectedSchedule.date)}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Users className="w-4 h-4" />
                      {selectedSchedule.age_group}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {selectedSchedule.duration_hours} hours
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  {selectedSchedule.activities?.map((activity, index) => (
                    <div
                      key={index}
                      className={cn(
                        'p-3 rounded-lg border bg-card'
                      )}
                    >
                      <div className="flex items-start gap-3">
                        <span className="text-sm font-medium text-muted-foreground min-w-[60px]">
                          {activity.start_time}
                        </span>
                        <div className="flex-1">
                          <p className="font-medium">
                            {activity.title}
                          </p>
                          {activity.description && (
                            <p className="text-sm text-muted-foreground mt-1">
                              {activity.description}
                            </p>
                          )}
                          {activity.indoor_outdoor && (
                            <Badge variant="outline" className="mt-2 text-xs">
                              {activity.indoor_outdoor}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Supply Checklist */}
                {selectedSchedule.activities?.some(a => a.supplies_needed?.length) && (
                  <div className="border rounded-lg p-4 bg-muted/30">
                    <h4 className="font-medium flex items-center gap-2 mb-3">
                      <Package className="w-4 h-4" />
                      Supply Checklist
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {Array.from(new Set(
                        selectedSchedule.activities
                          ?.flatMap(a => a.supplies_needed || [])
                          .filter(Boolean)
                      )).sort().map((supply, i) => (
                        <label key={i} className="flex items-center gap-2 text-sm">
                          <input type="checkbox" className="rounded border-gray-300" />
                          <span>{supply}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
        ) : (
          <ScrollArea className="flex-1 p-6 pt-2">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : schedules.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <CalendarDays className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No saved schedules yet</p>
                <p className="text-sm mt-1">
                  Generate and save a schedule to see it here
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {schedules.map((schedule) => (
                  <div
                    key={schedule.id || Math.random()}
                    className="group flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 cursor-pointer transition-colors"
                    onClick={() => schedule.id && handleView(schedule)}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium truncate">
                          Schedule for {formatDate(schedule.date)}
                        </p>
                        <ChevronRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                      <div className="flex flex-wrap gap-3 text-sm text-muted-foreground mt-1">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {formatDate(schedule.date)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Users className="w-3 h-3" />
                          {schedule.age_group}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {schedule.duration_hours}h
                        </span>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:text-destructive"
                      onClick={(e) => schedule.id && handleDelete(schedule.id, e)}
                      disabled={isDeleting === schedule.id || !schedule.id}
                    >
                      {isDeleting === schedule.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        )}
      </DialogContent>
    </Dialog>
  );
}
