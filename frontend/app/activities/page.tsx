import { ActivityBrowser } from '@/components/ActivityBrowser';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Browse Activities - KidsClubPlans',
  description: 'Search and browse activities for your summer camp planning',
};

export default function ActivitiesPage() {
  return (
    <div className="h-[calc(100vh-4rem)]">
      <ActivityBrowser />
    </div>
  );
}
