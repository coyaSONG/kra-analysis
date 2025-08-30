import type { Request, Response, NextFunction } from 'express';
import { AppError } from '../types/index.js';
import logger from '../utils/logger.js';

/**
 * Extended Request interface to include user information
 */
export interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    apiKey: string;
    permissions?: string[];
    rateLimitTier?: 'basic' | 'premium' | 'enterprise';
  };
}

/**
 * API key validation interface
 */
interface ApiKeyInfo {
  id: string;
  key: string;
  name?: string;
  permissions: string[];
  rateLimitTier: 'basic' | 'premium' | 'enterprise';
  enabled: boolean;
  createdAt: Date;
  lastUsed?: Date;
}

/**
 * In-memory API key store (in production, this would come from database)
 * This is a basic implementation - in production you'd want to use a proper database
 */
const apiKeys: Map<string, ApiKeyInfo> = new Map();

// Initialize with some default API keys if needed
const initializeApiKeys = () => {
  if (process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test') {
    // Development API keys
    const devKey = process.env.DEV_API_KEY || 'dev-key-12345';
    apiKeys.set(devKey, {
      id: 'dev-user',
      key: devKey,
      name: 'Development Key',
      permissions: ['read', 'write', 'admin'],
      rateLimitTier: 'enterprise',
      enabled: true,
      createdAt: new Date(),
    });
  }

  // Production API keys from environment
  const adminKey = process.env.ADMIN_API_KEY;
  if (adminKey) {
    apiKeys.set(adminKey, {
      id: 'admin-user',
      key: adminKey,
      name: 'Admin Key',
      permissions: ['read', 'write', 'admin'],
      rateLimitTier: 'enterprise',
      enabled: true,
      createdAt: new Date(),
    });
  }

  const userKey = process.env.USER_API_KEY;
  if (userKey) {
    apiKeys.set(userKey, {
      id: 'user',
      key: userKey,
      name: 'User Key',
      permissions: ['read', 'write'],
      rateLimitTier: 'premium',
      enabled: true,
      createdAt: new Date(),
    });
  }

  const readOnlyKey = process.env.READONLY_API_KEY;
  if (readOnlyKey) {
    apiKeys.set(readOnlyKey, {
      id: 'readonly-user',
      key: readOnlyKey,
      name: 'Read Only Key',
      permissions: ['read'],
      rateLimitTier: 'basic',
      enabled: true,
      createdAt: new Date(),
    });
  }
};

// Initialize API keys on module load
initializeApiKeys();

/**
 * Extract API key from request headers
 */
const extractApiKey = (req: Request): string | null => {
  // Check Authorization header (Bearer token)
  const authHeader = req.get('Authorization');
  if (authHeader && authHeader.startsWith('Bearer ')) {
    return authHeader.substring(7);
  }

  // Check X-API-Key header
  const apiKeyHeader = req.get('X-API-Key');
  if (apiKeyHeader) {
    return apiKeyHeader;
  }

  // Check query parameter (less secure, not recommended for production)
  const apiKeyQuery = req.query.api_key as string;
  if (apiKeyQuery) {
    return apiKeyQuery;
  }

  return null;
};

/**
 * Validate API key and return user information
 */
const validateApiKey = async (apiKey: string): Promise<ApiKeyInfo | null> => {
  // In production, this would query a database
  const keyInfo = apiKeys.get(apiKey);

  if (!keyInfo || !keyInfo.enabled) {
    return null;
  }

  // Update last used timestamp
  keyInfo.lastUsed = new Date();
  apiKeys.set(apiKey, keyInfo);

  return keyInfo;
};

/**
 * Required authentication middleware
 * Requires valid API key for all requests
 */
export const requireAuth = async (req: AuthenticatedRequest, res: Response, next: NextFunction): Promise<void> => {
  try {
    const apiKey = extractApiKey(req);

    if (!apiKey) {
      throw new AppError(
        'API key required. Please provide API key in Authorization header (Bearer token) or X-API-Key header.',
        401,
        true,
        { endpoint: req.path, method: req.method }
      );
    }

    const keyInfo = await validateApiKey(apiKey);

    if (!keyInfo) {
      logger.warn('Invalid API key attempt:', {
        ip: req.ip,
        userAgent: req.get('User-Agent'),
        endpoint: req.path,
        method: req.method,
        apiKey: apiKey.substring(0, 8) + '...', // Log only first 8 characters for security
      });

      throw new AppError('Invalid API key', 401, true, { endpoint: req.path, method: req.method });
    }

    // Add user information to request
    req.user = {
      id: keyInfo.id,
      apiKey: keyInfo.key,
      permissions: keyInfo.permissions,
      rateLimitTier: keyInfo.rateLimitTier,
    };

    // Log successful authentication (debug level)
    logger.debug('API key authenticated:', {
      userId: keyInfo.id,
      endpoint: req.path,
      method: req.method,
      rateLimitTier: keyInfo.rateLimitTier,
    });

    next();
  } catch (error) {
    next(error);
  }
};

/**
 * Optional authentication middleware
 * Allows requests without API key but adds user info if present
 */
export const optionalAuth = async (req: AuthenticatedRequest, res: Response, next: NextFunction): Promise<void> => {
  try {
    const apiKey = extractApiKey(req);

    if (apiKey) {
      const keyInfo = await validateApiKey(apiKey);

      if (keyInfo) {
        req.user = {
          id: keyInfo.id,
          apiKey: keyInfo.key,
          permissions: keyInfo.permissions,
          rateLimitTier: keyInfo.rateLimitTier,
        };

        logger.debug('Optional API key authenticated:', {
          userId: keyInfo.id,
          endpoint: req.path,
          method: req.method,
        });
      } else {
        logger.warn('Invalid API key in optional auth:', {
          ip: req.ip,
          endpoint: req.path,
          method: req.method,
        });
      }
    }

    next();
  } catch (error) {
    next(error);
  }
};

/**
 * Permission-based authorization middleware factory
 */
export const requirePermission = (permission: string) => {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
    if (!req.user) {
      throw new AppError('Authentication required', 401, true, { requiredPermission: permission });
    }

    if (!req.user.permissions || !req.user.permissions.includes(permission)) {
      logger.warn('Insufficient permissions:', {
        userId: req.user.id,
        requiredPermission: permission,
        userPermissions: req.user.permissions,
        endpoint: req.path,
        method: req.method,
      });

      throw new AppError(`Insufficient permissions. Required: ${permission}`, 403, true, {
        requiredPermission: permission,
        userPermissions: req.user.permissions,
      });
    }

    next();
  };
};

/**
 * Multiple permissions authorization (requires ANY of the specified permissions)
 */
export const requireAnyPermission = (permissions: string[]) => {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
    if (!req.user) {
      throw new AppError('Authentication required', 401, true, { requiredPermissions: permissions });
    }

    if (!req.user.permissions) {
      throw new AppError('No permissions assigned', 403, true, { requiredPermissions: permissions });
    }

    const hasPermission = permissions.some((permission) => req.user!.permissions!.includes(permission));

    if (!hasPermission) {
      logger.warn('Insufficient permissions (any):', {
        userId: req.user.id,
        requiredPermissions: permissions,
        userPermissions: req.user.permissions,
        endpoint: req.path,
        method: req.method,
      });

      throw new AppError(`Insufficient permissions. Required any of: ${permissions.join(', ')}`, 403, true, {
        requiredPermissions: permissions,
        userPermissions: req.user.permissions,
      });
    }

    next();
  };
};

/**
 * Multiple permissions authorization (requires ALL of the specified permissions)
 */
export const requireAllPermissions = (permissions: string[]) => {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
    if (!req.user) {
      throw new AppError('Authentication required', 401, true, { requiredPermissions: permissions });
    }

    if (!req.user.permissions) {
      throw new AppError('No permissions assigned', 403, true, { requiredPermissions: permissions });
    }

    const hasAllPermissions = permissions.every((permission) => req.user!.permissions!.includes(permission));

    if (!hasAllPermissions) {
      const missingPermissions = permissions.filter((permission) => !req.user!.permissions!.includes(permission));

      logger.warn('Missing required permissions:', {
        userId: req.user.id,
        requiredPermissions: permissions,
        missingPermissions,
        userPermissions: req.user.permissions,
        endpoint: req.path,
        method: req.method,
      });

      throw new AppError(`Missing required permissions: ${missingPermissions.join(', ')}`, 403, true, {
        requiredPermissions: permissions,
        missingPermissions,
        userPermissions: req.user.permissions,
      });
    }

    next();
  };
};

/**
 * Configure endpoint access (public, private, or optional auth)
 */
export const configureEndpointAccess = (type: 'public' | 'private' | 'optional' = 'optional') => {
  switch (type) {
    case 'public':
      // No authentication required, but still try to get user info if available
      return optionalAuth;
    case 'private':
      // Authentication required
      return requireAuth;
    case 'optional':
    default:
      // Authentication optional
      return optionalAuth;
  }
};

/**
 * Add API key management functions
 */
export const addApiKey = (keyInfo: Omit<ApiKeyInfo, 'createdAt'>): void => {
  apiKeys.set(keyInfo.key, {
    ...keyInfo,
    createdAt: new Date(),
  });
};

export const removeApiKey = (apiKey: string): boolean => {
  return apiKeys.delete(apiKey);
};

export const listApiKeys = (): ApiKeyInfo[] => {
  return Array.from(apiKeys.values()).map((key) => ({
    ...key,
    key: key.key.substring(0, 8) + '...', // Mask the key for security
  })) as ApiKeyInfo[];
};

/**
 * Cleanup function
 */
export const cleanup = (): void => {
  apiKeys.clear();
  logger.info('Auth middleware cleaned up');
};
