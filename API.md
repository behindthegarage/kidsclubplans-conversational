# KidsClubPlans Conversational API Documentation

## Base URL
```
Production: https://chat.kidsclubplans.app
Local: http://localhost:8000
```

## Authentication
All endpoints use session-based authentication via cookies. The first request establishes a session (`kcp_sid` cookie) that's used for subsequent requests.

---

## Core Endpoints

### Chat (Streaming)
```http
POST /chat
Content-Type: application/json

{
  "message": "string",
  "conversation_id": "string (optional)"
}
```

**Response:** Server-Sent Events (SSE)

**Event Types:**
```javascript
// Text content
{ "type": "content", "data": { "content": "..." } }

// Activity card
{ "type": "activity", "data": { "title": "...", "description": "..." } }

// Schedule
{ "type": "schedule", "data": { "date": "...", "activities": [...] } }

// Tool call
{ "type": "tool_call", "data": { "name": "...", "params": {} } }

// Stream complete
{ "type": "done", "data": { "conversation_id": "..." } }

// Error
{ "type": "error", "data": { "message": "..." } }
```

---

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-14T12:00:00Z"
}
```

---

## Activity Endpoints

### Save Activity
```http
POST /api/activities/save
Content-Type: application/json

{
  "title": "string",
  "description": "string",
  "instructions": "string",
  "age_group": "string (e.g., '6-10 years')",
  "duration_minutes": 30,
  "supplies": ["item1", "item2"],
  "activity_type": "string",
  "indoor_outdoor": "indoor|outdoor|either"
}
```

**Response:**
```json
{
  "success": true,
  "activity_id": "abc123",
  "message": "Activity saved successfully!",
  "searchable": true
}
```

---

## Schedule Endpoints

### Generate Schedule Template
```http
POST /api/schedule/generate
Content-Type: application/json

{
  "date": "2026-03-15",
  "age_group": "8-10 years",
  "duration_hours": 4,
  "preferences": {
    "start_time": "9:00 AM",
    "include_breaks": true
  },
  "include_weather": false,
  "location": "Lansing, MI (optional)"
}
```

**Response:**
```json
{
  "date": "2026-03-15",
  "age_group": "8-10 years",
  "duration_hours": 4,
  "template": [
    {
      "time": "9:00 AM",
      "type": "activity",
      "duration_minutes": 60,
      "needs_activity": true
    }
  ],
  "weather": { ... } // if include_weather=true
}
```

---

### Save Schedule
```http
POST /api/schedule/save
Content-Type: application/json

{
  "date": "2026-03-15",
  "title": "Spring Activity Day",
  "age_group": "8-10 years",
  "duration_hours": 4,
  "activities": [
    {
      "start_time": "9:00",
      "end_time": "10:00",
      "duration_minutes": 60,
      "title": "Morning Game",
      "description": "Fun ice breaker",
      "supplies_needed": ["balls", "cones"]
    }
  ]
}
```

**Response:**
```json
{
  "id": "uuid-string",
  "status": "saved"
}
```

---

### List Schedules
```http
GET /api/schedules?limit=10&offset=0
```

**Response:**
```json
{
  "schedules": [
    {
      "id": "uuid",
      "date": "2026-03-15",
      "title": "Spring Activity Day",
      "age_group": "8-10 years",
      "duration_hours": 4,
      "created_at": "2026-02-14T12:00:00Z"
    }
  ],
  "total": 5,
  "limit": 10,
  "offset": 0
}
```

---

### Get Schedule
```http
GET /api/schedule/{schedule_id}
```

**Response:**
```json
{
  "id": "uuid",
  "date": "2026-03-15",
  "title": "Spring Activity Day",
  "age_group": "8-10 years",
  "duration_hours": 4,
  "activities": [...],
  "created_at": "2026-02-14T12:00:00Z"
}
```

---

### Delete Schedule
```http
DELETE /api/schedule/{schedule_id}
```

**Response:**
```json
{
  "success": true,
  "message": "Schedule deleted"
}
```

---

## Weather Endpoints

### Check Weather
```http
POST /api/weather
Content-Type: application/json

{
  "location": "Lansing, MI",
  "date": "2026-03-15"
}
```

**Response:**
```json
{
  "date": "2026-03-15",
  "location": "Lansing, MI",
  "temperature": 72,
  "conditions": "sunny",
  "outdoor_suitable": true,
  "recommendation": "Great day for outdoor activities!"
}
```

---

## Error Responses

All errors follow this format:
```json
{
  "detail": "Error message"
}
```

**Common Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid input)
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error
- `503` - Service Unavailable (e.g., memory manager not initialized)

---

## Rate Limiting

- Chat endpoint: 10 requests per minute per session
- Other endpoints: 60 requests per minute per session

---

## Testing

Run the E2E test suite:
```bash
python3 tests/e2e_test.py
```

---

*Last updated: 2026-02-14*
