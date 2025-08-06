import type { Request, Response, NextFunction } from 'express';
import { v4 as uuidv4 } from 'uuid';
import logger from '../utils/logger.js';

/**
 * Extended Request interface to include request ID and timing
 */
export interface LoggingRequest extends Request {
  requestId?: string;
  startTime?: number;
  user?: {
    id?: string;
    permissions?: string[];
  };
}

/**
 * Sensitive data patterns to exclude from logs
 */
const SENSITIVE_PATTERNS = [
  /password/i,
  /token/i,
  /api[_-]?key/i,
  /secret/i,
  /private[_-]?key/i,
  /authorization/i,
  /credential/i,
  /ssn/i,
  /social[_-]?security/i,
  /credit[_-]?card/i,
  /card[_-]?number/i,
];

/**
 * Sensitive headers to exclude from logs
 */
const SENSITIVE_HEADERS = [
  'authorization',
  'x-api-key',
  'cookie',
  'set-cookie',
  'x-auth-token',
  'x-access-token',
  'x-refresh-token',
];

/**
 * Check if a field contains sensitive data
 */
const isSensitiveField = (fieldName: string): boolean => {
  return SENSITIVE_PATTERNS.some(pattern => pattern.test(fieldName));
};

/**
 * Sanitize object by removing sensitive fields
 */
const sanitizeObject = (obj: any, maxDepth: number = 3): any => {
  if (maxDepth <= 0 || obj === null || typeof obj !== 'object') {
    return obj;
  }

  if (Array.isArray(obj)) {
    return obj.map(item => sanitizeObject(item, maxDepth - 1));
  }

  const sanitized: any = {};
  for (const [key, value] of Object.entries(obj)) {
    if (isSensitiveField(key)) {
      sanitized[key] = '[REDACTED]';
    } else if (typeof value === 'object') {
      sanitized[key] = sanitizeObject(value, maxDepth - 1);
    } else {
      sanitized[key] = value;
    }
  }

  return sanitized;
};

/**
 * Sanitize headers by removing sensitive ones
 */
const sanitizeHeaders = (headers: Record<string, any>): Record<string, any> => {
  const sanitized: Record<string, any> = {};
  
  for (const [key, value] of Object.entries(headers)) {
    if (SENSITIVE_HEADERS.includes(key.toLowerCase()) || isSensitiveField(key)) {
      sanitized[key] = '[REDACTED]';
    } else {
      sanitized[key] = value;
    }
  }
  
  return sanitized;
};

/**
 * Get client IP address, considering proxy headers
 */
const getClientIp = (req: Request): string => {
  const forwarded = req.get('x-forwarded-for');
  if (forwarded) {
    return forwarded.split(',')[0]?.trim() || req.ip || 'unknown';
  }
  
  const realIp = req.get('x-real-ip');
  if (realIp) {
    return realIp;
  }
  
  return req.ip || req.connection.remoteAddress || 'unknown';
};

/**
 * Get user agent and parse basic info
 */
const getUserAgent = (req: Request): { userAgent: string; browser?: string; os?: string } => {
  const userAgent = req.get('User-Agent') || 'unknown';
  
  // Basic user agent parsing (you might want to use a library for more detailed parsing)
  let browser = 'unknown';
  let os = 'unknown';
  
  if (userAgent.includes('Chrome')) browser = 'Chrome';
  else if (userAgent.includes('Firefox')) browser = 'Firefox';
  else if (userAgent.includes('Safari')) browser = 'Safari';
  else if (userAgent.includes('Edge')) browser = 'Edge';
  
  if (userAgent.includes('Windows')) os = 'Windows';
  else if (userAgent.includes('Mac OS')) os = 'macOS';
  else if (userAgent.includes('Linux')) os = 'Linux';
  else if (userAgent.includes('Android')) os = 'Android';
  else if (userAgent.includes('iOS')) os = 'iOS';
  
  return { userAgent, browser, os };
};

/**
 * Determine log level based on response status
 */
const getLogLevel = (statusCode: number): string => {
  if (statusCode >= 500) return 'error';
  if (statusCode >= 400) return 'warn';
  if (statusCode >= 300) return 'info';
  return 'info';
};

/**
 * Request logging middleware
 * Logs incoming requests with sanitized data and assigns request ID
 */
export const requestLogger = (
  req: LoggingRequest,
  res: Response,
  next: NextFunction
): void => {
  // Generate unique request ID
  req.requestId = uuidv4();
  req.startTime = Date.now();
  
  // Add request ID to response headers for debugging
  res.set('X-Request-ID', req.requestId);
  
  // Get client information
  const clientIp = getClientIp(req);
  const userAgentInfo = getUserAgent(req);
  
  // Prepare request log data
  const requestLogData = {
    requestId: req.requestId,
    method: req.method,
    url: req.url,
    path: req.path,
    query: sanitizeObject(req.query, 2),
    headers: sanitizeHeaders(req.headers),
    body: req.method !== 'GET' ? sanitizeObject(req.body, 3) : undefined,
    ip: clientIp,
    userAgent: userAgentInfo.userAgent,
    browser: userAgentInfo.browser,
    os: userAgentInfo.os,
    timestamp: new Date().toISOString(),
    contentLength: req.get('content-length'),
    contentType: req.get('content-type'),
    // User info if available
    userId: req.user?.id,
    userPermissions: req.user?.permissions,
  };
  
  // Log the incoming request
  logger.info('Incoming request', requestLogData);
  
  // Store original res.end to capture response
  const originalEnd = res.end;
  const originalWrite = res.write;
  
  let responseBody = '';
  let responseSize = 0;
  
  // Capture response data
  res.write = function(chunk: any, encoding?: any, callback?: any) {
    if (chunk) {
      responseSize += chunk.length || 0;
      
      // Capture response body for logging (limit size)
      if (typeof chunk === 'string' || Buffer.isBuffer(chunk)) {
        const chunkStr = chunk.toString();
        if (responseBody.length < 1000) { // Limit response body logging to 1KB
          responseBody += chunkStr;
        }
      }
    }
    return originalWrite.call(this, chunk, encoding, callback);
  };
  
  // Override res.end to log response
  res.end = function(chunk: any, encoding?: any, callback?: any) {
    if (chunk) {
      responseSize += chunk.length || 0;
      
      // Capture final chunk
      if (typeof chunk === 'string' || Buffer.isBuffer(chunk)) {
        const chunkStr = chunk.toString();
        if (responseBody.length < 1000) {
          responseBody += chunkStr;
        }
      }
    }
    
    // Calculate response time
    const responseTime = req.startTime ? Date.now() - req.startTime : 0;
    
    // Prepare response log data
    const responseLogData = {
      requestId: req.requestId,
      method: req.method,
      url: req.url,
      statusCode: res.statusCode,
      statusMessage: res.statusMessage,
      responseTime: `${responseTime}ms`,
      responseSize: `${responseSize} bytes`,
      contentType: res.get('Content-Type'),
      timestamp: new Date().toISOString(),
      // User info if available
      userId: req.user?.id,
      // Response body (sanitized and truncated)
      responseBody: responseBody ? sanitizeObject(
        (() => {
          try {
            return JSON.parse(responseBody);
          } catch {
            return responseBody.substring(0, 500); // Truncate non-JSON responses
          }
        })(),
        2
      ) : undefined,
    };
    
    // Log with appropriate level based on status code
    const logLevel = getLogLevel(res.statusCode);
    logger.log(logLevel, 'Request completed', responseLogData);
    
    // Log performance warning if response is slow
    if (responseTime > 5000) { // 5 seconds
      logger.warn('Slow request detected', {
        requestId: req.requestId,
        method: req.method,
        url: req.url,
        responseTime: `${responseTime}ms`,
        statusCode: res.statusCode,
        userId: req.user?.id,
      });
    }
    
    return originalEnd.call(this, chunk, encoding, callback);
  };
  
  next();
};

/**
 * Error logging middleware
 * Logs errors with request context
 */
export const errorLogger = (
  error: Error,
  req: LoggingRequest,
  res: Response,
  next: NextFunction
): void => {
  const errorLogData = {
    requestId: req.requestId,
    method: req.method,
    url: req.url,
    error: {
      name: error.name,
      message: error.message,
      stack: error.stack,
    },
    ip: getClientIp(req),
    userAgent: req.get('User-Agent'),
    userId: req.user?.id,
    timestamp: new Date().toISOString(),
    body: req.method !== 'GET' ? sanitizeObject(req.body, 2) : undefined,
    query: sanitizeObject(req.query, 2),
  };
  
  logger.error('Request error', errorLogData);
  
  next(error);
};

/**
 * Performance monitoring middleware
 * Logs performance metrics for monitoring
 */
export const performanceLogger = (
  req: LoggingRequest,
  res: Response,
  next: NextFunction
): void => {
  const start = process.hrtime.bigint();
  
  res.on('finish', () => {
    const end = process.hrtime.bigint();
    const duration = Number(end - start) / 1000000; // Convert to milliseconds
    
    const performanceData = {
      requestId: req.requestId,
      method: req.method,
      url: req.url,
      statusCode: res.statusCode,
      duration: `${duration.toFixed(2)}ms`,
      memoryUsage: {
        rss: `${(process.memoryUsage().rss / 1024 / 1024).toFixed(2)}MB`,
        heapUsed: `${(process.memoryUsage().heapUsed / 1024 / 1024).toFixed(2)}MB`,
        heapTotal: `${(process.memoryUsage().heapTotal / 1024 / 1024).toFixed(2)}MB`,
      },
      timestamp: new Date().toISOString(),
    };
    
    // Log performance metrics
    if (duration > 1000) { // Log slow requests (>1s)
      logger.warn('Performance: Slow request', performanceData);
    } else {
      logger.debug('Performance metrics', performanceData);
    }
  });
  
  next();
};

/**
 * Health check middleware - minimal logging for health endpoints
 */
export const healthCheckLogger = (
  req: LoggingRequest,
  res: Response,
  next: NextFunction
): void => {
  // Only log health check requests at debug level
  if (req.path === '/health' || req.path === '/status' || req.path === '/ping') {
    req.requestId = uuidv4();
    
    logger.debug('Health check request', {
      requestId: req.requestId,
      method: req.method,
      path: req.path,
      ip: getClientIp(req),
      timestamp: new Date().toISOString(),
    });
  }
  
  next();
};

/**
 * Security event logger
 * Logs security-relevant events
 */
export const securityLogger = {
  logAuthFailure: (req: Request, reason: string) => {
    logger.warn('Authentication failure', {
      ip: getClientIp(req),
      userAgent: req.get('User-Agent'),
      url: req.url,
      method: req.method,
      reason,
      timestamp: new Date().toISOString(),
    });
  },
  
  logSuspiciousActivity: (req: Request, activity: string, details?: any) => {
    logger.warn('Suspicious activity detected', {
      ip: getClientIp(req),
      userAgent: req.get('User-Agent'),
      url: req.url,
      method: req.method,
      activity,
      details: sanitizeObject(details, 2),
      timestamp: new Date().toISOString(),
    });
  },
  
  logRateLimitHit: (req: Request, limit: number, current: number) => {
    logger.warn('Rate limit exceeded', {
      ip: getClientIp(req),
      userAgent: req.get('User-Agent'),
      url: req.url,
      method: req.method,
      limit,
      current,
      timestamp: new Date().toISOString(),
    });
  },
};

export default requestLogger;