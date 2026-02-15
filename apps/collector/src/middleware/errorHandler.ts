import type { Request, Response, NextFunction } from 'express';
import { validationResult } from 'express-validator';
import { AppError, ValidationError, RateLimitError, ExternalApiError, NotFoundError } from '../types/index.js';
import logger from '../utils/logger.js';

export const errorHandler = (err: Error, req: Request, res: Response, _next: NextFunction): void => {
  // Log the error with appropriate level
  const logData = {
    message: err.message,
    stack: err.stack,
    url: req.url,
    method: req.method,
    ip: req.ip,
    userAgent: req.get('User-Agent'),
  };

  // Determine log level based on error type
  if (err instanceof ValidationError || err instanceof RateLimitError) {
    logger.warn('Client error occurred:', logData);
  } else if (err instanceof ExternalApiError) {
    logger.error('External API error occurred:', logData);
  } else if (err instanceof NotFoundError) {
    logger.info('Resource not found:', logData);
  } else {
    logger.error('Error occurred:', logData);
  }

  // Handle ValidationError from express-validator
  const validationErrors = validationResult(req);
  if (!validationErrors.isEmpty() && !(err instanceof ValidationError)) {
    const details = validationErrors.array().map((error) => ({
      field: error.type === 'field' ? error.path : 'unknown',
      message: error.msg,
      value: error.type === 'field' ? error.value : undefined,
    }));

    res.status(400).json({
      success: false,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Request validation failed',
        details,
      },
      timestamp: new Date().toISOString(),
    });
    return;
  }

  // Handle our custom ValidationError
  if (err instanceof ValidationError) {
    res.status(err.statusCode).json({
      success: false,
      error: {
        code: 'VALIDATION_ERROR',
        message: err.message,
        details: err.validationErrors,
      },
      timestamp: new Date().toISOString(),
      ...(process.env.NODE_ENV === 'development' && {
        stack: err.stack,
        context: err.context,
      }),
    });
    return;
  }

  // Handle RateLimitError
  if (err instanceof RateLimitError) {
    res
      .status(err.statusCode)
      .set({
        'Retry-After': err.retryAfter.toString(),
        'X-RateLimit-Limit': err.limit.toString(),
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Used': err.current.toString(),
      })
      .json({
        success: false,
        error: {
          code: 'RATE_LIMIT_EXCEEDED',
          message: err.message,
          retryAfter: err.retryAfter,
          limit: err.limit,
          current: err.current,
        },
        timestamp: new Date().toISOString(),
        ...(process.env.NODE_ENV === 'development' && {
          stack: err.stack,
          context: err.context,
        }),
      });
    return;
  }

  // Handle ExternalApiError
  if (err instanceof ExternalApiError) {
    res.status(err.statusCode).json({
      success: false,
      error: {
        code: 'EXTERNAL_API_ERROR',
        message: err.message,
        apiName: err.apiName,
        endpoint: err.endpoint,
        ...(err.apiResponseCode && { apiResponseCode: err.apiResponseCode }),
        ...(err.apiResponseMessage && { apiResponseMessage: err.apiResponseMessage }),
      },
      timestamp: new Date().toISOString(),
      ...(process.env.NODE_ENV === 'development' && {
        stack: err.stack,
        context: err.context,
      }),
    });
    return;
  }

  // Handle NotFoundError
  if (err instanceof NotFoundError) {
    res.status(err.statusCode).json({
      success: false,
      error: {
        code: 'NOT_FOUND',
        message: err.message,
        resourceType: err.resourceType,
        resourceId: err.resourceId,
      },
      timestamp: new Date().toISOString(),
      ...(process.env.NODE_ENV === 'development' && {
        stack: err.stack,
        context: err.context,
      }),
    });
    return;
  }

  // Handle other known application errors
  if (err instanceof AppError) {
    res.status(err.statusCode).json({
      success: false,
      error: {
        code: err.name === 'AppError' ? 'APPLICATION_ERROR' : err.name.toUpperCase(),
        message: err.message,
        ...(err.context && { context: err.context }),
      },
      timestamp: new Date().toISOString(),
      ...(process.env.NODE_ENV === 'development' && {
        stack: err.stack,
      }),
    });
    return;
  }

  // Handle specific error types by name
  if (err.name === 'ValidationError') {
    res.status(400).json({
      success: false,
      error: {
        code: 'VALIDATION_ERROR',
        message: err.message,
      },
      timestamp: new Date().toISOString(),
    });
    return;
  }

  // Handle MongoDB/Database errors
  if (err.name === 'MongoError' || err.name === 'CastError') {
    res.status(400).json({
      success: false,
      error: {
        code: 'DATABASE_ERROR',
        message: 'Invalid data format or database operation failed',
        ...(process.env.NODE_ENV === 'development' && { originalError: err.message }),
      },
      timestamp: new Date().toISOString(),
    });
    return;
  }

  // Handle JWT errors
  if (err.name === 'JsonWebTokenError' || err.name === 'TokenExpiredError') {
    res.status(401).json({
      success: false,
      error: {
        code: 'AUTHENTICATION_ERROR',
        message: 'Invalid or expired token',
      },
      timestamp: new Date().toISOString(),
    });
    return;
  }

  // Handle payload too large errors
  if (
    ('type' in err && (err as any).type === 'entity.too.large') ||
    err.message?.includes('request entity too large')
  ) {
    res.status(413).json({
      success: false,
      error: {
        code: 'PAYLOAD_TOO_LARGE',
        message: 'Request payload exceeds maximum allowed size',
      },
      timestamp: new Date().toISOString(),
    });
    return;
  }

  // Handle syntax errors (malformed JSON)
  if (err instanceof SyntaxError && 'body' in err) {
    res.status(400).json({
      success: false,
      error: {
        code: 'SYNTAX_ERROR',
        message: 'Invalid JSON format in request body',
      },
      timestamp: new Date().toISOString(),
    });
    return;
  }

  // Handle unexpected errors
  res.status(500).json({
    success: false,
    error: {
      code: 'INTERNAL_SERVER_ERROR',
      message: 'An unexpected error occurred',
      ...(process.env.NODE_ENV === 'development' && {
        originalMessage: err.message,
        stack: err.stack,
      }),
    },
    timestamp: new Date().toISOString(),
  });
};

export const methodNotAllowedHandler = (req: Request, res: Response, next: NextFunction): void => {
  // Check if this is a known route but with wrong method
  const route = req.route;
  if (route) {
    res.status(405).json({
      success: false,
      error: {
        code: 'METHOD_NOT_ALLOWED',
        message: `Method ${req.method} not allowed for this endpoint`,
        details: `Allowed methods: ${route.methods ? Object.keys(route.methods).join(', ').toUpperCase() : 'N/A'}`,
      },
      timestamp: new Date().toISOString(),
    });
    return;
  }
  next();
};

export const notFoundHandler = (req: Request, res: Response, _next: NextFunction): void => {
  res.status(404).json({
    success: false,
    error: {
      code: 'NOT_FOUND',
      message: `Route not found: ${req.method} ${req.originalUrl}`,
    },
    timestamp: new Date().toISOString(),
  });
};
