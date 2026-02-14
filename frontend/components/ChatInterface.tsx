'use client';

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Message, Activity, ToolCall, streamChatWithRetry } from '@/lib/api';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Trash2, Sparkles } from 'lucide-react';

const WELCOME = `👋 Hi! I'm your KidsClubPlans assistant. I can help you:

• Find activities for any age group or theme
• Plan schedules and get weather-aware suggestions
• Generate complete activity plans
• Answer questions about supplies, adaptations, and more

What would you like help with today?`;

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: WELCOME,
      timestamp: new Date(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [currentStreamId, setCurrentStreamId] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    return () => {
      activeAbortRef.current?.abort();
    };
  }, []);

  const cancelCurrentStream = useCallback(() => {
    activeAbortRef.current?.abort();
    setIsLoading(false);
    if (currentStreamId) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === currentStreamId
            ? { ...msg, isStreaming: false, content: msg.content + '\n\n⏹️ Stopped.' }
            : msg
        )
      );
    }
  }, [currentStreamId]);

  const handleSend = useCallback(
    async (content: string) => {
      // Cancel any in-flight stream to avoid races/token waste
      if (activeAbortRef.current) {
        activeAbortRef.current.abort();
      }

      const abortController = new AbortController();
      activeAbortRef.current = abortController;

      const userMessage: Message = {
        id: uuidv4(),
        role: 'user',
        content,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      const assistantMessageId = uuidv4();
      setCurrentStreamId(assistantMessageId);

      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        activities: [],
        toolCalls: [],
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      const collectedActivities: Activity[] = [];
      const collectedToolCalls: ToolCall[] = [];

      try {
        for await (const chunk of streamChatWithRetry(
          content,
          conversationId,
          {
            signal: abortController.signal,
            onActivity: (activity) => {
              collectedActivities.push(activity);
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId ? { ...msg, activities: [...collectedActivities] } : msg
                )
              );
            },
            onToolCall: (toolCall) => {
              collectedToolCalls.push(toolCall);
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId ? { ...msg, toolCalls: [...collectedToolCalls] } : msg
                )
              );
            },
            onMetadata: (metadata) => {
              if (metadata?.conversation_id) {
                setConversationId(metadata.conversation_id);
              }
            },
          },
          2
        )) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId ? { ...msg, content: msg.content + chunk } : msg
            )
          );
        }
      } catch (error) {
        if (abortController.signal.aborted) {
          // expected when user cancels
        } else {
          console.error('Chat error:', error);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    content: msg.content + '\n\n❌ Sorry, there was an error. Please try again.',
                  }
                : msg
            )
          );
        }
      } finally {
        setIsLoading(false);
        setCurrentStreamId(null);
        if (activeAbortRef.current === abortController) {
          activeAbortRef.current = null;
        }
        setMessages((prev) =>
          prev.map((msg) => (msg.id === assistantMessageId ? { ...msg, isStreaming: false } : msg))
        );
      }
    },
    [conversationId]
  );

  const handleClear = useCallback(() => {
    activeAbortRef.current?.abort();
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content: WELCOME,
        timestamp: new Date(),
      },
    ]);
    setConversationId(undefined);
    setCurrentStreamId(null);
    setIsLoading(false);
  }, []);

  return (
    <div className="flex flex-col h-full bg-background">
      <header className="flex items-center justify-between px-4 py-3 border-b bg-card">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-primary-foreground" />
          </div>
          <div>
            <h1 className="font-semibold text-sm">KidsClubPlans Assistant</h1>
            <p className="text-xs text-muted-foreground">AI-powered activity planning</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isLoading && (
            <Button variant="secondary" size="sm" onClick={cancelCurrentStream}>
              Stop
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClear}
            disabled={isLoading}
            className="text-muted-foreground hover:text-foreground"
          >
            <Trash2 className="w-4 h-4 mr-1" />
            Clear
          </Button>
        </div>
      </header>

      <ScrollArea className="flex-1 px-4" ref={scrollRef}>
        <div className="py-4 space-y-1">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      <ChatInput
        onSend={handleSend}
        isLoading={isLoading}
        placeholder="Ask about activities, planning, or schedules..."
      />
    </div>
  );
}
