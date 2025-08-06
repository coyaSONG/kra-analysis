/**
 * Race Controller
 * 
 * Handles race-related API endpoints including data retrieval, collection, and enrichment
 */

import type { Request, Response, NextFunction } from 'express';
import { validationResult } from 'express-validator';
import { services } from '../services/index.js';
import type { 
  ApiResponse, 
  CollectionRequest, 
  EnrichmentRequest,
  RaceQueryParams,
  PaginatedResponse,
  CollectedRaceData
} from '../types/api.types.js';
import type { EnrichedRaceData } from '../types/kra-api.types.js';
import { ValidationError } from '../types/index.js';
import logger from '../utils/logger.js';

export class RaceController {
  /**
   * Get all races for a specific date
   * GET /api/races/:date
   */
  getRacesByDate = async (
    req: Request<{ date: string }, ApiResponse<CollectedRaceData[]>, {}, RaceQueryParams>,
    res: Response<ApiResponse<CollectedRaceData[]>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      // Validate request parameters
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        throw new ValidationError(`Validation failed: ${errors.array().map(err => err.msg).join(', ')}`);
      }

      const { date } = req.params;
      const { meet, includeEnriched = false } = req.query;

      logger.info('Getting races by date', { 
        date, 
        meet, 
        includeEnriched 
      });

      // Use cache service to check for existing data first
      const cacheKeyParams = { 
        type: 'races',
        date, 
        meet: meet || 'all' 
      };
      const cachedData = await services.cacheService.get('race_result', cacheKeyParams);

      if (cachedData && !includeEnriched) {
        logger.info('Returning cached race data', { date, meet });
        res.json({
          success: true,
          data: Array.isArray(cachedData) ? cachedData : [],
          message: 'Races retrieved successfully (cached)'
        });
        return;
      }

      // If no cached data or enriched data requested, collect from API
      const races: CollectedRaceData[] = [];
      
      // For now, we'll simulate getting all races for a date
      // In a real implementation, you'd query your database or call the collection service
      logger.info('No cached data found or enriched data requested', { date, meet });

      res.json({
        success: true,
        data: races,
        message: 'Races retrieved successfully',
        meta: {
          totalCount: races.length,
          timestamp: new Date().toISOString(),
          processingTime: Date.now() - (req.startTime || Date.now())
        }
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
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        throw new ValidationError(`Validation failed: ${errors.array().map(err => err.msg).join(', ')}`);
      }

      const { date, meet, raceNo } = req.params;
      const raceNumber = parseInt(raceNo, 10);
      const { includeEnriched = false } = req.query;

      logger.info('Getting race details', { 
        date, 
        meet, 
        raceNo: raceNumber,
        includeEnriched 
      });

      // Check cache first
      const raceCacheParams = { 
        date, 
        meet, 
        raceNo: raceNumber.toString() 
      };
      let raceData = await services.cacheService.get(
        includeEnriched ? 'enriched_race' : 'race_result', 
        raceCacheParams
      );

      if (!raceData) {
        // Collect race data if not in cache
        const collectionRequest: CollectionRequest = {
          date,
          meet,
          raceNo: raceNumber,
          enrichData: !!includeEnriched
        };

        logger.info('Collecting race data from API', collectionRequest);
        const collectedData = await services.collectionService.collectRace(collectionRequest);
        raceData = collectedData as CollectedRaceData;

        // Cache the result
        await services.cacheService.set(
          includeEnriched ? 'enriched_race' : 'race_result',
          raceCacheParams,
          raceData,
          { ttl: 3600 } // 1 hour cache
        );
      }

      res.json({
        success: true,
        data: raceData as CollectedRaceData | undefined,
        message: 'Race details retrieved successfully',
        meta: {
          timestamp: new Date().toISOString(),
          processingTime: Date.now() - (req.startTime || Date.now())
        }
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
    req: Request<{}, ApiResponse<CollectedRaceData>, CollectionRequest>,
    res: Response<ApiResponse<CollectedRaceData>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        throw new ValidationError(`Validation failed: ${errors.array().map(err => err.msg).join(', ')}`);
      }

      const collectionRequest: CollectionRequest = {
        date: req.body.date,
        raceNo: req.body.raceNo,
        meet: req.body.meet,
        enrichData: req.body.enrichData || false,
        forceRefresh: req.body.forceRefresh || false
      };

      logger.info('Processing race data collection request', collectionRequest);

      const data = await services.collectionService.collectRace(collectionRequest);

      res.json({
        success: true,
        data,
        message: 'Race data collected successfully',
        meta: {
          timestamp: new Date().toISOString(),
          processingTime: Date.now() - (req.startTime || Date.now())
        }
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
    req: Request<{}, ApiResponse<EnrichedRaceData>, EnrichmentRequest>,
    res: Response<ApiResponse<EnrichedRaceData>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        throw new ValidationError(`Validation failed: ${errors.array().map(err => err.msg).join(', ')}`);
      }

      const enrichmentRequest: EnrichmentRequest = {
        date: req.body.date,
        raceNo: req.body.raceNo,
        meet: req.body.meet,
        enrichmentTypes: req.body.enrichmentTypes || ['horse_info', 'jockey_info', 'trainer_info'],
        forceRefresh: req.body.forceRefresh || false
      };

      logger.info('Processing race data enrichment request', enrichmentRequest);

      // First get the race data, then enrich it
      // This is a simplified implementation - in practice you'd get the race data first
      // For now, return a mock response indicating the feature is not fully implemented
      const data: EnrichedRaceData = {
        raceInfo: {
          date: enrichmentRequest.date,
          meet: enrichmentRequest.meet,
          raceNo: enrichmentRequest.raceNo,
          rcName: '',
          rcDist: 0,
          track: '',
          weather: ''
        },
        horses: []
      };

      res.json({
        success: true,
        data,
        message: 'Race data enriched successfully',
        meta: {
          timestamp: new Date().toISOString(),
          processingTime: Date.now() - (req.startTime || Date.now())
        }
      });

    } catch (error) {
      next(error);
    }
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
    try {
      const { date, meet, raceNo } = req.params;
      
      logger.info('Getting race result', { date, meet, raceNo });

      // TODO: Implement actual race result retrieval
      res.json({
        success: true,
        data: {
          date,
          meet,
          raceNo,
          message: 'Race result endpoint - to be implemented'
        },
        message: 'Race result retrieved successfully'
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Get race statistics
   * GET /api/races/stats
   */
  getRaceStats = async (
    req: Request<{}, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      logger.info('Getting race statistics');

      // TODO: Implement actual race statistics
      res.json({
        success: true,
        data: {
          totalRaces: 0,
          message: 'Race statistics endpoint - to be implemented'
        },
        message: 'Race statistics retrieved successfully'
      });
    } catch (error) {
      next(error);
    }
  };
}

// Export singleton instance
export const raceController = new RaceController();