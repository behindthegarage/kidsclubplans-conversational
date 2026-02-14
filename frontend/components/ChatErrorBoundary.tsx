'use client';

import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
}

export class ChatErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('Chat UI crashed:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="h-screen w-full overflow-hidden flex items-center justify-center">
          <div className="max-w-md text-center space-y-4 p-6 rounded-xl border bg-card">
            <AlertTriangle className="w-8 h-8 mx-auto text-yellow-500" />
            <h2 className="text-lg font-semibold">Chat hit an error</h2>
            <p className="text-sm text-muted-foreground">
              Good news: this is recoverable. Reload to continue.
            </p>
            <Button onClick={() => window.location.reload()}>Reload app</Button>
          </div>
        </main>
      );
    }

    return this.props.children;
  }
}
