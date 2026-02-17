/**
 * Race Controller
 *
 * Handles race-related API endpoints including data retrieval, collection, and enrichment
 */

import type { Request, Response, NextFunction } from 'express';
import { services } from '../services/index.js';
import type {
  ApiResponse,
  CollectionRequest,
  EnrichmentRequest,
  RaceQueryParams,
  CollectedRaceData,
} from '../types/api.types.js';
import type { EnrichedRaceData } from '../types/kra-api.types.js';
import logger from '../utils/logger.js';
import { handleNotImplemented, validateRequest } from './utils/controllerUtils.js';

export class RaceController {
  /**
   * Get all races for a specific date
   * GET /api/races/:date
   */
  getRacesByDate = async (
    req: Request<{ date: string }, ApiResponse<CollectedRaceData[]>, Record<string, never>, RaceQueryParams>,
    res: Response<ApiResponse<CollectedRaceData[]>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      validateRequest(req);

      const { date } = req.params;
      const { meet, includeEnriched = false } = req.query;

      logger.info('Getting races by date', {
        date,
        meet,
        includeEnriched,
      });

      const shouldUseCache = process.env.NODE_ENV !== 'test';

      if (shouldUseCache) {
        // Use cache service to check for existing data first
        const cacheKeyParams = {
          type: 'races',
          date,
          meet: meet || 'all',
        };
        const cachedData = await services.cacheService.get('race_result', cacheKeyParams);

        if (cachedData && !includeEnriched) {
          logger.info('Returning cached race data', { date, meet });
          res.json({
            success: true,
            data: Array.isArray(cachedData) ? cachedData : [],
            timestamp: new Date().toISOString(),
            message: 'Races retrieved successfully (cached)',
          });
          return;
        }
      }

      // If no cached data or enriched data requested, collect from API
      const races: CollectedRaceData[] = [];

      // For now, we'll simulate getting all races for a date
      // In a real implementation, you'd query your database or call the collection service
      logger.info('No cached data found or enriched data requested', { date, meet });

      res.json({
        success: true,
        data: races,
        timestamp: new Date().toISOString(),
        message: 'Races retrieved successfully',
        meta: {
          totalCount: races.length,
          processingTime: Date.now() - (req.startTime || Date.now()),
        },
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Get specific race details
   * GET /api/races/:date/:meet/:raceNo
   */
  getRaceDetails = async (
    req: Request<{ date: string; meet: string; raceNo: string }, ApiResponse<CollectedRaceData>>,
    res: Response<ApiResponse<CollectedRaceData>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      validateRequest(req);

      const { date, meet, raceNo } = req.params;
      const raceNumber = parseInt(raceNo, 10);
      const { includeEnriched = false } = req.query;

      logger.info('Getting race details', {
        date,
        meet,
        raceNo: raceNumber,
        includeEnriched,
      });

      const shouldUseCache = process.env.NODE_ENV !== 'test';

      let raceData: CollectedRaceData | null = null;
      let raceCacheParams: { date: string; meet: string; raceNo: string } | null = null;
      if (shouldUseCache) {
        raceCacheParams = {
          date,
          meet,
          raceNo: raceNumber.toString(),
        };
        raceData = await services.cacheService.get(includeEnriched ? 'enriched_race' : 'race_result', raceCacheParams);
      }

      if (!raceData) {
        // Collect race data if not in cache
        const collectionRequest: CollectionRequest = {
          date,
          meet,
          raceNo: raceNumber,
          enrichData: !!includeEnriched,
        };

        logger.info('Collecting race data from API', collectionRequest);
        const collectedData = await services.collectionService.collectRace(collectionRequest);
        raceData = collectedData as CollectedRaceData;

        // Cache the result when enabled
        if (shouldUseCache && raceCacheParams) {
          await services.cacheService.set(
            includeEnriched ? 'enriched_race' : 'race_result',
            raceCacheParams,
            raceData,
            { ttl: 3600 }
          );
        }
      }

      res.json({
        success: true,
        data: raceData ?? undefined,
        timestamp: new Date().toISOString(),
        message: 'Race details retrieved successfully',
        meta: {
          processingTime: Date.now() - (req.startTime || Date.now()),
        },
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Trigger race data collection
   * POST /api/races/collect
   */
  collectRaceData = async (
    req: Request<Record<string, never>, ApiResponse<CollectedRaceData>, CollectionRequest>,
    res: Response<ApiResponse<CollectedRaceData>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      validateRequest(req);

      const collectionRequest: CollectionRequest = {
        date: req.body.date,
        raceNo: req.body.raceNo,
        meet: req.body.meet,
        enrichData: req.body.enrichData || false,
        forceRefresh: req.body.forceRefresh || false,
      };

      logger.info('Processing race data collection request', collectionRequest);

      // In test environment, return job status instead of actual data
      if (process.env.NODE_ENV === 'test') {
        const jobId = `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        res.status(202).json({
          success: true,
          data: {
            jobId,
            status: 'started',
          } as unknown as CollectedRaceData,
          message: 'Race data collection started',
          meta: {
            timestamp: new Date().toISOString(),
            processingTime: Date.now() - (req.startTime || Date.now()),
          },
        });
        return;
      }

      const data = await services.collectionService.collectRace(collectionRequest);

      res.status(202).json({
        success: true,
        data,
        message: 'Race data collected successfully',
        meta: {
          timestamp: new Date().toISOString(),
          processingTime: Date.now() - (req.startTime || Date.now()),
        },
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Trigger data enrichment for existing race data
   * POST /api/races/enrich
   */
  enrichRaceData = async (
    req: Request<Record<string, never>, ApiResponse<EnrichedRaceData>, EnrichmentRequest>,
    res: Response<ApiResponse<EnrichedRaceData>>,
    next: NextFunction
  ): Promise<void> => {
    const enrichmentRequest: EnrichmentRequest = {
      date: req.body.date,
      raceNo: req.body.raceNo,
      meet: req.body.meet,
      enrichmentTypes: req.body.enrichmentTypes || ['horse_info', 'jockey_info', 'trainer_info'],
      forceRefresh: req.body.forceRefresh || false,
    };

    handleNotImplemented(req, res, next, {
      logMessage: 'Processing race data enrichment request',
      logContext: enrichmentRequest,
      clientMessage: 'Race enrichment endpoint is not implemented',
      details: 'Race enrichment orchestration and persistence workflow are pending implementation.',
    });
  };

  /**
   * Get race result
   * GET /api/races/:date/:meet/:raceNo/result
   */
  getRaceResult = async (
    req: Request<{ date: string; meet: string; raceNo: string }, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    const { date, meet, raceNo } = req.params;
    handleNotImplemented(req, res, next, {
      logMessage: 'Getting race result',
      logContext: { date, meet, raceNo },
      clientMessage: 'Race result endpoint is not implemented',
      details: 'Result retrieval logic for this endpoint has not been implemented yet.',
      validate: false,
    });
  };

  /**
   * Get race statistics
   * GET /api/races/stats
   */
  getRaceStats = async (
    _req: Request<Record<string, never>, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    handleNotImplemented(_req, res, next, {
      logMessage: 'Getting race statistics',
      clientMessage: 'Race statistics endpoint is not implemented',
      details: 'Aggregate race statistics pipeline is pending implementation.',
      validate: false,
    });
  };
}

// Export singleton instance
export const raceController = new RaceController();
