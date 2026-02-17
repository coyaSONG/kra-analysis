/**
 * KRA API Service
 *
 * Core service for interacting with Korea Racing Authority (KRA) Public APIs
 * Implements retry logic, rate limiting, and comprehensive error handling
 */

import type {
  Api214Response,
  Api8_2Response,
  Api12_1Response,
  Api19_1Response,
  Api214Item,
  Api8_2Item,
  Api12_1Item,
  Api19_1Item,
  Api299Response,
  Api299Item,
} from '../types/kra-api.types.js';
import { KraApiEndpoint, KraMeet } from '../types/kra-api.types.js';
import { ExternalApiError, RateLimitError } from '../types/index.js';
import { appConfig } from '../config/index.js';
import logger from '../utils/logger.js';

/**
 * Request options for KRA API calls
 */
interface KraApiRequestOptions {
  /** Request timeout in milliseconds */
  timeout?: number;
  /** Number of retry attempts */
  retryAttempts?: number;
  /** Delay between retries in milliseconds */
  retryDelay?: number;
  /** Additional headers */
  headers?: Record<string, string>;
}

/**
 * Rate limiting configuration
 */
interface RateLimitConfig {
  /** Maximum requests per time window */
  maxRequests: number;
  /** Time window in milliseconds */
  windowMs: number;
  /** Current request count */
  currentRequests: number;
  /** Window start time */
  windowStart: number;
}

/**
 * Retry configuration
 */
interface RetryConfig {
  attempts: number;
  delay: number;
  backoffFactor: number;
}

export class KraApiService {
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly defaultTimeout: number;
  private readonly retryConfig: RetryConfig;
  private readonly rateLimitConfig: RateLimitConfig;

  constructor() {
    this.baseUrl = appConfig.kra.baseUrl;
    this.apiKey = appConfig.kra.apiKey;
    this.defaultTimeout = appConfig.kra.timeout || 30000; // 30 seconds default

    this.retryConfig = {
      attempts: appConfig.kra.retry?.attempts || 3,
      delay: appConfig.kra.retry?.delay || 1000,
      backoffFactor: appConfig.kra.retry?.backoffFactor || 2,
    };

    this.rateLimitConfig = {
      maxRequests: appConfig.kra.rateLimit?.maxRequests || 60,
      windowMs: appConfig.kra.rateLimit?.windowMs || 60000, // 1 minute
      currentRequests: 0,
      windowStart: Date.now(),
    };

    logger.info('KRA API Service initialized', {
      baseUrl: this.baseUrl,
      hasApiKey: Boolean(this.apiKey),
      timeout: this.defaultTimeout,
      rateLimit: {
        maxRequests: this.rateLimitConfig.maxRequests,
        windowMs: this.rateLimitConfig.windowMs,
      },
    });
  }

  /**
   * Fetch race result data from API214_1
   * @param date Race date in YYYYMMDD format
   * @param meet Meet identifier (서울, 부산경남, 제주)
   * @param raceNo Race number
   * @param options Request options
   */
  async getRaceResult(
    date: string,
    meet: string,
    raceNo: number,
    options: KraApiRequestOptions = {}
  ): Promise<Api214Item[]> {
    const endpoint = KraApiEndpoint.RACE_RESULT;
    const params = {
      rc_date: date,
      meet: meet,
      rc_no: raceNo.toString(),
    };

    logger.info('Fetching race result', { date, meet, raceNo, endpoint });

    try {
      const response = await this.fetchWithRetry<Api214Response>(endpoint, params, options);

      if (!response.response || response.response.header.resultCode !== '00') {
        throw new ExternalApiError(
          `KRA API returned error: ${response.response?.header?.resultMsg || 'Unknown error'}`,
          'KRA_API',
          502,
          endpoint,
          response.response?.header?.resultCode,
          response.response?.header?.resultMsg
        );
      }

      const items = response.response.body.items.item;
      const raceData = Array.isArray(items) ? items : [items];

      logger.info('Race result fetched successfully', {
        date,
        meet,
        raceNo,
        horseCount: raceData.length,
      });

      return raceData;
    } catch (error) {
      logger.error('Failed to fetch race result', { error, date, meet, raceNo });

      if (error instanceof ExternalApiError || error instanceof RateLimitError) {
        throw error;
      }

      throw new ExternalApiError(
        `Failed to fetch race result: ${error instanceof Error ? error.message : 'Unknown error'}`,
        'KRA_API',
        502,
        endpoint
      );
    }
  }

  /**
   * Fetch horse detail information from API8_2
   * @param hrNo Horse number
   * @param options Request options
   */
  async getHorseDetail(hrNo: string, options: KraApiRequestOptions = {}): Promise<Api8_2Item | null> {
    const endpoint = KraApiEndpoint.HORSE_INFO;
    const params = { hr_no: hrNo };

    logger.debug('Fetching horse detail', { hrNo, endpoint });

    try {
      const response = await this.fetchWithRetry<Api8_2Response>(endpoint, params, options);

      if (!response.response || response.response.header.resultCode !== '00') {
        // For horse details, return null if not found rather than throwing
        if (response.response?.header?.resultCode === '03') {
          logger.debug('Horse not found', { hrNo });
          return null;
        }

        throw new ExternalApiError(
          `KRA API returned error: ${response.response?.header?.resultMsg || 'Unknown error'}`,
          'KRA_API',
          502,
          endpoint,
          response.response?.header?.resultCode,
          response.response?.header?.resultMsg
        );
      }

      const items = response.response.body.items.item;
      const horseData = Array.isArray(items) ? items[0] : items;

      logger.debug('Horse detail fetched successfully', { hrNo, horseName: horseData?.hrName });

      return horseData || null;
    } catch (error) {
      logger.error('Failed to fetch horse detail', { error, hrNo });

      if (error instanceof ExternalApiError || error instanceof RateLimitError) {
        throw error;
      }

      throw new ExternalApiError(
        `Failed to fetch horse detail: ${error instanceof Error ? error.message : 'Unknown error'}`,
        'KRA_API',
        502,
        endpoint
      );
    }
  }

  /**
   * Fetch race totals/statistics from API299
   * @param date Race date (YYYYMMDD)
   * @param meet Meet code or name (e.g., '1' or '서울')
   * @param options Request options
   */
  async getRaceTotals(date: string, meet?: string, options: KraApiRequestOptions = {}): Promise<Api299Item[]> {
    const endpoint = KraApiEndpoint.RACE_TOTALS;
    const params: Record<string, string> = {
      rc_date: date,
      pageNo: '1',
      numOfRows: '100',
    };
    if (meet) params.meet = meet;

    logger.info('Fetching race totals (API299)', { date, meet, endpoint });

    try {
      const response = await this.fetchWithRetry<Api299Response>(endpoint, params, options);

      if (!response.response || response.response.header.resultCode !== '00') {
        throw new ExternalApiError(
          `KRA API returned error: ${response.response?.header?.resultMsg || 'Unknown error'}`,
          'KRA_API',
          502,
          endpoint,
          response.response?.header?.resultCode,
          response.response?.header?.resultMsg
        );
      }

      const items = response.response.body.items.item;
      const data = Array.isArray(items) ? items : items ? [items] : [];

      logger.info('Race totals fetched successfully', {
        date,
        meet,
        count: data.length,
      });

      return data as Api299Item[];
    } catch (error) {
      logger.error('Failed to fetch race totals', { error, date, meet });

      if (error instanceof ExternalApiError || error instanceof RateLimitError) {
        throw error;
      }
      throw new ExternalApiError(
        `Failed to fetch race totals: ${error instanceof Error ? error.message : 'Unknown error'}`,
        'KRA_API',
        502,
        endpoint
      );
    }
  }

  /**
   * Fetch jockey detail information from API12_1
   * @param jkNo Jockey number
   * @param options Request options
   */
  async getJockeyDetail(jkNo: string, options: KraApiRequestOptions = {}): Promise<Api12_1Item | null> {
    const endpoint = KraApiEndpoint.JOCKEY_INFO;
    const params = { jk_no: jkNo };

    logger.debug('Fetching jockey detail', { jkNo, endpoint });

    try {
      const response = await this.fetchWithRetry<Api12_1Response>(endpoint, params, options);

      if (!response.response || response.response.header.resultCode !== '00') {
        // For jockey details, return null if not found rather than throwing
        if (response.response?.header?.resultCode === '03') {
          logger.debug('Jockey not found', { jkNo });
          return null;
        }

        throw new ExternalApiError(
          `KRA API returned error: ${response.response?.header?.resultMsg || 'Unknown error'}`,
          'KRA_API',
          502,
          endpoint,
          response.response?.header?.resultCode,
          response.response?.header?.resultMsg
        );
      }

      const items = response.response.body.items.item;
      const jockeyData = Array.isArray(items) ? items[0] : items;

      logger.debug('Jockey detail fetched successfully', { jkNo, jockeyName: jockeyData?.jkName });

      return jockeyData || null;
    } catch (error) {
      logger.error('Failed to fetch jockey detail', { error, jkNo });

      if (error instanceof ExternalApiError || error instanceof RateLimitError) {
        throw error;
      }

      throw new ExternalApiError(
        `Failed to fetch jockey detail: ${error instanceof Error ? error.message : 'Unknown error'}`,
        'KRA_API',
        502,
        endpoint
      );
    }
  }

  /**
   * Fetch trainer detail information from API19_1
   * @param trNo Trainer number
   * @param options Request options
   */
  async getTrainerDetail(trNo: string, options: KraApiRequestOptions = {}): Promise<Api19_1Item | null> {
    const endpoint = KraApiEndpoint.TRAINER_INFO;
    const params = { tr_no: trNo };

    logger.debug('Fetching trainer detail', { trNo, endpoint });

    try {
      const response = await this.fetchWithRetry<Api19_1Response>(endpoint, params, options);

      if (!response.response || response.response.header.resultCode !== '00') {
        // For trainer details, return null if not found rather than throwing
        if (response.response?.header?.resultCode === '03') {
          logger.debug('Trainer not found', { trNo });
          return null;
        }

        throw new ExternalApiError(
          `KRA API returned error: ${response.response?.header?.resultMsg || 'Unknown error'}`,
          'KRA_API',
          502,
          endpoint,
          response.response?.header?.resultCode,
          response.response?.header?.resultMsg
        );
      }

      const items = response.response.body.items.item;
      const trainerData = Array.isArray(items) ? items[0] : items;

      logger.debug('Trainer detail fetched successfully', { trNo, trainerName: trainerData?.trName });

      return trainerData || null;
    } catch (error) {
      logger.error('Failed to fetch trainer detail', { error, trNo });

      if (error instanceof ExternalApiError || error instanceof RateLimitError) {
        throw error;
      }

      throw new ExternalApiError(
        `Failed to fetch trainer detail: ${error instanceof Error ? error.message : 'Unknown error'}`,
        'KRA_API',
        502,
        endpoint
      );
    }
  }

  /**
   * Fetch data with retry logic and exponential backoff
   * @private
   */
  private async fetchWithRetry<T>(
    endpoint: string,
    params: Record<string, string>,
    options: KraApiRequestOptions = {}
  ): Promise<T> {
    const {
      timeout = this.defaultTimeout,
      retryAttempts = this.retryConfig.attempts,
      retryDelay = this.retryConfig.delay,
      headers = {},
    } = options;

    let lastError: Error;

    for (let attempt = 1; attempt <= retryAttempts; attempt++) {
      try {
        // Check rate limit
        await this.checkRateLimit();

        const url = this.buildUrl(endpoint, params);
        const { signal, cleanup } = this.createTimeoutSignal(timeout);
        const requestOptions: RequestInit = {
          method: 'GET',
          headers: {
            Accept: 'application/json',
            'User-Agent': 'collector/1.0',
            ...headers,
          },
          signal,
        };

        logger.debug('Making API request', {
          url,
          attempt,
          maxAttempts: retryAttempts,
        });

        const response = await fetch(url, requestOptions).finally(() => {
          cleanup();
        });

        // Handle rate limiting
        if (response.status === 429) {
          const retryAfter = parseInt(response.headers.get('Retry-After') || '60');
          throw new RateLimitError(
            'KRA API rate limit exceeded',
            retryAfter,
            this.rateLimitConfig.maxRequests,
            this.rateLimitConfig.currentRequests
          );
        }

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = (await response.json()) as T;

        // Increment rate limit counter
        this.incrementRateLimitCounter();

        return data;
      } catch (error) {
        lastError = error as Error;

        // Don't retry certain errors
        if (error instanceof RateLimitError || (error instanceof Error && error.name === 'AbortError')) {
          throw error;
        }

        if (attempt === retryAttempts) {
          break;
        }

        // Calculate exponential backoff delay
        const delay = retryDelay * Math.pow(this.retryConfig.backoffFactor, attempt - 1);

        logger.warn('API request failed, retrying', {
          endpoint,
          attempt,
          maxAttempts: retryAttempts,
          error: error instanceof Error ? error.message : 'Unknown error',
          retryDelay: delay,
        });

        await this.delay(delay);
      }
    }

    throw lastError!;
  }

  /**
   * Check rate limit and wait if necessary
   * @private
   */
  private async checkRateLimit(): Promise<void> {
    const now = Date.now();

    // Reset window if expired
    if (now - this.rateLimitConfig.windowStart >= this.rateLimitConfig.windowMs) {
      this.rateLimitConfig.currentRequests = 0;
      this.rateLimitConfig.windowStart = now;
    }

    // Check if rate limit exceeded
    if (this.rateLimitConfig.currentRequests >= this.rateLimitConfig.maxRequests) {
      const waitTime = this.rateLimitConfig.windowMs - (now - this.rateLimitConfig.windowStart);

      if (waitTime > 0) {
        logger.warn('Rate limit reached, waiting', { waitTimeMs: waitTime });
        await this.delay(waitTime);

        // Reset counters after waiting
        this.rateLimitConfig.currentRequests = 0;
        this.rateLimitConfig.windowStart = Date.now();
      }
    }
  }

  /**
   * Increment rate limit counter
   * @private
   */
  private incrementRateLimitCounter(): void {
    this.rateLimitConfig.currentRequests++;
  }

  /**
   * Build API URL with parameters
   * @private
   */
  private buildUrl(endpoint: string, params: Record<string, string>): string {
    // The endpoint now includes both API_ID and endpoint_name (e.g., "API214_1/RaceDetailResult_1")
    // Split the endpoint to get API_ID and endpoint_name
    const [apiId, endpointName] = endpoint.split('/');

    // Build URL as: baseUrl/API_ID/endpoint_name
    const url = new URL(`${this.baseUrl}/${apiId}/${endpointName}`);

    // Add service key if available
    if (this.apiKey) {
      url.searchParams.set('serviceKey', this.apiKey);
    }

    // Add request parameters
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, value);
      }
    });

    return url.toString();
  }

  /**
   * Promise-based delay utility
   * @private
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Create an abort signal with timeout.
   * Falls back to AbortController when AbortSignal.timeout is unavailable.
   * @private
   */
  private createTimeoutSignal(timeout: number): { signal: AbortSignal; cleanup: () => void } {
    const timeoutFactory = (AbortSignal as unknown as { timeout?: (ms: number) => AbortSignal }).timeout;
    if (typeof timeoutFactory === 'function') {
      return { signal: timeoutFactory(timeout), cleanup: () => {} };
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    return {
      signal: controller.signal,
      cleanup: () => clearTimeout(timeoutId),
    };
  }

  /**
   * Check API health
   */
  async healthCheck(): Promise<boolean> {
    try {
      // Test with a simple API call (get Seoul race 1 for today)
      const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      await this.fetchWithRetry(
        KraApiEndpoint.RACE_RESULT,
        {
          rc_date: today,
          meet: KraMeet.SEOUL,
          rc_no: '1',
        },
        { timeout: 5000, retryAttempts: 1 }
      );

      logger.info('KRA API health check passed');
      return true;
    } catch (error) {
      logger.error('KRA API health check failed', { error });
      return false;
    }
  }
}
