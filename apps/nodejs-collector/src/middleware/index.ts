// Middleware exports
export { errorHandler, notFoundHandler } from './errorHandler.js';
export { requestLogger } from './requestLogger.js';

// Rate limiting middleware
export {
  generalRateLimit,
  strictRateLimit,
  apiCollectionRateLimit,
  gradualSlowDown,
  createRateLimit,
  cleanup as rateLimitCleanup
} from './rate-limit.middleware.js';

// Validation middleware
export {
  handleValidationErrors,
  validateDate,
  validateMeet,
  validateRaceNo,
  validateOptionalRaceNo,
  validateHorseId,
  validateJockeyId,
  validateTrainerId,
  validatePagination,
  validateSort,
  validateBoolean,
  validateArray,
  validateCollectionRequest,
  validateRaceParams,
  validateHorseParams,
  validateJockeyParams,
  validateTrainerParams,
  validateEnrichmentRequest,
  createCustomValidator,
  sanitizeInput,
  createValidationMiddleware
} from './validation.middleware.js';

// Authentication middleware
export {
  requireAuth,
  optionalAuth,
  requirePermission,
  requireAnyPermission,
  requireAllPermissions,
  configureEndpointAccess,
  addApiKey,
  removeApiKey,
  listApiKeys,
  cleanup as authCleanup
} from './auth.middleware.js';

// Logging middleware
export {
  requestLogger as detailedRequestLogger,
  errorLogger,
  performanceLogger,
  healthCheckLogger,
  securityLogger
} from './logging.middleware.js';

// Middleware registry and helpers
export {
  registerGlobalMiddleware,
  registerApiMiddleware,
  registerErrorHandling,
  registerAllMiddleware,
  createRouteMiddleware,
  middlewarePresets,
  default as registerMiddleware
} from './middleware-registry.js';

// Type exports for TypeScript support
export type { AuthenticatedRequest } from './auth.middleware.js';
export type { LoggingRequest } from './logging.middleware.js';
export type { MiddlewareConfig } from './middleware-registry.js';