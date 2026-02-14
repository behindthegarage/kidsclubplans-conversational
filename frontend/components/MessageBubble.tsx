'use client';

import React from 'react';
import { Message } from '@/lib/api';
import { ActivityCard } from './ActivityCard';
import { User, Bot, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex gap-3 mb-4 animate-fade-in',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center shrink-0',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-secondary text-secondary-foreground'
        )}
      >
        {isUser ? (
          <User className="w-4 h-4" />
        ) : message.isStreaming ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Bot className="w-4 h-4" />
        )}
      </div>

      {/* Message Content */}
      <div
        className={cn(
          'flex flex-col max-w-[80%]',
          isUser ? 'items-end' : 'items-start'
        )}
      >
        {/* Text Bubble */}
        <div
          className={cn(
            'px-4 py-2.5 rounded-2xl text-sm leading-relaxed',
            isUser
              ? 'bg-primary text-primary-foreground rounded-tr-sm'
              : 'bg-muted text-foreground rounded-tl-sm'
          )}
        >
          {message.content}
          {message.isStreaming && (
            <span className="inline-block w-1.5 h-4 ml-1 bg-current animate-pulse-opacity rounded-sm" />
          )}
        </div>

        {/* Activity Cards */}
        {message.activities && message.activities.length > 0 && (
          <div className="w-full mt-3 space-y-2">
            <p className="text-xs font-medium text-muted-foreground mb-2">
              Found activities:
            </p>
            {message.activities.map((activity) => (
              <ActivityCard key={activity.id} activity={activity} />
            ))}
          </div>
        )}

        {/* Tool Calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {message.toolCalls.map((toolCall, idx) => (
              <span
                key={idx}
                className="text-xs px-2 py-1 bg-secondary/50 rounded text-muted-foreground"
              >
                🔧 {toolCall.name}
              </span>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <span className="text-xs text-muted-foreground mt-1">
          {message.timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>
    </div>
  );
}
