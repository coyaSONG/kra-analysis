import type { Response } from 'express';

export const sendNotImplemented = (res: Response, message: string, details: string): void => {
  res.status(501).json({
    success: false,
    error: {
      code: 'NOT_IMPLEMENTED',
      message,
      details,
    },
    timestamp: new Date().toISOString(),
  });
};
