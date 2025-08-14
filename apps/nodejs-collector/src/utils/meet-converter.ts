/**
 * Meet/Track name converter utility
 * 
 * Converts between Korean meet names and numeric codes required by KRA API
 */

import { Meet } from '../types/index.js';

/**
 * Mapping of Korean meet names to numeric codes
 */
const MEET_NAME_TO_CODE: Record<string, Meet> = {
  '서울': Meet.SEOUL,
  '제주': Meet.JEJU,
  '부산': Meet.BUSAN,
  '부산경남': Meet.BUSAN,
};

/**
 * Mapping of numeric codes to Korean meet names
 */
const MEET_CODE_TO_NAME: Record<Meet, string> = {
  [Meet.SEOUL]: '서울',
  [Meet.JEJU]: '제주',
  [Meet.BUSAN]: '부산경남',
};

/**
 * Convert Korean meet name to numeric code
 * @param meetName Korean meet name (e.g., '서울', '제주', '부산', '부산경남')
 * @returns Numeric meet code (1, 2, or 3)
 */
export function meetNameToCode(meetName: string): Meet {
  // If it's already a number string, parse it
  if (/^\d+$/.test(meetName)) {
    const code = parseInt(meetName, 10);
    if (Object.values(Meet).includes(code)) {
      return code as Meet;
    }
  }

  // Convert Korean name to code
  const code = MEET_NAME_TO_CODE[meetName];
  if (code === undefined) {
    throw new Error(`Invalid meet name: ${meetName}. Must be one of ${Object.keys(MEET_NAME_TO_CODE).join(', ')}`);
  }
  
  return code;
}

/**
 * Convert numeric code to Korean meet name
 * @param meetCode Numeric meet code (1, 2, or 3)
 * @returns Korean meet name
 */
export function meetCodeToName(meetCode: Meet | number): string {
  const name = MEET_CODE_TO_NAME[meetCode as Meet];
  if (!name) {
    throw new Error(`Invalid meet code: ${meetCode}. Must be 1 (Seoul), 2 (Jeju), or 3 (Busan)`);
  }
  
  return name;
}

/**
 * Convert meet parameter to string format for API
 * @param meet Meet name or code
 * @returns String representation of meet code
 */
export function meetToApiParam(meet: string | number | Meet): string {
  if (typeof meet === 'number') {
    return meet.toString();
  }
  
  if (typeof meet === 'string') {
    // If it's already a number string, return it
    if (/^\d+$/.test(meet)) {
      const code = parseInt(meet, 10);
      if (Object.values(Meet).includes(code)) {
        return meet;
      }
    }
    
    // Convert Korean name to code
    const code = meetNameToCode(meet);
    return code.toString();
  }
  
  throw new Error(`Invalid meet parameter: ${meet}`);
}

/**
 * Check if a string is a valid meet name
 * @param value Value to check
 * @returns True if valid meet name
 */
export function isValidMeetName(value: string): boolean {
  return value in MEET_NAME_TO_CODE || /^[123]$/.test(value);
}

/**
 * Get all valid meet names
 * @returns Array of valid meet names
 */
export function getValidMeetNames(): string[] {
  return Object.keys(MEET_NAME_TO_CODE);
}

/**
 * Get all valid meet codes
 * @returns Array of valid meet codes
 */
export function getValidMeetCodes(): Meet[] {
  return Object.values(Meet);
}