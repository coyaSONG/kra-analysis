/**
 * Collection Service
 *
 * Main orchestrator for data collection operations
 * Handles batch processing, error recovery, and progress tracking
 */

import type { Api214Item } from '../types/kra-api.types.js';
import type {
  CollectionRequest,
  CollectedRaceData,
  BatchCollectionRequest,
  BatchCollectionResult,
} from '../types/api.types.js';
import { KraApiService } from './kraApiService.js';
import { CacheService } from './cache.service.js';
import { EnrichmentService } from './enrichment.service.js';
import { AppError, ValidationError } from '../types/index.js';
import { meetToApiParam } from '../utils/meet-converter.js';
import logger from '../utils/logger.js';

/**
 * Collection options
 */
interface CollectionOptions {
  /** Whether to use cache */
  useCache?: boolean;
  /** Force refresh cached data */
  forceRefresh?: boolean;
  /** Maximum concurrent operations */
  concurrency?: number;
  /** Request timeout in milliseconds */
  timeout?: number;
  /** Number of retry attempts */
  retryAttempts?: number;
}

/**
 * Collection progress information
 */
interface CollectionProgress {
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
  /** Start time */
  startTime: number;
}

/**
 * Progress callback function
 */
type ProgressCallback = (progress: CollectionProgress) => void;

export class CollectionService {
  private readonly kraApiService: KraApiService;
  private readonly cacheService: CacheService;
  private readonly enrichmentService: EnrichmentService;

  constructor(kraApiService: KraApiService, cacheService: CacheService, enrichmentService: EnrichmentService) {
    this.kraApiService = kraApiService;
    this.cacheService = cacheService;
    this.enrichmentService = enrichmentService;

    logger.info('Collection Service initialized');
  }

  /**
   * Collect single race data
   * @param request Collection request
   * @param options Collection options
   * @param onProgress Progress callback
   */
  async collectRace(
    request: CollectionRequest,
    options: CollectionOptions = {},
    onProgress?: ProgressCallback
  ): Promise<CollectedRaceData> {
    const startTime = Date.now();
    const { useCache = true, forceRefresh = false, timeout = 30000, retryAttempts = 3 } = options;

    // Validate request
    this.validateCollectionRequest(request);

    const { date, raceNo, meet, enrichData = false } = request;

    logger.info('Starting race collection', {
      date,
      raceNo,
      meet,
      enrichData,
      useCache,
      forceRefresh,
    });

    try {
      // Step 1: Check cache first
      onProgress?.({
        operation: 'Checking cache',
        progress: 5,
        currentRace: { date, raceNo: raceNo || 0, meet: meet || '' },
        startTime,
      });

      if (useCache && !forceRefresh && raceNo !== undefined) {
        const cachedData = await this.cacheService.get<CollectedRaceData>('race_result', {
          date: date,
          meet: meet || '',
          raceNo: raceNo.toString(),
        });

        if (cachedData) {
          logger.info('Race data found in cache', { date, raceNo, meet });
          onProgress?.({
            operation: 'Completed (from cache)',
            progress: 100,
            currentRace: { date, raceNo, meet: meet || '' },
            startTime,
          });
          return cachedData;
        }
      }

      // Step 2: Fetch race data from API
      onProgress?.({
        operation: 'Fetching race data',
        progress: 20,
        currentRace: { date, raceNo: raceNo || 0, meet: meet || '' },
        startTime,
      });

      // eslint-disable-next-line prefer-const
      let raceData: Api214Item[];

      if (raceNo === undefined || raceNo === null) {
        throw new ValidationError('Race number is required for single race collection');
      }

      // Collect specific race - convert meet to API parameter format (numeric code)
      const apiMeet = meet ? meetToApiParam(meet) : '';
      raceData = await this.kraApiService.getRaceResult(date, apiMeet, raceNo, { timeout, retryAttempts });

      if (raceData.length === 0) {
        throw new AppError(`No race data found for ${date} race ${raceNo}`, 404);
      }

      // Step 3: Build basic collected data
      const firstRace = raceData[0];
      if (!firstRace) {
        throw new AppError(`No race data found for ${date} race ${raceNo}`, 404);
      }

      const collectedData: CollectedRaceData = {
        raceInfo: {
          date,
          meet: meet || firstRace.meet,
          raceNo: raceNo,
          rcName: firstRace.rcName,
          rcDist: firstRace.rcDist,
          track: firstRace.track,
          weather: firstRace.weather,
          totalHorses: raceData.length,
        },
        raceResult: raceData,
        collectionMeta: {
          collectedAt: new Date().toISOString(),
          isEnriched: false,
          dataSource: 'kra_api',
        },
      };

      // Step 4: Enrich data if requested
      if (enrichData) {
        onProgress?.({
          operation: 'Enriching data',
          progress: 60,
          currentRace: { date, raceNo, meet: meet || '' },
          startTime,
        });

        const enrichedData = await this.enrichmentService.enrichRaceData(
          raceData,
          date,
          meet || firstRace.meet,
          raceNo,
          {
            useCache,
            forceRefresh,
          },
          (current, total) => {
            const enrichProgress = 60 + (current / total) * 30; // 60-90%
            onProgress?.({
              operation: `Enriching (${current}/${total})`,
              progress: enrichProgress,
              currentRace: { date, raceNo, meet: meet || '' },
              startTime,
            });
          }
        );

        collectedData.collectionMeta.isEnriched = true;
        (collectedData as any).enrichedData = enrichedData; // Add enriched data
      }

      // Step 5: Cache the result
      if (useCache) {
        onProgress?.({
          operation: 'Caching result',
          progress: 95,
          currentRace: { date, raceNo, meet: meet || '' },
          startTime,
        });

        await this.cacheService.set(
          'race_result',
          { date: date, meet: collectedData.raceInfo.meet, raceNo: raceNo.toString() },
          collectedData
        );
      }

      const duration = Date.now() - startTime;
      logger.info('Race collection completed', {
        date,
        raceNo,
        meet: collectedData.raceInfo.meet,
        horseCount: raceData.length,
        enriched: enrichData,
        duration: `${duration}ms`,
      });

      onProgress?.({
        operation: 'Completed',
        progress: 100,
        currentRace: { date, raceNo, meet: collectedData.raceInfo.meet },
        startTime,
      });

      return collectedData;
    } catch (error) {
      const duration = Date.now() - startTime;
      logger.error('Race collection failed', {
        error,
        date,
        raceNo,
        meet,
        duration: `${duration}ms`,
      });

      if (error instanceof AppError || error instanceof ValidationError) {
        throw error;
      }

      throw new AppError(
        `Failed to collect race data: ${error instanceof Error ? error.message : 'Unknown error'}`,
        500,
        true,
        { date, raceNo, meet, duration }
      );
    }
  }

  /**
   * Collect multiple races in batch
   * @param request Batch collection request
   * @param options Collection options
   * @param onProgress Progress callback
   */
  async collectBatch(
    request: BatchCollectionRequest,
    options: CollectionOptions = {},
    onProgress?: ProgressCallback
  ): Promise<BatchCollectionResult> {
    const startTime = Date.now();
    const { concurrency = 3, useCache = true, forceRefresh = false } = options;

    // Validate request
    this.validateBatchCollectionRequest(request);

    logger.info('Starting batch collection', {
      startDate: request.startDate,
      endDate: request.endDate,
      meets: request.meets,
      concurrency,
      enrichData: request.enrichData,
    });

    try {
      // Step 1: Generate race list
      onProgress?.({
        operation: 'Generating race list',
        progress: 2,
        startTime,
      });

      const raceList = await this.generateRaceList(request);
      logger.info('Generated race list', { totalRaces: raceList.length });

      // Step 2: Process races in batches
      const results: Array<{
        date: string;
        raceNo: number;
        meet: string;
        status: 'success' | 'failed' | 'skipped';
        error?: string;
        dataSize?: number;
      }> = [];

      const errors: string[] = [];
      let completed = 0;

      // Process races with concurrency control
      for (let i = 0; i < raceList.length; i += concurrency) {
        const batch = raceList.slice(i, i + concurrency);

        const batchPromises = batch.map(async (race) => {
          try {
            const collectionRequest: CollectionRequest = {
              date: race.date,
              raceNo: race.raceNo,
              meet: race.meet,
              enrichData: request.enrichData,
              forceRefresh: Boolean(request.forceRefresh || forceRefresh),
            };

            const result = await this.collectRace(collectionRequest, {
              ...options,
              useCache,
              forceRefresh: request.forceRefresh || forceRefresh,
            });

            completed++;
            const progress = Math.min(5 + (completed / raceList.length) * 90, 95);

            onProgress?.({
              operation: `Collecting races (${completed}/${raceList.length})`,
              progress,
              currentRace: race,
              estimatedTimeRemaining: this.estimateTimeRemaining(startTime, completed, raceList.length),
              startTime,
            });

            return {
              date: race.date,
              raceNo: race.raceNo,
              meet: race.meet,
              status: 'success' as const,
              dataSize: JSON.stringify(result).length,
            };
          } catch (error) {
            completed++;
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';

            logger.error('Failed to collect race in batch', {
              race,
              error: errorMessage,
            });

            errors.push(`${race.date} R${race.raceNo} ${race.meet}: ${errorMessage}`);

            return {
              date: race.date,
              raceNo: race.raceNo,
              meet: race.meet,
              status: 'failed' as const,
              error: errorMessage,
            };
          }
        });

        const batchResults = await Promise.allSettled(batchPromises);
        batchResults.forEach((result) => {
          if (result.status === 'fulfilled') {
            results.push(result.value);
          }
        });
      }

      // Step 3: Final statistics
      const duration = Date.now() - startTime;
      const summary = {
        totalRequested: raceList.length,
        totalCollected: results.filter((r) => r.status === 'success').length,
        totalFailed: results.filter((r) => r.status === 'failed').length,
        totalSkipped: results.filter((r) => r.status === 'skipped').length,
        duration,
      };

      logger.info('Batch collection completed', summary);

      onProgress?.({
        operation: 'Completed',
        progress: 100,
        startTime,
      });

      return {
        summary,
        results,
        errors,
      };
    } catch (error) {
      const duration = Date.now() - startTime;
      logger.error('Batch collection failed', {
        error,
        request,
        duration: `${duration}ms`,
      });

      throw new AppError(
        `Failed to collect batch data: ${error instanceof Error ? error.message : 'Unknown error'}`,
        500,
        true,
        { request, duration }
      );
    }
  }

  /**
   * Collect all races for a specific day
   * @param date Date in YYYY-MM-DD format
   * @param meet Meet identifier (optional)
   * @param enrichData Whether to enrich data
   * @param options Collection options
   * @param onProgress Progress callback
   */
  async collectDay(
    date: string,
    meet?: string,
    enrichData: boolean = false,
    options: CollectionOptions = {},
    onProgress?: ProgressCallback
  ): Promise<CollectedRaceData[]> {
    const startTime = Date.now();
    logger.info('Collecting full day races', { date, meet, enrichData });

    try {
      // Determine race count for the day (typically 1-12 races)
      const raceNumbers = await this.getRaceNumbersForDay(date, meet);
      const results: CollectedRaceData[] = [];

      for (let i = 0; i < raceNumbers.length; i++) {
        const raceNo = raceNumbers[i];
        if (raceNo === undefined) continue;

        const progress = (i / raceNumbers.length) * 100;

        onProgress?.({
          operation: `Collecting race ${i + 1} of ${raceNumbers.length}`,
          progress,
          currentRace: { date, raceNo, meet: meet || '' },
          startTime,
        });

        try {
          const raceData = await this.collectRace(
            {
              date,
              raceNo,
              meet,
              enrichData,
            },
            options
          );

          results.push(raceData);
        } catch (error) {
          logger.warn('Failed to collect race in day collection', {
            date,
            raceNo,
            meet,
            error,
          });
        }
      }

      logger.info('Day collection completed', {
        date,
        meet,
        totalRaces: results.length,
        requestedRaces: raceNumbers.length,
      });

      return results;
    } catch (error) {
      logger.error('Day collection failed', { error, date, meet });
      throw new AppError(
        `Failed to collect day races: ${error instanceof Error ? error.message : 'Unknown error'}`,
        500,
        true,
        { date, meet }
      );
    }
  }

  /**
   * Validate collection request
   * @private
   */
  private validateCollectionRequest(request: CollectionRequest): void {
    const errors: Array<{ field: string; message: string; value?: any }> = [];

    if (!request.date) {
      errors.push({ field: 'date', message: 'Date is required' });
    } else if (!/^\d{8}$/.test(request.date)) {
      errors.push({
        field: 'date',
        message: 'Date must be in YYYYMMDD format',
        value: request.date,
      });
    }

    if (request.raceNo !== undefined && (request.raceNo < 1 || request.raceNo > 12)) {
      errors.push({
        field: 'raceNo',
        message: 'Race number must be between 1 and 12',
        value: request.raceNo,
      });
    }

    if (errors.length > 0) {
      throw new ValidationError('Invalid collection request', errors);
    }
  }

  /**
   * Validate batch collection request
   * @private
   */
  private validateBatchCollectionRequest(request: BatchCollectionRequest): void {
    const errors: Array<{ field: string; message: string; value?: any }> = [];

    if (!request.startDate) {
      errors.push({ field: 'startDate', message: 'Start date is required' });
    } else if (!/^\d{8}$/.test(request.startDate)) {
      errors.push({
        field: 'startDate',
        message: 'Start date must be in YYYYMMDD format',
        value: request.startDate,
      });
    }

    if (!request.endDate) {
      errors.push({ field: 'endDate', message: 'End date is required' });
    } else if (!/^\d{8}$/.test(request.endDate)) {
      errors.push({
        field: 'endDate',
        message: 'End date must be in YYYYMMDD format',
        value: request.endDate,
      });
    }

    if (request.startDate && request.endDate && request.startDate > request.endDate) {
      errors.push({
        field: 'dateRange',
        message: 'Start date must be before or equal to end date',
      });
    }

    if (request.concurrency && (request.concurrency < 1 || request.concurrency > 10)) {
      errors.push({
        field: 'concurrency',
        message: 'Concurrency must be between 1 and 10',
        value: request.concurrency,
      });
    }

    if (errors.length > 0) {
      throw new ValidationError('Invalid batch collection request', errors);
    }
  }

  /**
   * Generate list of races to collect for batch operation
   * @private
   */
  private async generateRaceList(request: BatchCollectionRequest): Promise<
    Array<{
      date: string;
      raceNo: number;
      meet: string;
    }>
  > {
    const races: Array<{ date: string; raceNo: number; meet: string }> = [];
    // Parse YYYYMMDD format dates
    const year = parseInt(request.startDate.substring(0, 4), 10);
    const month = parseInt(request.startDate.substring(4, 6), 10) - 1;
    const day = parseInt(request.startDate.substring(6, 8), 10);
    const startDate = new Date(year, month, day);
    
    const endYear = parseInt(request.endDate.substring(0, 4), 10);
    const endMonth = parseInt(request.endDate.substring(4, 6), 10) - 1;
    const endDay = parseInt(request.endDate.substring(6, 8), 10);
    const endDate = new Date(endYear, endMonth, endDay);
    
    const meets: string[] = (request.meets ?? ['서울', '부산경남', '제주']).filter(
      (m): m is string => typeof m === 'string' && m.length > 0
    );

    // Generate date range
    for (let date = new Date(startDate); date <= endDate; date.setDate(date.getDate() + 1)) {
      // Format as YYYYMMDD
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const dateStr: string = `${year}${month}${day}`;

      for (let i = 0; i < meets.length; i++) {
        const meetName = meets[i];
        if (!meetName) continue;

        // Get race numbers for this day and meet
        const raceNumbers = await this.getRaceNumbersForDay(dateStr, meetName as string);

        for (const raceNo of raceNumbers) {
          if (raceNo !== undefined) {
            races.push({ date: dateStr, raceNo, meet: meetName as string });
          }
        }
      }
    }

    return races;
  }

  /**
   * Get available race numbers for a specific day and meet
   * @private
   */
  private async getRaceNumbersForDay(_date: string, _meet?: string): Promise<number[]> {
    // For now, return typical race numbers (1-12)
    // In a real implementation, this could call an API to get actual race schedule
    return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
  }

  /**
   * Estimate time remaining for batch operation
   * @private
   */
  private estimateTimeRemaining(startTime: number, completed: number, total: number): number {
    if (completed === 0) return 0;

    const elapsed = Date.now() - startTime;
    const averageTimePerItem = elapsed / completed;
    const remaining = total - completed;

    return Math.round(remaining * averageTimePerItem);
  }
}
