/**
 * Trainer Controller
 *
 * Handles trainer-related API endpoints including trainer details and statistics
 */

import type { Request, Response, NextFunction } from 'express';
import { services } from '../services/index.js';
import type { ApiResponse, TrainerQueryParams } from '../types/api.types.js';
import type { Api19_1Item } from '../types/kra-api.types.js';
import { AppError } from '../types/index.js';
import logger from '../utils/logger.js';
import { handleNotImplemented, validateRequest } from './utils/controllerUtils.js';

/**
 * Enhanced trainer data with additional metadata
 */
interface TrainerDetails extends Api19_1Item {
  /** Additional metadata */
  metadata?: {
    lastUpdated: string;
    dataSource: 'api' | 'cache';
    cacheExpiresAt?: string;
  };
}

/**
 * Trainer performance statistics
 */
interface TrainerStats {
  /** Basic information */
  trNo: string;
  trName: string;

  /** Performance metrics */
  totalRaces: number;
  totalHorses: number;
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

  /** Horse development metrics */
  avgHorseCareerLength: number;
  horsesImproved: number;
  improvementRate: number;

  /** Recent form (last 30 days) */
  recentForm: {
    races: number;
    wins: number;
    places: number;
    shows: number;
    winRate: number;
    period: string;
  };

  /** Track-specific performance */
  trackStats?: {
    meet: string;
    races: number;
    wins: number;
    winRate: number;
    specialization: string;
  }[];

  /** Horse grade specialization */
  gradeStats?: {
    grade: string;
    races: number;
    wins: number;
    winRate: number;
  }[];

  /** Distance specialization */
  distanceStats?: {
    distance: string;
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

export class TrainerController {
  /**
   * Get trainer details by trainer number
   * GET /api/trainers/:trNo
   */
  getTrainerDetails = async (
    req: Request<{ trNo: string }, ApiResponse<TrainerDetails>, Record<string, never>, TrainerQueryParams>,
    res: Response<ApiResponse<TrainerDetails>>,
    next: NextFunction
  ): Promise<void> => {
    try {
      validateRequest(req);

      const { trNo } = req.params;
      const { meet } = req.query;

      logger.info('Getting trainer details', { trNo, meet });

      // Check cache first
      const cacheKeyParams = { trNo, meet: meet || 'all' };
      let trainerData = await services.cacheService.get('trainer_detail', cacheKeyParams);

      if (!trainerData) {
        // Fetch from KRA API if not in cache
        logger.info('Trainer data not in cache, fetching from API', { trNo, meet });

        try {
          trainerData = await services.kraApiService.getTrainerDetail(trNo);

          if (!trainerData) {
            throw new AppError('Trainer not found', 404, true, { trNo, meet });
          }

          // Cache the result for 8 hours (trainer data changes infrequently)
          await services.cacheService.set('trainer_detail', cacheKeyParams, trainerData, { ttl: 28800 });

          // Add metadata
          (trainerData as TrainerDetails).metadata = {
            lastUpdated: new Date().toISOString(),
            dataSource: 'api',
          };
        } catch (error) {
          logger.error('Failed to fetch trainer data from API', { trNo, meet, error });
          throw error;
        }
      } else {
        // Add cache metadata
        (trainerData as TrainerDetails).metadata = {
          lastUpdated: new Date().toISOString(),
          dataSource: 'cache',
          cacheExpiresAt: new Date(Date.now() + 28800 * 1000).toISOString(),
        };
      }

      res.json({
        success: true,
        data: trainerData as TrainerDetails,
        message: 'Trainer details retrieved successfully',
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
   * Get trainer performance statistics
   * GET /api/trainers/:trNo/stats
   */
  getTrainerStats = async (
    req: Request<{ trNo: string }, ApiResponse<TrainerStats>, Record<string, never>, TrainerQueryParams>,
    res: Response<ApiResponse<TrainerStats>>,
    next: NextFunction
  ): Promise<void> => {
    const { trNo } = req.params;
    const { meet, minWinRate, sortBy = 'winRate', sortOrder = 'desc' } = req.query;
    handleNotImplemented(req, res, next, {
      logMessage: 'Getting trainer statistics',
      logContext: { trNo, meet, minWinRate, sortBy, sortOrder },
      clientMessage: 'Trainer statistics endpoint is not implemented',
      details: 'Statistics aggregation from trainer race history is pending implementation.',
    });
  };

  /**
   * Search trainers by name or other criteria
   * GET /api/trainers (with query parameters)
   */
  searchTrainers = async (
    req: Request<Record<string, never>, ApiResponse<TrainerDetails[]>, Record<string, never>, TrainerQueryParams>,
    res: Response<ApiResponse<TrainerDetails[]>>,
    next: NextFunction
  ): Promise<void> => {
    const { trName, meet, minWinRate, page = 1, pageSize = 20, sortBy = 'trName', sortOrder = 'asc' } = req.query;
    handleNotImplemented(req, res, next, {
      logMessage: 'Searching trainers',
      logContext: { trName, meet, minWinRate, page, pageSize, sortBy, sortOrder },
      clientMessage: 'Trainer search endpoint is not implemented',
      details: 'Search, filtering, and pagination queries are pending implementation.',
    });
  };

  /**
   * Get top performing trainers
   * GET /api/trainers/top (with query parameters for criteria)
   */
  getTopTrainers = async (
    req: Request<
      Record<string, never>,
      ApiResponse<(TrainerDetails & { stats: Partial<TrainerStats> })[]>,
      Record<string, never>,
      TrainerQueryParams
    >,
    res: Response<ApiResponse<(TrainerDetails & { stats: Partial<TrainerStats> })[]>>,
    next: NextFunction
  ): Promise<void> => {
    const { meet, minWinRate, page = 1, pageSize = 10, sortBy = 'winRate', sortOrder = 'desc' } = req.query;
    handleNotImplemented(req, res, next, {
      logMessage: 'Getting top trainers',
      logContext: { meet, minWinRate, page, pageSize, sortBy, sortOrder },
      clientMessage: 'Top trainers endpoint is not implemented',
      details: 'Ranking and scoring logic for trainer leaderboard is pending.',
    });
  };

  /**
   * Get trainer specialization analysis
   * GET /api/trainers/:trNo/specialization
   */
  getTrainerSpecialization = async (
    req: Request<{ trNo: string }, ApiResponse<any>, Record<string, never>, TrainerQueryParams>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    const { trNo } = req.params;
    handleNotImplemented(req, res, next, {
      logMessage: 'Getting trainer specialization analysis',
      logContext: { trNo },
      clientMessage: 'Trainer specialization endpoint is not implemented',
      details: 'Specialization analytics pipeline is pending implementation.',
    });
  };
  // (removed duplicate lighter stub of getTrainerStats)

  // (removed duplicate lighter stub of getTrainerSpecialization)

  /**
   * Get trainer performance
   * GET /api/trainers/:trNo/performance
   */
  getTrainerPerformance = async (
    req: Request<{ trNo: string }, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    const { trNo } = req.params;
    handleNotImplemented(req, res, next, {
      logMessage: 'Getting trainer performance',
      logContext: { trNo },
      clientMessage: 'Trainer performance endpoint is not implemented',
      details: 'Performance time-series analytics are pending implementation.',
      validate: false,
    });
  };

  /**
   * Get trainer horses
   * GET /api/trainers/:trNo/horses
   */
  getTrainerHorses = async (
    req: Request<{ trNo: string }, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    const { trNo } = req.params;
    handleNotImplemented(req, res, next, {
      logMessage: 'Getting trainer horses',
      logContext: { trNo },
      clientMessage: 'Trainer horses endpoint is not implemented',
      details: 'Horse list by trainer endpoint is pending implementation.',
      validate: false,
    });
  };

  // (removed duplicate lighter stub of searchTrainers)

  // (removed duplicate lighter stub of getTopTrainers)

  /**
   * Get trainer rankings
   * GET /api/trainers/rankings
   */
  getTrainerRankings = async (
    req: Request<Record<string, never>, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    handleNotImplemented(req, res, next, {
      logMessage: 'Getting trainer rankings',
      clientMessage: 'Trainer rankings endpoint is not implemented',
      details: 'Current ranking calculation has not been implemented.',
      validate: false,
    });
  };

  /**
   * Get trainer stats summary
   * GET /api/trainers/stats/summary
   */
  getTrainerStatsSummary = async (
    req: Request<Record<string, never>, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    handleNotImplemented(req, res, next, {
      logMessage: 'Getting trainer stats summary',
      clientMessage: 'Trainer stats summary endpoint is not implemented',
      details: 'Summary aggregation for trainer statistics is pending.',
      validate: false,
    });
  };

  /**
   * Get specializations
   * GET /api/trainers/specializations
   */
  getSpecializations = async (
    req: Request<Record<string, never>, ApiResponse<any>>,
    res: Response<ApiResponse<any>>,
    next: NextFunction
  ): Promise<void> => {
    handleNotImplemented(req, res, next, {
      logMessage: 'Getting specializations',
      clientMessage: 'Trainer specializations endpoint is not implemented',
      details: 'Specialization category index is pending implementation.',
      validate: false,
    });
  };
}

// Export singleton instance
export const trainerController = new TrainerController();
