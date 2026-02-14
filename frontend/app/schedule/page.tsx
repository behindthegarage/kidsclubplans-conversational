import { WeeklyScheduler } from '@/components/WeeklyScheduler';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Weekly Schedule - KidsClubPlans',
  description: 'Plan your summer camp week by week',
};

export default function SchedulePage() {
  return (
    <div className="h-[calc(100vh-4rem)]">
      <WeeklyScheduler />
    </div>
  );
}
