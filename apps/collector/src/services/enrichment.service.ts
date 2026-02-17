/**
 * Enrichment Service
 *
 * Service for enriching race data with additional information from multiple APIs
 * Combines race results with horse, jockey, and trainer details and calculates performance metrics
 */

import type {
  Api214Item,
  Api8_2Item,
  Api12_1Item,
  Api19_1Item,
  EnrichedRaceData,
  EnrichedHorseEntry,
} from '../types/kra-api.types.js';
import { KraApiService } from './kraApiService.js';
import { CacheService } from './cache.service.js';
import { AppError } from '../types/index.js';
import logger from '../utils/logger.js';

/**
 * Enrichment options
 */
interface EnrichmentOptions {
  /** Whether to fetch horse details */
  includeHorseDetails?: boolean;
  /** Whether to fetch jockey details */
  includeJockeyDetails?: boolean;
  /** Whether to fetch trainer details */
  includeTrainerDetails?: boolean;
  /** Whether to calculate performance metrics */
  calculateMetrics?: boolean;
  /** Maximum concurrent API calls */
  concurrency?: number;
  /** Whether to use cache */
  useCache?: boolean;
  /** Force refresh cached data */
  forceRefresh?: boolean;
}

/**
 * Enrichment progress callback
 */
type ProgressCallback = (current: number, total: number, operation: string) => void;

/**
 * Batch processing result
 */
interface BatchResult<T> {
  /** Successful results */
  success: T[];
  /** Failed items with errors */
  failed: Array<{ item: any; error: string }>;
  /** Processing statistics */
  stats: {
    total: number;
    successful: number;
    failed: number;
    duration: number;
  };
}

export class EnrichmentService {
  private readonly kraApiService: KraApiService;
  private readonly cacheService: CacheService;

  constructor(kraApiService: KraApiService, cacheService: CacheService) {
    this.kraApiService = kraApiService;
    this.cacheService = cacheService;

    logger.info('Enrichment Service initialized');
  }

  /**
   * Enrich race data with detailed information
   * @param raceData Raw race data from API214_1
   * @param date Race date in YYYY-MM-DD format
   * @param meet Meet identifier
   * @param raceNo Race number
   * @param options Enrichment options
   * @param onProgress Progress callback
   */
  async enrichRaceData(
    raceData: Api214Item[],
    date: string,
    meet: string,
    raceNo: number,
    options: EnrichmentOptions = {},
    onProgress?: ProgressCallback
  ): Promise<EnrichedRaceData> {
    const startTime = Date.now();
    const {
      includeHorseDetails = true,
      includeJockeyDetails = true,
      includeTrainerDetails = true,
      calculateMetrics = true,
      concurrency = 5,
      useCache = true,
      forceRefresh = false,
    } = options;

    logger.info('Starting race data enrichment', {
      date,
      meet,
      raceNo,
      horseCount: raceData.length,
      options,
    });

    try {
      // Step 1: Enrich horse entries with details
      onProgress?.(0, raceData.length, 'Enriching horse entries');

      const enrichedHorses = await this.enrichHorseEntries(
        raceData,
        {
          includeHorseDetails,
          includeJockeyDetails,
          includeTrainerDetails,
          concurrency,
          useCache,
          forceRefresh,
        },
        (current, total) => onProgress?.(current, total, 'Fetching details')
      );

      // Step 2: Calculate performance metrics if requested
      if (calculateMetrics) {
        onProgress?.(raceData.length, raceData.length + 1, 'Calculating metrics');
        this.calculatePerformanceMetrics(enrichedHorses);
      }

      // Build enriched race data
      const enrichedRaceData: EnrichedRaceData = {
        raceInfo: {
          date,
          meet,
          raceNo,
          rcName: raceData[0]?.rcName || '',
          rcDist: raceData[0]?.rcDist || 0,
          track: raceData[0]?.track || '',
          weather: raceData[0]?.weather || '',
        },
        horses: enrichedHorses,
      };

      const duration = Date.now() - startTime;
      logger.info('Race data enrichment completed', {
        date,
        meet,
        raceNo,
        horseCount: enrichedHorses.length,
        duration: `${duration}ms`,
        includeHorseDetails,
        includeJockeyDetails,
        includeTrainerDetails,
        calculateMetrics,
      });

      // Cache the enriched data
      if (useCache && !forceRefresh) {
        await this.cacheService.set('enriched_race', { date, meet, raceNo: raceNo.toString() }, enrichedRaceData);
      }

      onProgress?.(raceData.length + 1, raceData.length + 1, 'Completed');
      return enrichedRaceData;
    } catch (error) {
      const duration = Date.now() - startTime;
      logger.error('Race data enrichment failed', {
        error,
        date,
        meet,
        raceNo,
        duration: `${duration}ms`,
      });

      throw new AppError(
        `Failed to enrich race data: ${error instanceof Error ? error.message : 'Unknown error'}`,
        500,
        true,
        { date, meet, raceNo, duration }
      );
    }
  }

  /**
   * Get cached enriched race data
   * @param date Race date in YYYY-MM-DD format
   * @param meet Meet identifier
   * @param raceNo Race number
   */
  async getCachedEnrichedRaceData(date: string, meet: string, raceNo: number): Promise<EnrichedRaceData | null> {
    try {
      return await this.cacheService.get<EnrichedRaceData>('enriched_race', { date, meet, raceNo: raceNo.toString() });
    } catch (error) {
      logger.error('Failed to get cached enriched race data', {
        error,
        date,
        meet,
        raceNo,
      });
      return null;
    }
  }

  /**
   * Enrich multiple horse entries with parallel processing
   * @private
   */
  private async enrichHorseEntries(
    raceData: Api214Item[],
    options: EnrichmentOptions,
    onProgress?: ProgressCallback
  ): Promise<EnrichedHorseEntry[]> {
    const {
      includeHorseDetails = true,
      includeJockeyDetails = true,
      includeTrainerDetails = true,
      concurrency = 5,
      useCache = true,
      forceRefresh = false,
    } = options;

    const enrichedHorses: EnrichedHorseEntry[] = [];
    let completed = 0;

    // Process horses in batches for better performance
    for (let i = 0; i < raceData.length; i += concurrency) {
      const batch = raceData.slice(i, i + concurrency);
      const batchPromises = batch.map(async (horseEntry) => {
        try {
          const enrichedEntry: EnrichedHorseEntry = { ...horseEntry };

          const detailPromises: Promise<void>[] = [];

          // Fetch horse details
          if (includeHorseDetails && horseEntry.hrNo) {
            detailPromises.push(
              this.fetchHorseDetail(horseEntry.hrNo, useCache, forceRefresh)
                .then((detail) => {
                  enrichedEntry.horseDetail = detail || undefined;
                })
                .catch((error) => {
                  logger.warn('Failed to fetch horse detail', {
                    hrNo: horseEntry.hrNo,
                    error: error.message,
                  });
                })
            );
          }

          // Fetch jockey details
          if (includeJockeyDetails && horseEntry.jkNo) {
            detailPromises.push(
              this.fetchJockeyDetail(horseEntry.jkNo, useCache, forceRefresh)
                .then((detail) => {
                  enrichedEntry.jockeyDetail = detail || undefined;
                })
                .catch((error) => {
                  logger.warn('Failed to fetch jockey detail', {
                    jkNo: horseEntry.jkNo,
                    error: error.message,
                  });
                })
            );
          }

          // Fetch trainer details
          if (includeTrainerDetails && horseEntry.trNo) {
            detailPromises.push(
              this.fetchTrainerDetail(horseEntry.trNo, useCache, forceRefresh)
                .then((detail) => {
                  enrichedEntry.trainerDetail = detail || undefined;
                })
                .catch((error) => {
                  logger.warn('Failed to fetch trainer detail', {
                    trNo: horseEntry.trNo,
                    error: error.message,
                  });
                })
            );
          }

          // Wait for all details to be fetched
          await Promise.allSettled(detailPromises);

          completed++;
          onProgress?.(completed, raceData.length, 'Processing');

          return enrichedEntry;
        } catch (error) {
          logger.error('Failed to enrich horse entry', {
            hrNo: horseEntry.hrNo,
            hrName: horseEntry.hrName,
            error,
          });

          completed++;
          onProgress?.(completed, raceData.length, 'Error occurred');

          // Return the original entry if enrichment fails
          return { ...horseEntry };
        }
      });

      const batchResults = await Promise.allSettled(batchPromises);
      const batchEnriched = batchResults
        .filter((result): result is PromiseFulfilledResult<EnrichedHorseEntry> => result.status === 'fulfilled')
        .map((result) => result.value);

      enrichedHorses.push(...batchEnriched);
    }

    return enrichedHorses;
  }

  /**
   * Fetch horse detail with caching
   * @private
   */
  private async fetchHorseDetail(
    hrNo: string,
    useCache: boolean = true,
    forceRefresh: boolean = false
  ): Promise<Api8_2Item | null> {
    if (!useCache) {
      return await this.kraApiService.getHorseDetail(hrNo);
    }

    if (forceRefresh) {
      await this.cacheService.delete('horse_detail', { hrNo });
    }

    return await this.cacheService.getOrSet('horse_detail', { hrNo }, () => this.kraApiService.getHorseDetail(hrNo));
  }

  /**
   * Fetch jockey detail with caching
   * @private
   */
  private async fetchJockeyDetail(
    jkNo: string,
    useCache: boolean = true,
    forceRefresh: boolean = false
  ): Promise<Api12_1Item | null> {
    if (!useCache) {
      return await this.kraApiService.getJockeyDetail(jkNo);
    }

    if (forceRefresh) {
      await this.cacheService.delete('jockey_detail', { jkNo });
    }

    return await this.cacheService.getOrSet('jockey_detail', { jkNo }, () => this.kraApiService.getJockeyDetail(jkNo));
  }

  /**
   * Fetch trainer detail with caching
   * @private
   */
  private async fetchTrainerDetail(
    trNo: string,
    useCache: boolean = true,
    forceRefresh: boolean = false
  ): Promise<Api19_1Item | null> {
    if (!useCache) {
      return await this.kraApiService.getTrainerDetail(trNo);
    }

    if (forceRefresh) {
      await this.cacheService.delete('trainer_detail', { trNo });
    }

    return await this.cacheService.getOrSet('trainer_detail', { trNo }, () =>
      this.kraApiService.getTrainerDetail(trNo)
    );
  }

  /**
   * Calculate performance metrics for enriched horse entries
   * @private
   */
  private calculatePerformanceMetrics(enrichedHorses: EnrichedHorseEntry[]): void {
    for (const horse of enrichedHorses) {
      try {
        const metrics = {
          horseWinRate: this.calculateWinRate(horse.horseDetail?.ord1CntT || 0, horse.horseDetail?.rcCntT || 0),
          jockeyWinRate: this.calculateWinRate(horse.jockeyDetail?.ord1CntT || 0, horse.jockeyDetail?.rcCntT || 0),
          trainerWinRate: horse.trainerDetail?.winRateT || 0,
          combinedScore: 0,
        };

        // Calculate combined performance score
        metrics.combinedScore = this.calculateCombinedScore(
          metrics.horseWinRate,
          metrics.jockeyWinRate,
          metrics.trainerWinRate,
          horse.rating || 0,
          horse.winOdds || 0
        );

        horse.performanceMetrics = metrics;

        logger.debug('Performance metrics calculated', {
          hrNo: horse.hrNo,
          hrName: horse.hrName,
          metrics,
        });
      } catch (error) {
        logger.warn('Failed to calculate performance metrics', {
          hrNo: horse.hrNo,
          hrName: horse.hrName,
          error,
        });
      }
    }
  }

  /**
   * Calculate win rate percentage
   * @private
   */
  private calculateWinRate(wins: number, total: number): number {
    if (total === 0) return 0;
    return Math.round((wins / total) * 10000) / 100; // Round to 2 decimal places
  }

  /**
   * Calculate combined performance score
   * @private
   */
  private calculateCombinedScore(
    horseWinRate: number,
    jockeyWinRate: number,
    trainerWinRate: number,
    rating: number,
    odds: number
  ): number {
    // Weighted combination of factors
    const horseWeight = 0.4;
    const jockeyWeight = 0.25;
    const trainerWeight = 0.2;
    const ratingWeight = 0.1;
    const oddsWeight = 0.05;

    // Normalize rating (assume max rating of 120)
    const normalizedRating = Math.min(rating / 120, 1) * 100;

    // Inverse odds factor (lower odds = higher score)
    const oddsScore = odds > 0 ? Math.max(0, 100 - odds * 5) : 0;

    const combinedScore =
      horseWinRate * horseWeight +
      jockeyWinRate * jockeyWeight +
      trainerWinRate * trainerWeight +
      normalizedRating * ratingWeight +
      oddsScore * oddsWeight;

    return Math.round(combinedScore * 100) / 100; // Round to 2 decimal places
  }

  /**
   * Batch process multiple races
   * @param races Array of race identifiers
   * @param options Enrichment options
   * @param onProgress Progress callback
   */
  async batchEnrichRaces(
    races: Array<{ date: string; meet: string; raceNo: number }>,
    options: EnrichmentOptions = {},
    onProgress?: (current: number, total: number, currentRace?: (typeof races)[0]) => void
  ): Promise<BatchResult<EnrichedRaceData>> {
    const startTime = Date.now();
    const results: EnrichedRaceData[] = [];
    const failed: Array<{ item: (typeof races)[0]; error: string }> = [];

    logger.info('Starting batch race enrichment', {
      raceCount: races.length,
      options,
    });

    for (let i = 0; i < races.length; i++) {
      const race = races[i];
      if (!race) continue;

      onProgress?.(i, races.length, race);

      try {
        // First get the race data
        const raceData = await this.kraApiService.getRaceResult(race.date.replace(/-/g, ''), race.meet, race.raceNo);

        // Then enrich it
        const enrichedData = await this.enrichRaceData(raceData, race.date, race.meet, race.raceNo, options);

        results.push(enrichedData);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        logger.error('Failed to enrich race in batch', {
          race,
          error: errorMessage,
        });
        failed.push({ item: race, error: errorMessage });
      }
    }

    onProgress?.(races.length, races.length);

    const duration = Date.now() - startTime;
    const stats = {
      total: races.length,
      successful: results.length,
      failed: failed.length,
      duration,
    };

    logger.info('Batch race enrichment completed', stats);

    return { success: results, failed, stats };
  }
}
