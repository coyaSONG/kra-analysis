// Utility functions
export const formatDate = (date: Date): string => {
  return date.toISOString().split('T')[0] ?? '';
};

export const parseRaceDate = (dateStr: string): Date => {
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) {
    throw new Error(`Invalid date format: ${dateStr}`);
  }
  return date;
};

export const validateRaceNumber = (raceNo: number): boolean => {
  return raceNo >= 1 && raceNo <= 12;
};

export const delay = (ms: number): Promise<void> => {
  return new Promise((resolve) => setTimeout(resolve, ms));
};

export const retry = async <T>(fn: () => Promise<T>, maxAttempts: number = 3, delayMs: number = 1000): Promise<T> => {
  let lastError: Error;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      if (attempt === maxAttempts) {
        break;
      }

      await delay(delayMs * attempt); // Exponential backoff
    }
  }

  throw lastError!;
};
