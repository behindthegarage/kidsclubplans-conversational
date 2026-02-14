'use client';

import React, { useState, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Send, Mic } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  disabled?: boolean;
}

export function ChatInput({
  onSend,
  isLoading = false,
  placeholder = 'Ask about activities, planning, or schedule...',
  disabled = false,
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    if (!input.trim() || isLoading || disabled) return;
    onSend(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [input, isLoading, disabled, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        200
      )}px`;
    }
  };

  return (
    <div className="relative flex items-end gap-2 p-4 bg-background border-t">
      {/* Voice input button (Whisper integration point) */}
      <Button
        variant="ghost"
        size="icon"
        className="shrink-0 h-10 w-10 rounded-full"
        disabled={isLoading || disabled}
        title="Voice input (coming soon)"
        onClick={() => {
          // Whisper integration point
          console.log('Voice input clicked - integrate Whisper here');
        }}
      >
        <Mic className="w-5 h-5 text-muted-foreground" />
      </Button>

      {/* Text input */}
      <div className="relative flex-1">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isLoading || disabled}
          rows={1}
          className={cn(
            'w-full resize-none rounded-2xl border border-input bg-background px-4 py-3 pr-12 text-sm ring-offset-background',
            'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'min-h-[44px] max-h-[200px]'
          )}
        />
      </div>

      {/* Send button */}
      <Button
        onClick={handleSend}
        disabled={!input.trim() || isLoading || disabled}
        size="icon"
        className={cn(
          'shrink-0 h-10 w-10 rounded-full transition-all',
          input.trim() && !isLoading && !disabled
            ? 'opacity-100 scale-100'
            : 'opacity-50 scale-95'
        )}
      >
        <Send className="w-4 h-4" />
      </Button>
    </div>
  );
}
