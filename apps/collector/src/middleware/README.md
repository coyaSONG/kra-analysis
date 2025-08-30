# Express Middleware Documentation

Comprehensive middleware suite for the Node.js KRA Data Collector API server.

## Overview

This middleware collection provides:

- **Rate Limiting**: Multiple rate limiting strategies with Redis support
- **Validation**: Comprehensive request validation with express-validator
- **Authentication**: API key-based authentication with permission system
- **Logging**: Detailed request/response logging with security filtering
- **Error Handling**: Consistent error responses with proper HTTP status codes

## Quick Start

### Basic Setup

```typescript
import express from 'express';
import { registerAllMiddleware } from './middleware/index.js';

const app = express();

// Register all middleware with default configuration
registerAllMiddleware(app);

// Your routes here
app.get('/api/races', (req, res) => {
  res.json({ message: 'Hello World' });
});
```

### Custom Configuration

```typescript
import express from 'express';
import { registerAllMiddleware, type MiddlewareConfig } from './middleware/index.js';

const app = express();

const middlewareConfig: Partial<MiddlewareConfig> = {
  rateLimiting: {
    enabled: true,
    general: true,
    strict: false, // Disable strict rate limiting
  },
  auth: {
    enabled: true,
    defaultMode: 'private', // Require authentication by default
  },
  cors: {
    enabled: true,
    origin: ['http://localhost:3000', 'https://yourdomain.com'],
  },
};

registerAllMiddleware(app, middlewareConfig);
```

## Middleware Components

### 1. Rate Limiting (`rate-limit.middleware.ts`)

Multiple rate limiting strategies with Redis fallback to memory storage.

#### Usage

```typescript
import { 
  generalRateLimit, 
  strictRateLimit, 
  apiCollectionRateLimit,
  createRateLimit
} from './middleware/index.js';

// Apply to specific routes
app.use('/api/public', generalRateLimit);
app.use('/api/admin', strictRateLimit);
app.use('/api/collection', apiCollectionRateLimit);

// Custom rate limit
const customLimit = createRateLimit({
  windowMs: 5 * 60 * 1000, // 5 minutes
  max: 50,
  message: 'Custom rate limit exceeded',
  keyPrefix: 'custom',
});
```

#### Rate Limit Types

- **General**: 100 requests/minute for read operations
- **Strict**: 10 requests/minute for write operations
- **API Collection**: 20 requests/minute for data collection endpoints
- **Gradual Slowdown**: Progressive delays as limits approach

#### Redis Configuration

```bash
# Environment variables
REDIS_URL=redis://localhost:6379
# OR
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=yourpassword
```

### 2. Validation (`validation.middleware.ts`)

Express-validator based validation chains for common KRA API parameters.

#### Usage

```typescript
import { 
  validateRaceParams, 
  validateCollectionRequest,
  validateDate,
  validateMeet,
  handleValidationErrors 
} from './middleware/index.js';

// Route-level validation
app.get('/api/races/:date/:meet/:raceNo', 
  validateRaceParams,  // Validates date, meet, raceNo
  (req, res) => {
    // req.params are validated and sanitized
    res.json({ message: 'Valid parameters' });
  }
);

// Body validation
app.post('/api/collection',
  validateCollectionRequest, // Validates request body
  (req, res) => {
    // req.body is validated
    res.json({ message: 'Valid request' });
  }
);

// Custom validation chain
app.get('/api/custom/:date',
  ...validateDate('param', 'date'),
  handleValidationErrors,
  (req, res) => {
    res.json({ message: 'Custom validation passed' });
  }
);
```

#### Validation Functions

- `validateDate()`: YYYYMMDD format validation
- `validateMeet()`: Meet/track validation (1=Seoul, 2=Jeju, 3=Busan)
- `validateRaceNo()`: Race number validation (1-20)
- `validateHorseId()`: Horse ID format validation (7 digits)
- `validateJockeyId()`: Jockey ID format validation (5 digits)
- `validateTrainerId()`: Trainer ID format validation (5 digits)

#### Pre-built Validation Chains

- `validateRaceParams`: For race endpoints
- `validateCollectionRequest`: For collection requests
- `validateHorseParams`: For horse endpoints
- `validateJockeyParams`: For jockey endpoints
- `validateTrainerParams`: For trainer endpoints

### 3. Authentication (`auth.middleware.ts`)

API key-based authentication with permission system.

#### Environment Setup

```bash
# API Keys (for production)
ADMIN_API_KEY=your-secure-admin-key
USER_API_KEY=your-user-key
READONLY_API_KEY=your-readonly-key

# Development key (automatically created in dev mode)
DEV_API_KEY=dev-key-12345
```

#### Usage

```typescript
import { 
  requireAuth, 
  optionalAuth,
  requirePermission,
  configureEndpointAccess 
} from './middleware/index.js';

// Require authentication
app.get('/api/private', requireAuth, (req, res) => {
  const user = req.user; // User info available
  res.json({ user: user.id });
});

// Optional authentication
app.get('/api/public', optionalAuth, (req, res) => {
  const user = req.user; // May be undefined
  res.json({ authenticated: !!user });
});

// Permission-based access
app.delete('/api/admin/cache', 
  requireAuth,
  requirePermission('admin'),
  (req, res) => {
    res.json({ message: 'Cache cleared' });
  }
);
```

#### API Key Headers

Clients can provide API keys in multiple ways:

```bash
# Authorization header (preferred)
curl -H "Authorization: Bearer your-api-key" http://localhost:3000/api/data

# X-API-Key header
curl -H "X-API-Key: your-api-key" http://localhost:3000/api/data

# Query parameter (not recommended for production)
curl http://localhost:3000/api/data?api_key=your-api-key
```

#### Permission System

- `read`: Read-only access to data
- `write`: Write access for data modification
- `admin`: Administrative access

### 4. Logging (`logging.middleware.ts`)

Comprehensive request/response logging with security filtering.

#### Features

- Request ID generation for tracing
- Response time measurement
- Sensitive data filtering
- Performance monitoring
- Security event logging

#### Usage

```typescript
import { 
  detailedRequestLogger,
  performanceLogger,
  securityLogger 
} from './middleware/index.js';

// Detailed logging (default in registerAllMiddleware)
app.use(detailedRequestLogger);

// Performance monitoring
app.use(performanceLogger);

// Security event logging
app.post('/api/login', (req, res) => {
  if (authFailed) {
    securityLogger.logAuthFailure(req, 'Invalid credentials');
  }
  
  if (suspiciousActivity) {
    securityLogger.logSuspiciousActivity(req, 'Multiple failed attempts', { 
      attempts: 5 
    });
  }
});
```

#### Log Structure

```json
{
  "requestId": "123e4567-e89b-12d3-a456-426614174000",
  "method": "POST",
  "url": "/api/collection",
  "statusCode": 200,
  "responseTime": "150ms",
  "ip": "192.168.1.1",
  "userAgent": "curl/7.68.0",
  "userId": "user-123",
  "timestamp": "2024-08-06T12:00:00.000Z"
}
```

### 5. Error Handling (`errorHandler.ts`)

Centralized error handling with consistent response format.

#### Supported Error Types

- `ValidationError`: Request validation failures
- `RateLimitError`: Rate limit exceeded
- `ExternalApiError`: KRA API failures
- `NotFoundError`: Resource not found
- `AppError`: General application errors

#### Usage

```typescript
import { ValidationError, ExternalApiError } from './types/index.js';

// Throw custom errors
app.get('/api/data', async (req, res, next) => {
  try {
    if (!req.query.date) {
      throw new ValidationError(
        'Date parameter is required',
        [{ field: 'date', message: 'Required field missing' }]
      );
    }
    
    const data = await fetchFromKRA();
    res.json(data);
  } catch (error) {
    if (error.code === 'EXTERNAL_API_ERROR') {
      throw new ExternalApiError(
        'KRA API temporarily unavailable',
        'KRA_API',
        502,
        '/api/endpoint',
        error.code,
        error.message
      );
    }
    next(error);
  }
});
```

#### Error Response Format

```json
{
  "success": false,
  "error": "Validation failed",
  "details": [
    {
      "field": "date",
      "message": "Date is required",
      "value": null
    }
  ],
  "timestamp": "2024-08-06T12:00:00.000Z"
}
```

## Middleware Registry

The `middleware-registry.ts` provides easy configuration and registration of all middleware.

### Presets

```typescript
import { middlewarePresets } from './middleware/index.js';

// Different endpoint types
app.use('/api/public', ...middlewarePresets.public());
app.use('/api/private', ...middlewarePresets.private());
app.use('/api/admin', ...middlewarePresets.admin());
app.use('/api/collection', ...middlewarePresets.collection(validateCollectionRequest));
```

### Custom Route Middleware

```typescript
import { createRouteMiddleware } from './middleware/index.js';

const customMiddleware = createRouteMiddleware({
  auth: 'private',
  rateLimit: 'strict',
  validation: [validateDate('param', 'date')],
  permissions: ['write', 'admin']
});

app.post('/api/admin/update/:date', ...customMiddleware, (req, res) => {
  res.json({ message: 'Update successful' });
});
```

## Configuration Options

### MiddlewareConfig Interface

```typescript
interface MiddlewareConfig {
  detailedLogging?: boolean;
  performanceMonitoring?: boolean;
  rateLimiting?: {
    enabled: boolean;
    general?: boolean;
    strict?: boolean;
    apiCollection?: boolean;
    gradualSlowDown?: boolean;
  };
  auth?: {
    enabled: boolean;
    defaultMode?: 'public' | 'private' | 'optional';
    requireAuthForAdmin?: boolean;
  };
  cors?: {
    enabled: boolean;
    origin?: string | string[] | boolean;
    credentials?: boolean;
  };
  security?: {
    enabled: boolean;
    helmetOptions?: any;
  };
}
```

## Environment Variables

```bash
# Server
NODE_ENV=development|production
PORT=3000

# Redis (for rate limiting)
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=optional

# API Keys
ADMIN_API_KEY=secure-admin-key
USER_API_KEY=user-key
READONLY_API_KEY=readonly-key
DEV_API_KEY=dev-key-12345

# CORS
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

## Best Practices

1. **Security First**
   - Use HTTPS in production
   - Store API keys securely
   - Regularly rotate API keys
   - Monitor security logs

2. **Rate Limiting**
   - Use Redis in production for consistency
   - Set appropriate limits for your use case
   - Monitor rate limit metrics
   - Implement circuit breakers for external APIs

3. **Validation**
   - Validate all inputs
   - Sanitize data before processing
   - Use specific validation chains
   - Handle validation errors gracefully

4. **Logging**
   - Log all requests in production
   - Filter sensitive data
   - Use structured logging
   - Monitor performance metrics

5. **Error Handling**
   - Use specific error types
   - Provide helpful error messages
   - Log errors with context
   - Never expose internal errors to clients

## Troubleshooting

### Common Issues

1. **Rate limiting not working**
   - Check Redis connection
   - Verify trust proxy settings
   - Check IP detection in logs

2. **Validation errors**
   - Check parameter names match validation chains
   - Ensure handleValidationErrors is called
   - Verify request format

3. **Authentication issues**
   - Check API key format
   - Verify headers are being sent
   - Check logs for authentication attempts

4. **CORS issues**
   - Verify origin configuration
   - Check preflight requests
   - Ensure credentials settings match

### Debug Mode

Enable debug logging:

```bash
NODE_ENV=development
DEBUG=middleware:*
```

This will enable detailed debug logs for all middleware components.