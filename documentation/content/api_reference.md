# Public Event API Reference

**District Suite API for website integration**

> [!NOTE]
> This API enables partner districts to embed their event listings on external websites. The API is **read-only** and requires authentication via API key.

## Overview

| Aspect | Value |
|--------|-------|
| **Base URL** | `/api/v1/district/{tenant_slug}` |
| **Authentication** | API Key (header) |
| **Format** | JSON |
| **Methods** | GET only |

## Authentication

All API requests require an API key passed in the `X-API-Key` header.

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  https://polaris.prepkc.org/api/v1/district/kckps/events
```

### Obtaining Your API Key

1. Log in to your district portal as an administrator
2. Navigate to **Settings** → **API Settings**
3. Click **Generate API Key** or copy existing key
4. Store the key securely (it won't be shown again)

### Key Rotation

To rotate your API key:
1. Go to **Settings** → **API Settings**
2. Click **Rotate Key**
3. Update your integration with the new key immediately

> [!WARNING]
> The old key is immediately invalidated upon rotation. Update your integration before rotating.

---

## Endpoints

### GET /events

List all published events for the tenant.

**Request:**
```http
GET /api/v1/district/{tenant_slug}/events
X-API-Key: YOUR_API_KEY
```

**Query Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `page` | integer | Page number | 1 |
| `per_page` | integer | Results per page (max 50) | 20 |
| `status` | string | Filter by status (`published`, `completed`) | `published` |
| `from_date` | string | Events on or after (YYYY-MM-DD) | — |
| `to_date` | string | Events on or before (YYYY-MM-DD) | — |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "slug": "career-day-2026-01-15",
      "title": "Career Day at Central High",
      "description": "Join us for a career exploration day...",
      "event_type": "career_fair",
      "date": "2026-01-15",
      "start_time": "09:00",
      "end_time": "14:00",
      "location": "123 Main St, Kansas City, KS 66101",
      "school": "Central High School",
      "volunteers_needed": 10,
      "volunteers_registered": 4,
      "signup_url": "https://polaris.prepkc.org/signup/kckps/career-day-2026-01-15",
      "status": "published"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 45,
    "total_pages": 3
  }
}
```

---

### GET /events/{slug}

Get details for a single event.

**Request:**
```http
GET /api/v1/district/{tenant_slug}/events/{slug}
X-API-Key: YOUR_API_KEY
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "slug": "career-day-2026-01-15",
    "title": "Career Day at Central High",
    "description": "Join us for a career exploration day featuring professionals from various industries...",
    "event_type": "career_fair",
    "date": "2026-01-15",
    "start_time": "09:00",
    "end_time": "14:00",
    "duration_minutes": 300,
    "location": "123 Main St, Kansas City, KS 66101",
    "school": "Central High School",
    "district": "KCKPS",
    "volunteers_needed": 10,
    "volunteers_registered": 4,
    "signup_url": "https://polaris.prepkc.org/signup/kckps/career-day-2026-01-15",
    "registration_deadline": "2026-01-14T23:59:00Z",
    "additional_info": "Please arrive 15 minutes early for check-in.",
    "status": "published",
    "created_at": "2026-01-01T10:00:00Z",
    "updated_at": "2026-01-10T15:30:00Z"
  }
}
```

---

## Rate Limiting

API requests are rate-limited per API key:

| Limit | Threshold |
|-------|-----------|
| Per minute | 60 requests |
| Per hour | 1,000 requests |
| Per day | 10,000 requests |

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1706284800
```

**Exceeded Response (HTTP 429):**
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

---

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "error": "Error message here",
  "code": "ERROR_CODE"
}
```

### Error Codes

| HTTP Code | Error Code | Description |
|-----------|-----------|-------------|
| 400 | `BAD_REQUEST` | Invalid request parameters |
| 401 | `UNAUTHORIZED` | Missing or invalid API key |
| 403 | `FORBIDDEN` | API key does not have access |
| 404 | `NOT_FOUND` | Resource not found |
| 429 | `RATE_LIMITED` | Rate limit exceeded |
| 500 | `SERVER_ERROR` | Internal server error |

---

## CORS

The API supports Cross-Origin Resource Sharing (CORS) for browser-based integrations.

**Allowed Methods:** `GET`, `OPTIONS`
**Allowed Headers:** `X-API-Key`, `Content-Type`
**Allowed Origins:** Configured per tenant (contact your administrator)

---

## Example Integrations

### JavaScript (Fetch)

```javascript
async function getEvents() {
  const response = await fetch(
    'https://polaris.prepkc.org/api/v1/district/kckps/events',
    {
      headers: {
        'X-API-Key': 'YOUR_API_KEY'
      }
    }
  );

  const data = await response.json();

  if (data.success) {
    data.data.forEach(event => {
      console.log(`${event.title} - ${event.date}`);
    });
  }
}
```

### JavaScript (Embed on Website)

```html
<div id="event-list"></div>

<script>
  const API_KEY = 'YOUR_API_KEY';
  const TENANT = 'kckps';

  fetch(`https://polaris.prepkc.org/api/v1/district/${TENANT}/events`, {
    headers: { 'X-API-Key': API_KEY }
  })
  .then(res => res.json())
  .then(data => {
    if (!data.success) return;

    const container = document.getElementById('event-list');
    container.innerHTML = data.data.map(event => `
      <div class="event-card">
        <h3>${event.title}</h3>
        <p>${event.date} at ${event.location}</p>
        <p>Volunteers needed: ${event.volunteers_needed - event.volunteers_registered}</p>
        <a href="${event.signup_url}" target="_blank">Sign Up</a>
      </div>
    `).join('');
  });
</script>
```

### cURL

```bash
# List events
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://polaris.prepkc.org/api/v1/district/kckps/events?per_page=10"

# Get single event
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://polaris.prepkc.org/api/v1/district/kckps/events/career-day-2026-01-15"
```

---

## Related Documentation

- **Requirements:** [FR-API-101](requirements#fr-api-101) through [FR-API-108](requirements#fr-api-108)
- **User Stories:** [US-1201](user_stories#us-1201), [US-1202](user_stories#us-1202)
- **Use Cases:** [UC-17](use_cases#uc-17)
- **Architecture:** [Public Event API Architecture](architecture#public-event-api-architecture-district-suite)

---

*Last updated: January 2026*
*Version: 1.0*
