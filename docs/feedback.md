# AGC Feedback Engine — AGC-100.4

Lightweight in-app feedback collected after a highlight generation completes.

---

## Database Schema

**Table: `feedback`**

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `user_id` | INTEGER NOT NULL | Scoped to authenticated user |
| `project_id` | INTEGER | Nullable — links to `projects.id` |
| `rating` | INTEGER | 1–5 stars, nullable |
| `thumbs` | TEXT | `"up"` \| `"down"` \| NULL |
| `comment` | TEXT | Free text, max 2 000 chars, nullable |
| `created_at` | TEXT | ISO 8601 UTC timestamp |

All rows are scoped to `user_id`. Queries enforce ownership on every read and delete.

---

## API

All endpoints require a valid `Authorization: Bearer <token>` header.

### POST /feedback

Submit feedback for the authenticated user.

**Request body**
```json
{
  "project_id": 42,
  "rating": 4,
  "thumbs": "up",
  "comment": "Great clips!"
}
```
All fields are optional. `rating` must be 1–5 if provided. `thumbs` must be `"up"` or `"down"` if provided. `comment` is truncated to 2 000 characters by validation.

**Response**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "user_id": 7,
    "project_id": 42,
    "rating": 4,
    "thumbs": "up",
    "comment": "Great clips!",
    "created_at": "2026-07-01T12:00:00+00:00"
  }
}
```

### GET /feedback

List all feedback submitted by the authenticated user, newest first.

**Response**
```json
{
  "success": true,
  "count": 3,
  "data": [ /* FeedbackItem[] */ ]
}
```

### DELETE /feedback/{id}

Delete a feedback record owned by the authenticated user.

**Response**
```json
{ "success": true, "message": "Feedback deleted" }
```

Returns `404` if the record does not exist or belongs to another user.

---

## Analytics Events

Events are sent to PostHog via `track()` in `services/analytics.ts`. Comment text is **never** included.

| Event | Trigger | Properties |
|---|---|---|
| `Feedback Opened` | Pipeline result appears in the UI | — |
| `Feedback Submitted` | User clicks Submit | `rating`, `thumbs` |
| `Feedback Skipped` | User clicks Skip | — |

---

## UX Flow

1. Pipeline completes → `result` becomes non-null in `usePipeline`.
2. Dashboard detects the new result via `useEffect` → fires `Feedback Opened`, resets dismissed state.
3. `FeedbackCard` renders inline below `ResultPanel` (no modal, no page refresh).
4. User picks a star rating and/or thumbs, optionally types a comment, then clicks **Submit** or **Skip**.
5. On Submit: API call is made; card disappears regardless of outcome (non-critical).
6. On Skip: card disappears immediately, no API call.
7. Card does not re-appear until the next pipeline completion.

---

## Future Roadmap

- Admin dashboard to view and filter feedback by rating, thumbs, date, and project.
- Export to CSV for offline analysis.
- Automated alerts when average rating drops below a threshold.
- Associate feedback with specific highlight clips, not just projects.
- Sentiment analysis on comment text.
