/**
 * Services Export
 *
 * Central export point for all service classes with dependency injection setup
 */

import { KraApiService } from './kraApiService.js';
import { CacheService } from './cache.service.js';
import { EnrichmentService } from './enrichment.service.js';
import { CollectionService } from './collection.service.js';
import logger from '../utils/logger.js';

// Service exports
export { KraApiService } from './kraApiService.js';
export { CacheService } from './cache.service.js';
export { EnrichmentService } from './enrichment.service.js';
export { CollectionService } from './collection.service.js';

/**
 * Service container for dependency injection
 */
export class ServiceContainer {
  private static instance: ServiceContainer;

  public readonly kraApiService: KraApiService;
  public readonly cacheService: CacheService;
  public readonly enrichmentService: EnrichmentService;
  public readonly collectionService: CollectionService;

  // Alias for backwards compatibility
  public get kra() {
    return this.kraApiService;
  }
  public get cache() {
    return this.cacheService;
  }
  public get enrichment() {
    return this.enrichmentService;
  }
  public get collection() {
    return this.collectionService;
  }

  private constructor() {
    logger.info('Initializing service container');

    // Initialize services with dependency injection
    this.kraApiService = new KraApiService();
    this.cacheService = new CacheService();
    this.enrichmentService = new EnrichmentService(this.kraApiService, this.cacheService);
    this.collectionService = new CollectionService(this.kraApiService, this.cacheService, this.enrichmentService);

    logger.info('Service container initialized successfully');
  }

  /**
   * Get singleton instance of service container
   */
  public static getInstance(): ServiceContainer {
    if (!ServiceContainer.instance) {
      ServiceContainer.instance = new ServiceContainer();
    }
    return ServiceContainer.instance;
  }

  /**
   * Health check for all services
   */
  async healthCheck(): Promise<Record<string, boolean>> {
    const results: Record<string, boolean> = {};

    try {
      results.kraApi = await this.kraApiService.healthCheck();
    } catch (error) {
      logger.error('KRA API health check failed', { error });
      results.kraApi = false;
    }

    // Cache service doesn't need health check - it always works with fallback
    results.cache = true;

    // Enrichment and Collection services depend on others, so they're healthy if dependencies are
    results.enrichment = results.kraApi;
    results.collection = results.kraApi;

    return results;
  }

  /**
   * Get cache statistics
   */
  getCacheStats() {
    return this.cacheService.getStats();
  }

  /**
   * Clear all caches
   */
  async clearAllCaches(): Promise<void> {
    const cacheTypes = ['race_result', 'horse_detail', 'jockey_detail', 'trainer_detail', 'enriched_race'] as const;

    await Promise.all(cacheTypes.map((type) => this.cacheService.clear(type)));

    logger.info('All caches cleared');
  }
}

/**
 * Default service container instance
 */
export const services = ServiceContainer.getInstance();
