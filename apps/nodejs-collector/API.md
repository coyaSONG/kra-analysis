# KRA Data Collector API Reference

Complete API reference for the KRA Data Collector service with detailed examples, request/response formats, and usage patterns.

## Base Information

- **Base URL**: `http://localhost:3001`
- **API Version**: v1
- **Content Type**: `application/json`
- **Authentication**: API Key or JWT Token (optional for public endpoints)

## Authentication

### API Key Authentication

Include the API key in request headers:

```http
X-API-Key: your-api-key-here
```

### JWT Token Authentication

Include the JWT token in request headers:

```http
Authorization: Bearer your-jwt-token-here
```

### Public Access

Some endpoints are publicly accessible and don't require authentication.

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Public endpoints**: 100 requests per 15 minutes per IP
- **Authenticated endpoints**: 1000 requests per 15 minutes per API key
- **Burst protection**: 20 requests per minute per IP

Rate limit information is included in response headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1640995200
Retry-After: 900
```

## Response Format

All API responses follow a consistent structure:

### Success Response

```json
{
  "success": true,
  "data": {
    // Response data here
  },
  "message": "Operation completed successfully",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "requestId": "req_1234567890",
  "version": "v1",
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "totalPages": 8
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "date",
      "issue": "Date must be in YYYYMMDD format"
    }
  },
  "timestamp": "2024-01-01T00:00:00.000Z",
  "requestId": "req_1234567890"
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `EXTERNAL_API_ERROR` | 502 | KRA API error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

---

## Health & Monitoring Endpoints

### Health Check

Basic health check endpoint.

```http
GET /health
```

**Response:**

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-01T00:00:00.000Z",
    "uptime": 3600,
    "version": "1.0.0"
  }
}
```

### Detailed Health Status

Comprehensive health check including all system components.

```http
GET /health/detailed
```

**Response:**

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-01T00:00:00.000Z",
    "uptime": 3600,
    "version": "1.0.0",
    "components": {
      "redis": {
        "status": "healthy",
        "responseTime": 2,
        "memory": "15MB"
      },
      "kraApi": {
        "status": "healthy",
        "responseTime": 150,
        "lastCheck": "2024-01-01T00:00:00.000Z"
      },
      "server": {
        "status": "healthy",
        "memoryUsage": "128MB",
        "cpuUsage": "15%"
      }
    }
  }
}
```

### Application Metrics

System performance metrics and statistics.

```http
GET /health/metrics
```

**Response:**

```json
{
  "success": true,
  "data": {
    "requests": {
      "total": 15420,
      "success": 14890,
      "errors": 530,
      "avgResponseTime": 125
    },
    "memory": {
      "used": "128MB",
      "free": "256MB",
      "total": "384MB"
    },
    "cache": {
      "hitRate": 85.5,
      "missRate": 14.5,
      "keys": 2840
    },
    "externalApi": {
      "kraApiCalls": 3420,
      "avgResponseTime": 180,
      "errorRate": 2.1
    }
  }
}
```

---

## Race Data Endpoints

### Get Races by Date

Retrieve all races for a specific date.

```http
GET /api/v1/races/:date
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string | Yes | Race date in YYYYMMDD format |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `meet` | string | all | Filter by race track (서울, 부산경남, 제주) |
| `limit` | number | 20 | Number of races to return |
| `offset` | number | 0 | Number of races to skip |

**Example Request:**

```http
GET /api/v1/races/20241201?meet=서울&limit=10
```

**Example Response:**

```json
{
  "success": true,
  "data": {
    "races": [
      {
        "date": "20241201",
        "meet": "서울",
        "raceNo": 1,
        "raceName": "3세 미승리",
        "raceTime": "10:30",
        "distance": 1200,
        "horses": 12,
        "status": "completed"
      }
    ]
  },
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 11,
    "totalPages": 2
  }
}
```

### Get Specific Race Details

Get detailed information for a specific race.

```http
GET /api/v1/races/:date/:meet/:raceNo
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string | Yes | Race date in YYYYMMDD format |
| `meet` | string | Yes | Race track identifier |
| `raceNo` | number | Yes | Race number |

**Example Request:**

```http
GET /api/v1/races/20241201/서울/1
```

**Example Response:**

```json
{
  "success": true,
  "data": {
    "race": {
      "date": "20241201",
      "meet": "서울",
      "raceNo": 1,
      "raceName": "3세 미승리",
      "raceTime": "10:30",
      "distance": 1200,
      "surface": "모래",
      "weather": "맑음",
      "trackCondition": "양호",
      "horses": [
        {
          "chulNo": 1,
          "hrNo": "20210001",
          "hrName": "경주마명",
          "jkNo": "001",
          "jkName": "기수명",
          "trNo": "001",
          "trName": "조교사명",
          "weight": 55,
          "handicap": 0,
          "odds": 3.5
        }
      ]
    }
  }
}
```

### Get Race Results

Get the results of a completed race.

```http
GET /api/v1/races/:date/:meet/:raceNo/result
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string | Yes | Race date in YYYYMMDD format |
| `meet` | string | Yes | Race track identifier |
| `raceNo` | number | Yes | Race number |

**Example Request:**

```http
GET /api/v1/races/20241201/서울/1/result
```

**Example Response:**

```json
{
  "success": true,
  "data": {
    "result": {
      "date": "20241201",
      "meet": "서울",
      "raceNo": 1,
      "finishTime": "01:12.3",
      "horses": [
        {
          "ord": 1,
          "chulNo": 5,
          "hrNo": "20210005",
          "hrName": "우승마명",
          "jkNo": "005",
          "jkName": "우승기수",
          "finishTime": "01:12.3",
          "margin": 0,
          "winOdds": 4.2,
          "placeOdds": 1.8
        }
      ],
      "payouts": {
        "win": 420,
        "place": [180, 340, 120],
        "exacta": 2340,
        "trifecta": 15680
      }
    }
  }
}
```

### Trigger Race Data Collection

Initiate collection of race data from KRA API.

```http
POST /api/v1/races/collect
```

**Request Body:**

```json
{
  "date": "20241201",
  "meet": "서울",
  "raceNo": 1
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "jobId": "collect_20241201_seoul_1",
    "status": "started",
    "estimatedTime": "30s"
  },
  "message": "Data collection started"
}
```

### Trigger Race Data Enrichment

Enhance collected race data with additional analytics.

```http
POST /api/v1/races/enrich
```

**Request Body:**

```json
{
  "date": "20241201",
  "meet": "서울"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "jobId": "enrich_20241201_seoul",
    "status": "started",
    "racesQueued": 11,
    "estimatedTime": "5m"
  },
  "message": "Data enrichment started"
}
```

---

## Horse Data Endpoints

### Search Horses

Search for horses by various criteria.

```http
GET /api/v1/horses
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | - | Horse name (partial match) |
| `hrNo` | string | - | Horse number (exact match) |
| `age` | number | - | Horse age |
| `sex` | string | - | Horse sex (수컷, 암컷, 거세) |
| `limit` | number | 20 | Number of results to return |
| `offset` | number | 0 | Number of results to skip |

**Example Request:**

```http
GET /api/v1/horses?name=천리마&limit=10
```

**Example Response:**

```json
{
  "success": true,
  "data": {
    "horses": [
      {
        "hrNo": "20210001",
        "hrName": "천리마",
        "age": 4,
        "sex": "수컷",
        "birthDate": "20200315",
        "country": "한국",
        "owner": "마주명",
        "trainer": "조교사명",
        "career": {
          "starts": 15,
          "wins": 3,
          "places": 5,
          "winRate": 20.0
        }
      }
    ]
  },
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 1,
    "totalPages": 1
  }
}
```

### Get Horse Details

Get comprehensive information about a specific horse.

```http
GET /api/v1/horses/:hrNo
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `hrNo` | string | Yes | Horse number |

**Example Request:**

```http
GET /api/v1/horses/20210001
```

**Example Response:**

```json
{
  "success": true,
  "data": {
    "horse": {
      "hrNo": "20210001",
      "hrName": "천리마",
      "age": 4,
      "sex": "수컷",
      "birthDate": "20200315",
      "country": "한국",
      "color": "청모",
      "father": "아버지말명",
      "mother": "어머니말명",
      "owner": {
        "name": "마주명",
        "owNo": "001"
      },
      "trainer": {
        "name": "조교사명",
        "trNo": "001"
      },
      "career": {
        "starts": 15,
        "wins": 3,
        "seconds": 2,
        "thirds": 3,
        "winRate": 20.0,
        "placeRate": 53.3,
        "earnings": 50000000
      }
    }
  }
}
```

### Get Horse Racing History

Get racing history for a specific horse.

```http
GET /api/v1/horses/:hrNo/history
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `hrNo` | string | Yes | Horse number |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | number | 20 | Number of races to return |
| `offset` | number | 0 | Number of races to skip |
| `year` | number | - | Filter by year |
| `meet` | string | - | Filter by race track |

**Example Request:**

```http
GET /api/v1/horses/20210001/history?limit=10
```

**Example Response:**

```json
{
  "success": true,
  "data": {
    "history": [
      {
        "date": "20241201",
        "meet": "서울",
        "raceNo": 5,
        "raceName": "4세 이상 승리",
        "distance": 1400,
        "ord": 1,
        "chulNo": 3,
        "jockey": "기수명",
        "weight": 57,
        "odds": 2.8,
        "margin": "목",
        "time": "01:24.5"
      }
    ]
  },
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 15,
    "totalPages": 2
  }
}
```

---

## Jockey Data Endpoints

### Search Jockeys

Search for jockeys by name or number.

```http
GET /api/v1/jockeys
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | - | Jockey name (partial match) |
| `jkNo` | string | - | Jockey number (exact match) |
| `limit` | number | 20 | Number of results to return |
| `offset` | number | 0 | Number of results to skip |

**Example Request:**

```http
GET /api/v1/jockeys?name=김기수
```

**Example Response:**

```json
{
  "success": true,
  "data": {
    "jockeys": [
      {
        "jkNo": "001",
        "jkName": "김기수",
        "age": 35,
        "weight": 52,
        "debut": "20100301",
        "license": "정기수",
        "career": {
          "starts": 2450,
          "wins": 380,
          "seconds": 320,
          "thirds": 290,
          "winRate": 15.5,
          "placeRate": 40.4
        }
      }
    ]
  }
}
```

### Get Jockey Details

Get detailed information about a specific jockey.

```http
GET /api/v1/jockeys/:jkNo
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `jkNo` | string | Yes | Jockey number |

**Example Response:**

```json
{
  "success": true,
  "data": {
    "jockey": {
      "jkNo": "001",
      "jkName": "김기수",
      "age": 35,
      "height": 165,
      "weight": 52,
      "birthDate": "19890315",
      "debut": "20100301",
      "license": "정기수",
      "career": {
        "starts": 2450,
        "wins": 380,
        "seconds": 320,
        "thirds": 290,
        "winRate": 15.5,
        "placeRate": 40.4,
        "earnings": 1500000000
      }
    }
  }
}
```

### Get Jockey Statistics

Get performance statistics for a jockey.

```http
GET /api/v1/jockeys/:jkNo/stats
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `period` | string | 1y | Statistics period (1m, 3m, 6m, 1y, all) |
| `meet` | string | - | Filter by race track |

**Example Response:**

```json
{
  "success": true,
  "data": {
    "stats": {
      "period": "1y",
      "starts": 320,
      "wins": 48,
      "seconds": 42,
      "thirds": 38,
      "winRate": 15.0,
      "placeRate": 40.0,
      "earnings": 180000000,
      "avgOdds": 4.2,
      "byDistance": {
        "1000-1200": { "starts": 80, "wins": 12, "winRate": 15.0 },
        "1300-1600": { "starts": 160, "wins": 28, "winRate": 17.5 },
        "1700+": { "starts": 80, "wins": 8, "winRate": 10.0 }
      }
    }
  }
}
```

---

## Trainer Data Endpoints

### Search Trainers

Search for trainers by name or number.

```http
GET /api/v1/trainers
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | - | Trainer name (partial match) |
| `trNo` | string | - | Trainer number (exact match) |
| `limit` | number | 20 | Number of results to return |
| `offset` | number | 0 | Number of results to skip |

**Example Response:**

```json
{
  "success": true,
  "data": {
    "trainers": [
      {
        "trNo": "001",
        "trName": "박조교사",
        "license": "정조교사",
        "stable": "1구역",
        "debut": "20050301",
        "career": {
          "starts": 1850,
          "wins": 280,
          "winRate": 15.1,
          "earnings": 2100000000
        }
      }
    ]
  }
}
```

### Get Trainer Details

Get detailed information about a specific trainer.

```http
GET /api/v1/trainers/:trNo
```

**Example Response:**

```json
{
  "success": true,
  "data": {
    "trainer": {
      "trNo": "001",
      "trName": "박조교사",
      "age": 48,
      "license": "정조교사",
      "stable": "1구역",
      "debut": "20050301",
      "horses": 25,
      "career": {
        "starts": 1850,
        "wins": 280,
        "seconds": 240,
        "thirds": 220,
        "winRate": 15.1,
        "placeRate": 40.0,
        "earnings": 2100000000
      }
    }
  }
}
```

### Get Trainer Horses

Get all horses trained by a specific trainer.

```http
GET /api/v1/trainers/:trNo/horses
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `active` | boolean | true | Include only active horses |
| `limit` | number | 20 | Number of horses to return |
| `offset` | number | 0 | Number of horses to skip |

**Example Response:**

```json
{
  "success": true,
  "data": {
    "horses": [
      {
        "hrNo": "20210001",
        "hrName": "천리마",
        "age": 4,
        "sex": "수컷",
        "career": {
          "starts": 8,
          "wins": 2,
          "winRate": 25.0
        },
        "lastRace": "20241201"
      }
    ]
  },
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 25,
    "totalPages": 2
  }
}
```

---

## Pagination

All list endpoints support pagination using the following parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | number | 20 | Number of items per page (max: 100) |
| `offset` | number | 0 | Number of items to skip |
| `page` | number | 1 | Page number (alternative to offset) |

Pagination information is included in the response:

```json
{
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "totalPages": 8,
    "hasNext": true,
    "hasPrevious": false
  }
}
```

## Filtering and Sorting

Many endpoints support filtering and sorting:

### Common Filters

| Parameter | Type | Description |
|-----------|------|-------------|
| `date_from` | string | Start date (YYYYMMDD) |
| `date_to` | string | End date (YYYYMMDD) |
| `meet` | string | Race track filter |
| `status` | string | Status filter |

### Sorting

| Parameter | Type | Description |
|-----------|------|-------------|
| `sort_by` | string | Field to sort by |
| `sort_order` | string | Sort order (asc, desc) |

**Example:**

```http
GET /api/v1/races?date_from=20241101&date_to=20241130&sort_by=date&sort_order=desc
```

## Caching

The API implements intelligent caching to improve performance:

- **Browser Cache**: Static data cached for 1 hour
- **Redis Cache**: Dynamic data cached for 15 minutes
- **ETags**: Conditional requests supported
- **Last-Modified**: Timestamp-based caching

Cache headers are included in responses:

```http
Cache-Control: public, max-age=900
ETag: "W/\"1234567890\""
Last-Modified: Wed, 01 Jan 2024 00:00:00 GMT
```

## WebSocket Support (Future)

Real-time updates will be available via WebSocket connections:

```javascript
const socket = new WebSocket('ws://localhost:3001/ws');

socket.on('race_result', (data) => {
  console.log('New race result:', data);
});

socket.on('odds_update', (data) => {
  console.log('Odds updated:', data);
});
```

## SDK and Client Libraries

Official client libraries are available for:

- **JavaScript/TypeScript**: `@kra-collector/client-js`
- **Python**: `kra-collector-python`
- **Java**: `kra-collector-java`
- **Go**: `github.com/kra-collector/client-go`

**Example usage:**

```javascript
import { KraCollectorClient } from '@kra-collector/client-js';

const client = new KraCollectorClient({
  baseUrl: 'http://localhost:3001',
  apiKey: 'your-api-key'
});

const races = await client.races.getByDate('20241201');
const horse = await client.horses.getDetails('20210001');
```