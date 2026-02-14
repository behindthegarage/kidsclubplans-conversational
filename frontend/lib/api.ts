/** @format */

export interface Activity {
  id: number;
  title: string;
  type: string | null;
  description: string | null;
  supplies: string | null;
  instructions: string | null;
  source: string | null;
  to_do?: boolean;
  development_age_group?: string;
  development_group_justification?: string;
  adaptations?: string;
  score?: number;
  // Phase 4: Generated activities
  generated?: boolean;
  supply_based?: boolean;
  blended?: boolean;
  novelty_score?: number;
  target_age?: string;
  duration_minutes?: number;
}

export interface ScheduleActivity {
  activity_id?: string;
  title: string;
  description?: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  activity_type?: string;
  supplies_needed?: string[];
  indoor_outdoor?: 'indoor' | 'outdoor' | 'either';
  notes?: string;
}

export interface WeatherData {
  location: string;
  date: string;
  temperature_f?: number;
  temperature_c?: number;
  conditions: string;
  description?: string;
  precipitation_chance?: number;
  humidity?: number;
  wind_speed?: number;
  outdoor_suitable: boolean;
  uv_index?: number;
  cached_at?: string;
}

export interface Schedule {
  id?: string;
  date: string;
  age_group: string;
  duration_hours: number;
  location?: string;
  weather?: WeatherData;
  activities: ScheduleActivity[];
  outdoor_suitable?: boolean;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  activities?: Activity[];
  schedule?: Schedule;
  toolCalls?: ToolCall[];
  timestamp: Date;
  isStreaming?: boolean;
}

export interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
  result?: unknown;
}

export type ChatResponseChunk =
  | { type: 'content'; data: { content: string } }
  | { type: 'activity'; data: Activity }
  | { type: 'schedule'; data: Schedule }
  | { type: 'tool_call'; data: ToolCall }
  | { type: 'metadata'; data: { conversation_id?: string; [key: string]: unknown } }
  | { type: 'done'; data: { conversation_id?: string } }
  | { type: 'error'; data: { message: string } };

export interface StreamChatOptions {
  onActivity?: (activity: Activity) => void;
  onSchedule?: (schedule: Schedule) => void;
  onToolCall?: (toolCall: ToolCall) => void;
  onMetadata?: (data: { conversation_id?: string }) => void;
  signal?: AbortSignal;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function isRetryableError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  const msg = error.message.toLowerCase();
  return (
    msg.includes('failed to fetch') ||
    msg.includes('networkerror') ||
    msg.includes('network error') ||
    msg.includes('http error! status: 502') ||
    msg.includes('http error! status: 503') ||
    msg.includes('http error! status: 504')
  );
}

export async function* streamChat(
  message: string,
  conversationId?: string,
  options: StreamChatOptions = {}
): AsyncGenerator<string, void, unknown> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const response = await fetch(`${apiUrl}/chat`, {
    method: 'POST',
    credentials: 'include',
    signal: options.signal,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  if (!response.body) {
    throw new Error('Response body is null');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data: ')) continue;

        const data = trimmed.slice(6);
        if (data === '[DONE]') continue;

        try {
          const parsed = JSON.parse(data) as ChatResponseChunk;

          if (parsed.type === 'content') {
            yield parsed.data.content;
          } else if (parsed.type === 'activity') {
            options.onActivity?.(parsed.data);
          } else if (parsed.type === 'schedule') {
            options.onSchedule?.(parsed.data);
          } else if (parsed.type === 'tool_call') {
            options.onToolCall?.(parsed.data);
          } else if (parsed.type === 'metadata' || parsed.type === 'done') {
            options.onMetadata?.(parsed.data);
          } else if (parsed.type === 'error') {
            throw new Error(parsed.data.message || 'Unknown stream error');
          }
        } catch (e) {
          console.error('Failed to parse SSE data:', e);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function* streamChatWithRetry(
  message: string,
  conversationId?: string,
  options: StreamChatOptions = {},
  maxRetries = 2
): AsyncGenerator<string, void, unknown> {
  let attempt = 0;
  while (attempt <= maxRetries) {
    try {
      yield* streamChat(message, conversationId, options);
      return;
    } catch (err) {
      if (options.signal?.aborted) {
        throw err;
      }
      if (attempt >= maxRetries || !isRetryableError(err)) {
        throw err;
      }
      await sleep(500 * 2 ** attempt);
      attempt += 1;
    }
  }
}

export async function searchActivities(
  query: string,
  topK: number = 5,
  activityType?: string
): Promise<Activity[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const response = await fetch(`${apiUrl}/activities/search`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      top_k: topK,
      activity_type: activityType,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const data = await response.json();
  return data.activities || [];
}

export async function getActivity(id: number): Promise<Activity | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const response = await fetch(`${apiUrl}/activities/${id}`, { credentials: 'include' });

  if (!response.ok) {
    if (response.status === 404) return null;
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// Phase 3: Weather and Schedule API

export interface WeatherRequest {
  location?: string;
  date?: string;
}

export async function getWeather(request: WeatherRequest): Promise<WeatherData> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const response = await fetch(`${apiUrl}/api/weather`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Weather API error! status: ${response.status}`);
  }

  return response.json();
}

export interface ScheduleGenerateRequest {
  date: string;
  age_group: string;
  duration_hours: number;
  preferences?: Record<string, unknown>;
  location?: string;
  include_weather?: boolean;
}

export async function generateSchedule(
  request: ScheduleGenerateRequest
): Promise<Schedule> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const response = await fetch(`${apiUrl}/api/schedule/generate`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Schedule API error! status: ${response.status}`);
  }

  return response.json();
}

export interface ScheduleSaveRequest {
  date: string;
  title?: string;
  age_group?: string;
  duration_hours?: number;
  activities: ScheduleActivity[];
  preferences?: Record<string, unknown>;
}

export async function saveSchedule(
  request: ScheduleSaveRequest
): Promise<{ id: string; status: string }> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const response = await fetch(`${apiUrl}/api/schedule/save`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Save schedule API error! status: ${response.status}`);
  }

  return response.json();
}

export async function getSchedule(scheduleId: string): Promise<Schedule> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const response = await fetch(`${apiUrl}/api/schedule/${scheduleId}`, {
    credentials: 'include',
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Schedule not found');
    }
    throw new Error(`Get schedule API error! status: ${response.status}`);
  }

  return response.json();
}
