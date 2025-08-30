/**
 * Cache Service
 *
 * Generic caching service with Redis as primary storage and file system as fallback
 * Provides type-safe operations with TTL management and cache invalidation
 */

import { Redis } from 'ioredis';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as crypto from 'crypto';
import { getRedisClient } from '../utils/redis.js';
import logger from '../utils/logger.js';
import { AppError } from '../types/index.js';

/**
 * Cache configuration options
 */
interface CacheOptions {
  /** Time to live in seconds */
  ttl?: number;
  /** Whether to use compression */
  compress?: boolean;
  /** Whether to use file fallback if Redis is unavailable */
  useFileFallback?: boolean;
}

/**
 * Cache key configuration for different data types
 */
interface CacheKeyConfig {
  /** Key prefix */
  prefix: string;
  /** Default TTL in seconds */
  ttl: number;
}

/**
 * Cache entry with metadata
 */
interface CacheEntry<T> {
  /** Cached data */
  data: T;
  /** Creation timestamp */
  createdAt: number;
  /** Expiration timestamp */
  expiresAt: number;
  /** Data version for cache invalidation */
  version?: string;
}

/**
 * Cache statistics
 */
export interface CacheStats {
  /** Number of cache hits */
  hits: number;
  /** Number of cache misses */
  misses: number;
  /** Hit rate percentage */
  hitRate: number;
  /** Total operations */
  totalOperations: number;
}

export class CacheService {
  private readonly redisClient: Redis | null;
  private readonly fileCache: boolean;
  private readonly fileCacheDir: string;
  private readonly stats: CacheStats;

  // Cache key configurations
  private readonly keyConfigs: Record<string, CacheKeyConfig> = {
    race_result: { prefix: 'kra:race', ttl: 3600 }, // 1 hour
    horse_detail: { prefix: 'kra:horse', ttl: 604800 }, // 7 days
    jockey_detail: { prefix: 'kra:jockey', ttl: 604800 }, // 7 days
    trainer_detail: { prefix: 'kra:trainer', ttl: 604800 }, // 7 days
    enriched_race: { prefix: 'kra:enriched', ttl: 3600 }, // 1 hour
    api_response: { prefix: 'kra:api', ttl: 1800 }, // 30 minutes
  };

  constructor(fileCacheDir: string = './cache') {
    this.redisClient = getRedisClient();
    this.fileCache = true; // Always enable file fallback
    this.fileCacheDir = fileCacheDir;
    this.stats = {
      hits: 0,
      misses: 0,
      hitRate: 0,
      totalOperations: 0,
    };

    this.initializeFileCache();
    logger.info('Cache Service initialized', {
      redisAvailable: Boolean(this.redisClient),
      fileCacheEnabled: this.fileCache,
      fileCacheDir: this.fileCacheDir,
    });
  }

  /**
   * Get cached data with type safety
   * @param keyType Cache key type configuration
   * @param keyParams Parameters to build the cache key
   * @param options Cache options
   */
  async get<T>(
    keyType: keyof typeof this.keyConfigs,
    keyParams: Record<string, string | number>,
    options: CacheOptions = {}
  ): Promise<T | null> {
    const key = this.buildKey(keyType, keyParams);

    try {
      // Try Redis first if available
      if (this.redisClient) {
        const result = await this.getFromRedis<T>(key);
        if (result !== null) {
          this.incrementHits();
          logger.debug('Cache hit (Redis)', { key, keyType });
          return result;
        }
      }

      // Fallback to file cache
      if (this.fileCache && options.useFileFallback !== false) {
        const result = await this.getFromFile<T>(key);
        if (result !== null) {
          // Store in Redis for faster access next time
          if (this.redisClient && result) {
            const config = this.keyConfigs[keyType];
            if (config) {
              await this.setToRedis(key, result, config.ttl);
            }
          }
          this.incrementHits();
          logger.debug('Cache hit (File)', { key, keyType });
          return result;
        }
      }

      this.incrementMisses();
      logger.debug('Cache miss', { key, keyType });
      return null;
    } catch (error) {
      logger.error('Cache get error', { error, key, keyType });
      this.incrementMisses();
      return null;
    }
  }

  /**
   * Set cached data with TTL
   * @param keyType Cache key type configuration
   * @param keyParams Parameters to build the cache key
   * @param data Data to cache
   * @param options Cache options
   */
  async set<T>(
    keyType: keyof typeof this.keyConfigs,
    keyParams: Record<string, string | number>,
    data: T,
    options: CacheOptions = {}
  ): Promise<void> {
    const key = this.buildKey(keyType, keyParams);
    const config = this.keyConfigs[keyType];
    const ttl = options.ttl || config?.ttl || 3600;

    try {
      const promises: Promise<void>[] = [];

      // Store in Redis if available
      if (this.redisClient) {
        promises.push(this.setToRedis(key, data, ttl));
      }

      // Store in file cache
      if (this.fileCache) {
        promises.push(this.setToFile(key, data, ttl));
      }

      await Promise.allSettled(promises);

      logger.debug('Cache set', { key, keyType, ttl });
    } catch (error) {
      logger.error('Cache set error', { error, key, keyType });
      throw new AppError(`Failed to cache data: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Delete cached data
   * @param keyType Cache key type configuration
   * @param keyParams Parameters to build the cache key
   */
  async delete(keyType: keyof typeof this.keyConfigs, keyParams: Record<string, string | number>): Promise<void> {
    const key = this.buildKey(keyType, keyParams);

    try {
      const promises: Promise<void>[] = [];

      // Delete from Redis if available
      if (this.redisClient) {
        promises.push(this.deleteFromRedis(key));
      }

      // Delete from file cache
      if (this.fileCache) {
        promises.push(this.deleteFromFile(key));
      }

      await Promise.allSettled(promises);

      logger.debug('Cache delete', { key, keyType });
    } catch (error) {
      logger.error('Cache delete error', { error, key, keyType });
    }
  }

  /**
   * Clear all cache entries for a specific type
   * @param keyType Cache key type to clear
   */
  async clear(keyType: keyof typeof this.keyConfigs): Promise<void> {
    const config = this.keyConfigs[keyType];
    if (!config) return;

    const pattern = `${config.prefix}:*`;

    try {
      const promises: Promise<void>[] = [];

      // Clear from Redis if available
      if (this.redisClient) {
        promises.push(this.clearFromRedis(pattern));
      }

      // Clear from file cache
      if (this.fileCache) {
        promises.push(this.clearFromFile(pattern));
      }

      await Promise.allSettled(promises);

      logger.info('Cache cleared', { keyType, pattern });
    } catch (error) {
      logger.error('Cache clear error', { error, keyType });
    }
  }

  /**
   * Get cache statistics
   */
  getStats(): CacheStats {
    this.updateHitRate();
    return { ...this.stats };
  }

  /**
   * Check if a key exists in cache
   * @param keyType Cache key type configuration
   * @param keyParams Parameters to build the cache key
   */
  async exists(keyType: keyof typeof this.keyConfigs, keyParams: Record<string, string | number>): Promise<boolean> {
    const key = this.buildKey(keyType, keyParams);

    try {
      // Check Redis first if available
      if (this.redisClient) {
        const exists = await this.redisClient.exists(key);
        if (exists) return true;
      }

      // Check file cache
      if (this.fileCache) {
        return await this.fileExists(key);
      }

      return false;
    } catch (error) {
      logger.error('Cache exists check error', { error, key, keyType });
      return false;
    }
  }

  /**
   * Get or set pattern - get data if exists, otherwise compute and cache
   * @param keyType Cache key type configuration
   * @param keyParams Parameters to build the cache key
   * @param computeFn Function to compute data if not in cache
   * @param options Cache options
   */
  async getOrSet<T>(
    keyType: keyof typeof this.keyConfigs,
    keyParams: Record<string, string | number>,
    computeFn: () => Promise<T>,
    options: CacheOptions = {}
  ): Promise<T> {
    // Try to get from cache first
    const cachedData = await this.get<T>(keyType, keyParams, options);
    if (cachedData !== null) {
      return cachedData;
    }

    // Compute the data
    const data = await computeFn();

    // Cache the computed data
    await this.set(keyType, keyParams, data, options);

    return data;
  }

  /**
   * Build cache key from type and parameters
   * @private
   */
  private buildKey(keyType: keyof typeof this.keyConfigs, keyParams: Record<string, string | number>): string {
    const config = this.keyConfigs[keyType];
    if (!config) {
      throw new Error(`Unknown cache key type: ${keyType}`);
    }

    const paramString = Object.entries(keyParams)
      .sort(([a], [b]) => a.localeCompare(b)) // Sort for consistent keys
      .map(([key, value]) => `${key}:${value}`)
      .join(':');

    return `${config.prefix}:${paramString}`;
  }

  /**
   * Get data from Redis
   * @private
   */
  private async getFromRedis<T>(key: string): Promise<T | null> {
    if (!this.redisClient) return null;

    try {
      const data = await this.redisClient.get(key);
      if (!data) return null;

      const entry: CacheEntry<T> = JSON.parse(data);

      // Check expiration
      if (entry.expiresAt < Date.now()) {
        await this.redisClient.del(key);
        return null;
      }

      return entry.data;
    } catch (error) {
      logger.error('Redis get error', { error, key });
      return null;
    }
  }

  /**
   * Set data to Redis
   * @private
   */
  private async setToRedis<T>(key: string, data: T, ttl: number): Promise<void> {
    if (!this.redisClient) return;

    try {
      const entry: CacheEntry<T> = {
        data,
        createdAt: Date.now(),
        expiresAt: Date.now() + ttl * 1000,
      };

      await this.redisClient.setex(key, ttl, JSON.stringify(entry));
    } catch (error) {
      logger.error('Redis set error', { error, key });
    }
  }

  /**
   * Delete data from Redis
   * @private
   */
  private async deleteFromRedis(key: string): Promise<void> {
    if (!this.redisClient) return;

    try {
      await this.redisClient.del(key);
    } catch (error) {
      logger.error('Redis delete error', { error, key });
    }
  }

  /**
   * Clear data from Redis by pattern
   * @private
   */
  private async clearFromRedis(pattern: string): Promise<void> {
    if (!this.redisClient) return;

    try {
      const keys = await this.redisClient.keys(pattern);
      if (keys.length > 0) {
        await this.redisClient.del(...keys);
      }
    } catch (error) {
      logger.error('Redis clear error', { error, pattern });
    }
  }

  /**
   * Get data from file cache
   * @private
   */
  private async getFromFile<T>(key: string): Promise<T | null> {
    try {
      const filePath = this.getFilePath(key);
      const data = await fs.readFile(filePath, 'utf-8');
      const entry: CacheEntry<T> = JSON.parse(data);

      // Check expiration
      if (entry.expiresAt < Date.now()) {
        await this.deleteFromFile(key);
        return null;
      }

      return entry.data;
    } catch (error) {
      // File not found or other error
      return null;
    }
  }

  /**
   * Set data to file cache
   * @private
   */
  private async setToFile<T>(key: string, data: T, ttl: number): Promise<void> {
    try {
      const filePath = this.getFilePath(key);
      const entry: CacheEntry<T> = {
        data,
        createdAt: Date.now(),
        expiresAt: Date.now() + ttl * 1000,
      };

      // Ensure directory exists
      await fs.mkdir(path.dirname(filePath), { recursive: true });

      await fs.writeFile(filePath, JSON.stringify(entry), 'utf-8');
    } catch (error) {
      logger.error('File cache set error', { error, key });
    }
  }

  /**
   * Delete data from file cache
   * @private
   */
  private async deleteFromFile(key: string): Promise<void> {
    try {
      const filePath = this.getFilePath(key);
      await fs.unlink(filePath);
    } catch (error) {
      // Ignore file not found errors
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
        logger.error('File cache delete error', { error, key });
      }
    }
  }

  /**
   * Clear file cache by pattern
   * @private
   */
  private async clearFromFile(pattern: string): Promise<void> {
    try {
      const prefix = pattern.replace(':*', '');
      const files = await fs.readdir(this.fileCacheDir, { recursive: true });

      const filesToDelete = files
        .filter((file) => typeof file === 'string' && file.includes(this.hashKey(prefix)))
        .map((file) => path.join(this.fileCacheDir, file as string));

      await Promise.all(
        filesToDelete.map((file) =>
          fs.unlink(file).catch((err) => {
            if ((err as NodeJS.ErrnoException).code !== 'ENOENT') {
              logger.error('File cache clear error', { error: err, file });
            }
          })
        )
      );
    } catch (error) {
      logger.error('File cache clear error', { error, pattern });
    }
  }

  /**
   * Check if file exists in cache
   * @private
   */
  private async fileExists(key: string): Promise<boolean> {
    try {
      const filePath = this.getFilePath(key);
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get file path for cache key
   * @private
   */
  private getFilePath(key: string): string {
    const hash = this.hashKey(key);
    const dir = hash.substring(0, 2);
    return path.join(this.fileCacheDir, dir, `${hash}.json`);
  }

  /**
   * Hash cache key for file name
   * @private
   */
  private hashKey(key: string): string {
    return crypto.createHash('sha256').update(key).digest('hex');
  }

  /**
   * Initialize file cache directory
   * @private
   */
  private async initializeFileCache(): Promise<void> {
    if (!this.fileCache) return;

    try {
      await fs.mkdir(this.fileCacheDir, { recursive: true });
    } catch (error) {
      logger.error('Failed to initialize file cache directory', { error, dir: this.fileCacheDir });
      throw new AppError('Failed to initialize file cache');
    }
  }

  /**
   * Increment cache hit counter
   * @private
   */
  private incrementHits(): void {
    this.stats.hits++;
    this.stats.totalOperations++;
  }

  /**
   * Increment cache miss counter
   * @private
   */
  private incrementMisses(): void {
    this.stats.misses++;
    this.stats.totalOperations++;
  }

  /**
   * Update hit rate calculation
   * @private
   */
  private updateHitRate(): void {
    this.stats.hitRate = this.stats.totalOperations > 0 ? (this.stats.hits / this.stats.totalOperations) * 100 : 0;
  }
}
