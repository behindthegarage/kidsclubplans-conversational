'use client';

import { WeeklyScheduler } from '@/components/WeeklyScheduler';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Button } from '@/components/ui/button';
import { MessageSquare, LayoutGrid, Menu } from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from "@/components/ui/sheet";
import { useRouter } from 'next/navigation';

export default function SchedulePage() {
  const router = useRouter();
  
  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b bg-card">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push('/')}
            className="font-semibold"
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            Chat
          </Button>
          <span className="text-muted-foreground hidden sm:inline">|</span>
          <span className="font-semibold text-sm hidden sm:inline">Weekly Schedule</span>
        </div>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push('/activities')}
            className="hidden sm:flex"
          >
            <LayoutGrid className="w-4 h-4 mr-1" />
            Activities
          </Button>
          
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="sm" className="sm:hidden">
                <Menu className="w-5 h-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[200px]">
              <div className="flex flex-col gap-2 mt-4">
                <Button
                  variant="ghost"
                  className="justify-start"
                  onClick={() => router.push('/')}
                >
                  <MessageSquare className="w-4 h-4 mr-2" />
                  Chat
                </Button>
                <Button
                  variant="ghost"
                  className="justify-start"
                  onClick={() => router.push('/activities')}
                >
                  <LayoutGrid className="w-4 h-4 mr-2" />
                  Activities
                </Button>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </header>

      <div className="flex-1 overflow-hidden">
        <WeeklyScheduler />
      </div>
    </div>
  );
}
