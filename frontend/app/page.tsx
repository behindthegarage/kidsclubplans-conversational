import { ChatInterface } from '@/components/ChatInterface';
import { ChatErrorBoundary } from '@/components/ChatErrorBoundary';

export default function Home() {
  return (
    <ChatErrorBoundary>
      <main className="h-screen w-full overflow-hidden">
        <ChatInterface />
      </main>
    </ChatErrorBoundary>
  );
}
