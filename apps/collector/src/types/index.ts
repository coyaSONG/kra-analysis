/**
 * Central type definitions for collector
 *
 * This file serves as the main entry point for all type definitions
 * used throughout the collector application. It imports and
 * re-exports types from various modules and integrates with shared types.
 */

// ============================================================================
// Import comprehensive KRA API types
// ============================================================================
export * from './kra-api.types.js';
export * from './api.types.js';

// ============================================================================
// Shared Types (compatible with @packages/shared-types)
// ============================================================================

/**
 * Meet/Track enum matching shared types
 */
export enum Meet {
  SEOUL = 1,
  JEJU = 2,
  BUSAN = 3,
}

/**
 * Shared API response structure
 */
export interface SharedApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

/**
 * Shared horse entry structure
 */
export interface SharedHorseEntry {
  hrNo: string;
  hrName: string;
  jkNo: string;
  jkName: string;
  trNo: string;
  trName: string;
  ord?: number;
  winOdds?: number;
  plcOdds?: number;
  hrDetail?: SharedHorseDetail;
  jkDetail?: SharedJockeyDetail;
  trDetail?: SharedTrainerDetail;
}

/**
 * Shared horse detail structure
 */
export interface SharedHorseDetail {
  faHrName?: string;
  moHrName?: string;
  rcCntT?: number;
  ord1CntT?: number;
  winRateT?: string;
}

/**
 * Shared jockey detail structure
 */
export interface SharedJockeyDetail {
  age?: string;
  debut?: string;
  ord1CntT?: number;
  winRateT?: string;
}

/**
 * Shared trainer detail structure
 */
export interface SharedTrainerDetail {
  meet?: string;
  ord1CntT?: number;
  winRateT?: number;
  plcRateT?: number;
}

/**
 * Shared race data structure
 */
export interface SharedRaceData {
  date: string;
  meet: Meet;
  raceNo: number;
  horses: SharedHorseEntry[];
}

// ============================================================================
// Application Configuration Types
// ============================================================================

/**
 * Application configuration structure
 */
export interface Config {
  /** Server port number */
  port: number;
  /** Server host address */
  host?: string;
  /** Node environment (development, production, test) */
  nodeEnv: string;
  /** CORS allowed origins */
  corsOrigins?: string[];
  /** Redis configuration (optional) */
  redis?: {
    host: string;
    port: number;
    password?: string;
    /** Connection timeout in milliseconds */
    connectTimeout?: number;
    /** Command timeout in milliseconds */
    commandTimeout?: number;
    /** Number of retry attempts */
    retryAttempts?: number;
  };
  /** KRA API configuration */
  kra: {
    /** Base URL for KRA API */
    baseUrl: string;
    /** API key for authentication (optional) */
    apiKey?: string;
    /** Request timeout in milliseconds */
    timeout?: number;
    /** Rate limiting configuration */
    rateLimit?: {
      /** Maximum requests per time window */
      maxRequests: number;
      /** Time window in milliseconds */
      windowMs: number;
    };
    /** Retry configuration */
    retry?: {
      /** Number of retry attempts */
      attempts: number;
      /** Delay between retries in milliseconds */
      delay: number;
      /** Exponential backoff factor */
      backoffFactor: number;
    };
  };
  /** Database configuration */
  database?: {
    /** Database connection URL */
    url: string;
    /** Maximum number of connections in pool */
    maxConnections?: number;
    /** Connection timeout in milliseconds */
    connectionTimeout?: number;
    /** Query timeout in milliseconds */
    queryTimeout?: number;
  };
  /** Logging configuration */
  logging?: {
    /** Log level (error, warn, info, debug) */
    level: 'error' | 'warn' | 'info' | 'debug';
    /** Whether to log to console */
    console: boolean;
    /** File logging configuration */
    file?: {
      /** Log file path */
      path: string;
      /** Maximum file size in bytes */
      maxSize: number;
      /** Number of backup files to keep */
      maxFiles: number;
    };
  };
}

// ============================================================================
// Backward Compatibility Types (deprecated, use KRA API types instead)
// ============================================================================

/**
 * @deprecated Use CollectionRequest from api.types.ts instead
 * Legacy race data structure for backward compatibility
 */
export interface RaceData {
  /** Race date in YYYY-MM-DD format */
  date: string;
  /** Meet/Track identifier */
  meet: Meet;
  /** Race number */
  raceNo: number;
  /** Track identifier (deprecated, use meet instead) */
  track?: string;
  /** Array of horse entries */
  horses: HorseData[];
}

/**
 * @deprecated Use Api214Item or EnrichedHorseEntry instead
 * Legacy horse data structure for backward compatibility
 */
export interface HorseData {
  /** Horse number */
  horseNo: number;
  /** Horse name */
  horseName: string;
  /** Jockey name */
  jockeyName: string;
  /** Betting odds */
  odds: number;
  /** Carrying weight */
  weight: number;
  /** Additional fields for compatibility */
  [key: string]: any;
}

/**
 * @deprecated Use CollectionRequest from api.types.ts instead
 * Legacy collection request structure
 */
export interface CollectionRequest {
  /** Race date in YYYY-MM-DD format */
  date: string;
  /** Race number (optional) */
  raceNo?: number;
  /** Track identifier (optional, use meet instead) */
  track?: string;
}

/**
 * @deprecated Use CollectionResponse from api.types.ts instead
 * Legacy collection response structure
 */
export interface CollectionResponse extends SharedApiResponse<RaceData> {}

// ============================================================================
// Error Handling Types
// ============================================================================

/**
 * Custom application error with additional context
 */
export class AppError extends Error {
  /** HTTP status code */
  public readonly statusCode: number;
  /** Whether the error is operational (not a programmer error) */
  public readonly isOperational: boolean;
  /** Additional error context */
  public readonly context?: Record<string, any>;
  /** Error timestamp */
  public readonly timestamp: Date;

  constructor(message: string, statusCode: number = 500, isOperational: boolean = true, context?: Record<string, any>) {
    super(message);
    this.name = this.constructor.name;
    this.statusCode = statusCode;
    this.isOperational = isOperational;
    this.context = context;
    this.timestamp = new Date();

    // Ensure the stack trace points to where the error was thrown
    Error.captureStackTrace(this, this.constructor);
  }

  /**
   * Convert error to JSON for logging/API responses
   */
  toJSON() {
    return {
      name: this.name,
      message: this.message,
      statusCode: this.statusCode,
      isOperational: this.isOperational,
      context: this.context,
      timestamp: this.timestamp.toISOString(),
      stack: this.stack,
    };
  }
}

/**
 * Validation error for request validation failures
 */
export class ValidationError extends AppError {
  /** Array of validation error details */
  public readonly validationErrors: Array<{
    field: string;
    message: string;
    value?: any;
  }>;

  constructor(
    message: string = 'Validation failed',
    validationErrors: Array<{ field: string; message: string; value?: any }> = [],
    context?: Record<string, any>
  ) {
    super(message, 400, true, context);
    this.validationErrors = validationErrors;
  }

  /**
   * Add a validation error
   */
  addError(field: string, message: string, value?: any) {
    this.validationErrors.push({ field, message, value });
    return this;
  }

  /**
   * Convert to JSON with validation details
   */
  toJSON() {
    return {
      ...super.toJSON(),
      validationErrors: this.validationErrors,
    };
  }
}

/**
 * Resource not found error
 */
export class NotFoundError extends AppError {
  /** Resource type that was not found */
  public readonly resourceType?: string;
  /** Resource identifier that was not found */
  public readonly resourceId?: string;

  constructor(
    message: string = 'Resource not found',
    resourceType?: string,
    resourceId?: string,
    context?: Record<string, any>
  ) {
    super(message, 404, true, context);
    this.resourceType = resourceType;
    this.resourceId = resourceId;
  }

  /**
   * Convert to JSON with resource details
   */
  toJSON() {
    return {
      ...super.toJSON(),
      resourceType: this.resourceType,
      resourceId: this.resourceId,
    };
  }
}

/**
 * Rate limiting error
 */
export class RateLimitError extends AppError {
  /** Time until rate limit resets (in seconds) */
  public readonly retryAfter: number;
  /** Current rate limit window */
  public readonly limit: number;
  /** Number of requests made in current window */
  public readonly current: number;

  constructor(
    message: string = 'Rate limit exceeded',
    retryAfter: number,
    limit: number,
    current: number,
    context?: Record<string, any>
  ) {
    super(message, 429, true, context);
    this.retryAfter = retryAfter;
    this.limit = limit;
    this.current = current;
  }

  /**
   * Convert to JSON with rate limit details
   */
  toJSON() {
    return {
      ...super.toJSON(),
      retryAfter: this.retryAfter,
      limit: this.limit,
      current: this.current,
    };
  }
}

/**
 * External API error (for KRA API failures)
 */
export class ExternalApiError extends AppError {
  /** External API name */
  public readonly apiName: string;
  /** External API endpoint */
  public readonly endpoint?: string;
  /** External API response code */
  public readonly apiResponseCode?: string;
  /** External API response message */
  public readonly apiResponseMessage?: string;

  constructor(
    message: string,
    apiName: string,
    statusCode: number = 502,
    endpoint?: string,
    apiResponseCode?: string,
    apiResponseMessage?: string,
    context?: Record<string, any>
  ) {
    super(message, statusCode, true, context);
    this.apiName = apiName;
    this.endpoint = endpoint;
    this.apiResponseCode = apiResponseCode;
    this.apiResponseMessage = apiResponseMessage;
  }

  /**
   * Convert to JSON with API error details
   */
  toJSON() {
    return {
      ...super.toJSON(),
      apiName: this.apiName,
      endpoint: this.endpoint,
      apiResponseCode: this.apiResponseCode,
      apiResponseMessage: this.apiResponseMessage,
    };
  }
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Extract the data type from an ApiResponse
 */
export type ExtractApiResponseData<T> = T extends SharedApiResponse<infer U> ? U : never;

/**
 * Make all properties of T optional recursively
 */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

/**
 * Make specified properties of T optional
 */
export type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

/**
 * Make specified properties of T required
 */
export type RequiredBy<T, K extends keyof T> = T & Required<Pick<T, K>>;

/**
 * Extract keys of T that are of type U
 */
export type KeysOfType<T, U> = {
  [K in keyof T]: T[K] extends U ? K : never;
}[keyof T];

/**
 * Timestamp string in ISO format
 */
export type ISOTimestamp = string;

/**
 * Date string in YYYY-MM-DD format
 */
export type DateString = string;
