/**
 * REST API Type Definitions
 * 
 * Type definitions for our internal REST API endpoints and responses
 * Used for request/response validation and client-server communication
 */

import { 
  Api214Item, 
  Api8_2Item, 
  Api12_1Item, 
  Api19_1Item, 
  EnrichedRaceData,
  EnrichedHorseEntry 
} from './kra-api.types.js';

// ============================================================================
// Generic API Response Wrapper
// ============================================================================

/**
 * Standard API response wrapper for all our endpoints
 * @template T - The type of data contained in the response
 */
export interface ApiResponse<T = any> {
  /** Indicates if the request was successful */
  success: boolean;
  /** Response data (present on success) */
  data?: T;
  /** Human-readable success message */
  message?: string;
  /** Error message (present on failure) */
  error?: string;
  /** Additional metadata */
  meta?: ResponseMetadata;
}

/**
 * Response metadata for pagination and additional info
 */
export interface ResponseMetadata {
  /** Total count of items available */
  totalCount?: number;
  /** Current page number (1-based) */
  page?: number;
  /** Number of items per page */
  pageSize?: number;
  /** Total number of pages */
  totalPages?: number;
  /** Timestamp of response generation */
  timestamp?: string;
  /** Time taken to process request (in milliseconds) */
  processingTime?: number;
}

// ============================================================================
// Error Response Types
// ============================================================================

/**
 * Standard error response structure
 */
export interface ErrorResponse extends ApiResponse<never> {
  success: false;
  error: string;
  /** HTTP status code */
  statusCode?: number;
  /** Error code for programmatic handling */
  errorCode?: string;
  /** Additional error details for debugging */
  details?: Record<string, any>;
  /** Request ID for tracking */
  requestId?: string;
}

/**
 * Validation error details
 */
export interface ValidationError {
  /** Field that failed validation */
  field: string;
  /** Validation error message */
  message: string;
  /** Actual value that failed */
  value?: any;
  /** Expected format or constraint */
  constraint?: string;
}

/**
 * Validation error response
 */
export interface ValidationErrorResponse extends ErrorResponse {
  errorCode: 'VALIDATION_ERROR';
  /** Array of validation errors */
  validationErrors: ValidationError[];
}

// ============================================================================
// Pagination Types
// ============================================================================

/**
 * Standard pagination parameters
 */
export interface PaginationParams {
  /** Page number (1-based, default: 1) */
  page?: number;
  /** Number of items per page (default: 10, max: 100) */
  pageSize?: number;
  /** Field to sort by */
  sortBy?: string;
  /** Sort order */
  sortOrder?: 'asc' | 'desc';
}

/**
 * Paginated response wrapper
 * @template T - The type of items in the results array
 */
export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  data: T[];
  meta: ResponseMetadata & {
    totalCount: number;
    page: number;
    pageSize: number;
    totalPages: number;
  };
}

// ============================================================================
// Collection API Types
// ============================================================================

/**
 * Request to collect race data from KRA API
 */
export interface CollectionRequest {
  /** Race date in YYYY-MM-DD format */
  date: string;
  /** Race number (optional, if not provided collects all races for the date) */
  raceNo?: number;
  /** Track/Meet identifier (optional) */
  meet?: string;
  /** Whether to enrich data with additional API calls */
  enrichData?: boolean;
  /** Force refresh even if data exists */
  forceRefresh?: boolean;
}

/**
 * Response from race data collection
 */
export interface CollectionResponse extends ApiResponse<CollectedRaceData> {}

/**
 * Collected race data structure
 */
export interface CollectedRaceData {
  /** Race metadata */
  raceInfo: {
    date: string;
    meet: string;
    raceNo: number;
    rcName: string;
    rcDist: number;
    track: string;
    weather: string;
    totalHorses: number;
  };
  /** Raw race result data from API214_1 */
  raceResult: Api214Item[];
  /** Collection metadata */
  collectionMeta: {
    collectedAt: string;
    isEnriched: boolean;
    dataSource: 'kra_api' | 'cache' | 'database';
    cacheExpiresAt?: string;
  };
}

/**
 * Batch collection request for multiple races
 */
export interface BatchCollectionRequest {
  /** Start date in YYYY-MM-DD format */
  startDate: string;
  /** End date in YYYY-MM-DD format */
  endDate: string;
  /** Specific meets to collect (optional, default: all) */
  meets?: string[];
  /** Whether to enrich data with additional API calls */
  enrichData?: boolean;
  /** Maximum number of concurrent API calls */
  concurrency?: number;
  /** Force refresh even if data exists */
  forceRefresh?: boolean;
}

/**
 * Batch collection response
 */
export interface BatchCollectionResponse extends ApiResponse<BatchCollectionResult> {}

/**
 * Result of batch collection operation
 */
export interface BatchCollectionResult {
  /** Summary statistics */
  summary: {
    totalRequested: number;
    totalCollected: number;
    totalFailed: number;
    totalSkipped: number;
    duration: number; // in milliseconds
  };
  /** Detailed results per race */
  results: {
    date: string;
    raceNo: number;
    meet: string;
    status: 'success' | 'failed' | 'skipped';
    error?: string;
    dataSize?: number;
  }[];
  /** Any errors encountered */
  errors: string[];
}

// ============================================================================
// Query Parameter Types
// ============================================================================

/**
 * Query parameters for race data endpoints
 */
export interface RaceQueryParams extends PaginationParams {
  /** Filter by date (YYYY-MM-DD) */
  date?: string;
  /** Filter by date range start */
  dateFrom?: string;
  /** Filter by date range end */
  dateTo?: string;
  /** Filter by race number */
  raceNo?: number;
  /** Filter by meet/track */
  meet?: string;
  /** Include enriched data */
  includeEnriched?: boolean;
  /** Include performance metrics */
  includeMetrics?: boolean;
}

/**
 * Query parameters for horse data endpoints
 */
export interface HorseQueryParams extends PaginationParams {
  /** Filter by horse number */
  hrNo?: string;
  /** Filter by horse name (partial match) */
  hrName?: string;
  /** Filter by meet/track */
  meet?: string;
  /** Filter by rank/grade */
  rank?: string;
  /** Include race history */
  includeHistory?: boolean;
}

/**
 * Query parameters for jockey data endpoints
 */
export interface JockeyQueryParams extends PaginationParams {
  /** Filter by jockey number */
  jkNo?: string;
  /** Filter by jockey name (partial match) */
  jkName?: string;
  /** Filter by meet/track */
  meet?: string;
  /** Filter by part (프리기수, 전속기수 등) */
  part?: string;
  /** Include performance statistics */
  includeStats?: boolean;
}

/**
 * Query parameters for trainer data endpoints
 */
export interface TrainerQueryParams extends PaginationParams {
  /** Filter by trainer number */
  trNo?: string;
  /** Filter by trainer name (partial match) */
  trName?: string;
  /** Filter by meet/track */
  meet?: string;
  /** Minimum win rate filter */
  minWinRate?: number;
  /** Include performance statistics */
  includeStats?: boolean;
}

// ============================================================================
// Data Enrichment Types
// ============================================================================

/**
 * Request to enrich existing race data
 */
export interface EnrichmentRequest {
  /** Race date in YYYY-MM-DD format */
  date: string;
  /** Race number */
  raceNo: number;
  /** Meet identifier */
  meet: string;
  /** Types of enrichment to perform */
  enrichmentTypes: EnrichmentType[];
  /** Force re-enrichment even if already enriched */
  forceRefresh?: boolean;
}

/**
 * Types of data enrichment available
 */
export type EnrichmentType = 'horse_info' | 'jockey_info' | 'trainer_info' | 'performance_metrics';

/**
 * Response from data enrichment operation
 */
export interface EnrichmentResponse extends ApiResponse<EnrichedRaceData> {}

// ============================================================================
// Analytics & Statistics Types
// ============================================================================

/**
 * Request for performance analytics
 */
export interface AnalyticsRequest {
  /** Analysis period start date */
  startDate: string;
  /** Analysis period end date */
  endDate: string;
  /** Entity type to analyze */
  entityType: 'horse' | 'jockey' | 'trainer';
  /** Specific entity ID (optional) */
  entityId?: string;
  /** Meet filter (optional) */
  meet?: string;
  /** Metrics to calculate */
  metrics: AnalyticsMetric[];
}

/**
 * Available analytics metrics
 */
export type AnalyticsMetric = 
  | 'win_rate' 
  | 'place_rate' 
  | 'show_rate' 
  | 'avg_odds' 
  | 'total_earnings' 
  | 'consistency_score'
  | 'improvement_trend'
  | 'comparative_ranking';

/**
 * Analytics response
 */
export interface AnalyticsResponse extends ApiResponse<AnalyticsResult> {}

/**
 * Analytics calculation result
 */
export interface AnalyticsResult {
  /** Analysis metadata */
  analysisInfo: {
    entityType: string;
    entityId?: string;
    period: {
      startDate: string;
      endDate: string;
    };
    totalRaces: number;
    totalEntities: number;
  };
  /** Calculated metrics */
  metrics: Record<AnalyticsMetric, number>;
  /** Trend data for time series analysis */
  trends?: {
    dates: string[];
    values: number[];
    metric: AnalyticsMetric;
  }[];
  /** Comparative rankings */
  rankings?: {
    entityId: string;
    entityName: string;
    rank: number;
    value: number;
    metric: AnalyticsMetric;
  }[];
}

// ============================================================================
// Health Check Types
// ============================================================================

/**
 * Health check response
 */
export interface HealthCheckResponse extends ApiResponse<HealthStatus> {}

/**
 * System health status
 */
export interface HealthStatus {
  /** Overall system status */
  status: 'healthy' | 'degraded' | 'unhealthy';
  /** Timestamp of health check */
  timestamp: string;
  /** Individual service statuses */
  services: {
    /** API service status */
    api: ServiceStatus;
    /** Database connection status */
    database: ServiceStatus;
    /** Redis cache status */
    cache: ServiceStatus;
    /** KRA API connectivity status */
    kraApi: ServiceStatus;
  };
  /** System metrics */
  metrics: {
    /** API response time in milliseconds */
    responseTime: number;
    /** Memory usage percentage */
    memoryUsage: number;
    /** CPU usage percentage */
    cpuUsage: number;
    /** Active connections count */
    activeConnections: number;
  };
}

/**
 * Individual service health status
 */
export interface ServiceStatus {
  /** Service status */
  status: 'up' | 'down' | 'degraded';
  /** Response time in milliseconds */
  responseTime?: number;
  /** Last successful check timestamp */
  lastCheck?: string;
  /** Error message if service is down */
  error?: string;
  /** Additional service-specific metadata */
  metadata?: Record<string, any>;
}

// ============================================================================
// WebSocket Types (for real-time updates)
// ============================================================================

/**
 * WebSocket message types
 */
export type WebSocketMessageType = 
  | 'collection_started'
  | 'collection_progress' 
  | 'collection_completed'
  | 'collection_error'
  | 'enrichment_progress'
  | 'system_status';

/**
 * Generic WebSocket message structure
 */
export interface WebSocketMessage<T = any> {
  /** Message type identifier */
  type: WebSocketMessageType;
  /** Message payload */
  payload: T;
  /** Message timestamp */
  timestamp: string;
  /** Unique message ID */
  messageId: string;
  /** Optional correlation ID for request tracking */
  correlationId?: string;
}

/**
 * Collection progress message payload
 */
export interface CollectionProgressPayload {
  /** Current operation */
  operation: string;
  /** Progress percentage (0-100) */
  progress: number;
  /** Current race being processed */
  currentRace?: {
    date: string;
    raceNo: number;
    meet: string;
  };
  /** Estimated time remaining in milliseconds */
  estimatedTimeRemaining?: number;
}

// ============================================================================
// Export utility type for all API responses
// ============================================================================

/**
 * Union type of all possible API response types
 */
export type AnyApiResponse = 
  | ApiResponse
  | ErrorResponse
  | ValidationErrorResponse
  | CollectionResponse
  | BatchCollectionResponse
  | EnrichmentResponse
  | AnalyticsResponse
  | HealthCheckResponse;