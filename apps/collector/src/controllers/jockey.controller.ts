/**
 * Jockey Controller
 *
 * Handles jockey-related API endpoints including jockey details and statistics
 */

import type { Request, Response, NextFunction } from 'express';
import { services } from '../services/index.js';
import type { ApiResponse, JockeyQueryParams } from '../types/api.types.js';
import type { Api12_1Item } from '../types/kra-api.types.js';
import { AppError } from '../types/index.js';
import logger from '../utils/logger.js';
import { handleNotImplemented, validateRequest } from './utils/controllerUtils.js';

/**
 * Enhanced jockey data with additional metadata
 */
interface JockeyDetails extends Api12_1Item {
  /** Additional metadata */
  metadata?: {
    lastUpdated: string;
    dataSource: 'api' | 'cache';
    cacheExpiresAt?: string;
  };
}

/**
 * Jockey performance statistics
 */
interface JockeyStats {
  /** Basic information */
  jkNo: string;
  jkName: string;

  /** Performance metrics */
  totalRaces: number;
  wins: number;
  places: number;
  shows: number;

  /** Calculated rates */
  winRate: number;
  placeRate: number;
  showRate: number;

  /** Financial metrics */
  totalPrizeMoney: number;
  avgPrizeMoney: number;

  /** Recent form (last 10 races) */
  recentForm: {
    races: number;
    wins: number;
    places: number;
    shows: number;
    winRate: number;
  };

  /** Track-specific performance */
  trackStats?: {
    meet: string;
    races: number;
    wins: number;
    winRate: number;
  }[];

  /** Period information */
  period: {
    startDate: string;
    endDate: string;
    totalDays: number;
  };

  /** Last updated timestamp */
  lastUpdated: string;
}

export class JockeyController {
  /**
   * Get jockey details by jockey number
   * GET /api/jockeys/:jkNo
   */
  getJockeyDetails = async (
    req: Request<{ jkNo: string }, ApiResponse<JockeyDetails>, Record<string, never>, JockeyQueryParams>,
    res: Response<ApiResponse<JockeyDetails>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      validateRequest(req);

      const { jkNo } = req.params;
      const { meet } = req.query;

      logger.info('Getting jockey details', { jkNo, meet });

      // Check cache first
      const cacheKeyParams = { jkNo, meet: meet || 'all' };
      let jockeyData = await services.cacheService.get('jockey_detail', cacheKeyParams);

      if (!jockeyData) {
        // Fetch from KRA API if not in cache
        logger.info('Jockey data not in cache, fetching from API', { jkNo, meet });

        try {
          jockeyData = await services.kraApiService.getJockeyDetail(jkNo);

          if (!jockeyData) {
            throw new AppError('Jockey not found', 404, true, { jkNo, meet });
          }

          // Cache the result for 6 hours (jockey data doesn't change frequently)
          await services.cacheService.set('jockey_detail', cacheKeyParams, jockeyData, { ttl: 21600 });

          // Add metadata
          (jockeyData as JockeyDetails).metadata = {
            lastUpdated: new Date().toISOString(),
            dataSource: 'api',
          };
        } catch (error) {
          logger.error('Failed to fetch jockey data from API', { jkNo, meet, error });
          throw error;
        }
      } else {
        // Add cache metadata
        (jockeyData as JockeyDetails).metadata = {
          lastUpdated: new Date().toISOString(),
          dataSource: 'cache',
          cacheExpiresAt: new Date(Date.now() + 21600 * 1000).toISOString(),
        };
      }

      res.json({
        success: true,
        data: jockeyData as JockeyDetails,
        message: 'Jockey details retrieved successfully',
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
   * Get jockey performance statistics
   * GET /api/jockeys/:jkNo/stats
   */
  getJockeyStats = async (
    req: Request<{ jkNo: string }, ApiResponse<JockeyStats>, Record<string, never>, JockeyQueryParams>,
    res: Response<ApiResponse<JockeyStats>>,
    next: NextFunction
  ): Promise<void> => {
    const { jkNo } = req.params;
    const { meet, sortBy = 'winRate', sortOrder = 'desc' } = req.query;
    handleNotImplemented(req, res, next, {
      logMessage: 'Getting jockey statistics',
      logContext: {
        jkNo,
        meet,
        sortBy,
        sortOrder,
      },
      clientMessage: 'Jockey statistics endpoint is not implemented',
      details: 'Statistics aggregation from race history is pending implementation.',
    });
  };

  /**
   * Search jockeys by name or other criteria
   * GET /api/jockeys (with query parameters)
   */
  searchJockeys = async (
    req: Request<Record<string, never>, ApiResponse<JockeyDetails[]>, Record<string, never>, JockeyQueryParams>,
    res: Response<ApiResponse<JockeyDetails[]>>,
    next: NextFunction
  ): Promise<void> => {
    const { jkName, meet, part, page = 1, pageSize = 20, sortBy = 'jkName', sortOrder = 'asc' } = req.query;
    handleNotImplemented(req, res, next, {
      logMessage: 'Searching jockeys',
      logContext: {
        jkName,
        meet,
        part,
        page,
        pageSize,
        sortBy,
        sortOrder,
      },
      clientMessage: 'Jockey search endpoint is not implemented',
      details: 'Search, filtering, and pagination queries are pending implementation.',
    });
  };

  /**
   * Get top performing jockeys
   * GET /api/jockeys/top (with query parameters for criteria)
   */
  getTopJockeys = async (
    req: Request<
      Record<string, never>,
      ApiResponse<(JockeyDetails & { stats: Partial<JockeyStats> })[]>,
      Record<string, never>,
      JockeyQueryParams
    >,
    res: Response<ApiResponse<(JockeyDetails & { stats: Partial<JockeyStats> })[]>>,
    next: NextFunction
  ): Promise<void> => {
    const { meet, page = 1, pageSize = 10, sortBy = 'winRate', sortOrder = 'desc' } = req.query;
    handleNotImplemented(req, res, next, {
      logMessage: 'Getting top jockeys',
      logContext: {
        meet,
        page,
        pageSize,
        sortBy,
        sortOrder,
      },
      clientMessage: 'Top jockeys endpoint is not implemented',
      details: 'Ranking and scoring logic for jockey leaderboard is pending.',
    });
  };

  // (removed duplicate lighter stub of getJockeyStats)

  /**
   * Get jockey performance
   * GET /api/jockeys/:jkNo/performance
   */
  getJockeyPerformance = async (
    req: Request<{ jkNo: string }, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    const { jkNo } = req.params;
    handleNotImplemented(req, res, next, {
      logMessage: 'Getting jockey performance',
      logContext: { jkNo },
      clientMessage: 'Jockey performance endpoint is not implemented',
      details: 'Performance time-series analytics are pending implementation.',
      validate: false,
    });
  };

  /**
   * Get jockey races
   * GET /api/jockeys/:jkNo/races
   */
  getJockeyRaces = async (
    req: Request<{ jkNo: string }, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    const { jkNo } = req.params;
    handleNotImplemented(req, res, next, {
      logMessage: 'Getting jockey races',
      logContext: { jkNo },
      clientMessage: 'Jockey races endpoint is not implemented',
      details: 'Historical race listing by jockey is pending implementation.',
      validate: false,
    });
  };

  // (removed duplicate lighter stub of searchJockeys)

  // (removed duplicate lighter stub of getTopJockeys)

  /**
   * Get jockey rankings
   * GET /api/jockeys/rankings
   */
  getJockeyRankings = async (
    req: Request<Record<string, never>, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    handleNotImplemented(req, res, next, {
      logMessage: 'Getting jockey rankings',
      clientMessage: 'Jockey rankings endpoint is not implemented',
      details: 'Current ranking calculation has not been implemented.',
      validate: false,
    });
  };

  /**
   * Get jockey stats summary
   * GET /api/jockeys/stats/summary
   */
  getJockeyStatsSummary = async (
    req: Request<Record<string, never>, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    handleNotImplemented(req, res, next, {
      logMessage: 'Getting jockey stats summary',
      clientMessage: 'Jockey stats summary endpoint is not implemented',
      details: 'Summary aggregation for jockey statistics is pending.',
      validate: false,
    });
  };
}

// Export singleton instance
export const jockeyController = new JockeyController();
