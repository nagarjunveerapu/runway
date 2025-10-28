/**
 * Centralized Date Parser Utility for Frontend
 * 
 * This module provides consistent date parsing across the entire React app.
 * All date formats are normalized to ISO format (YYYY-MM-DD) for storage
 * and YYYY-MM for month fields.
 */

/**
 * Parse any date format to ISO format (YYYY-MM-DD)
 * 
 * @param {string} dateStr - Date string in various formats
 * @returns {string|null} ISO format date string (YYYY-MM-DD) or null if parsing fails
 * 
 * @example
 * parseDate("15/01/2025") => "2025-01-15"
 * parseDate("2025-01-15") => "2025-01-15"
 * parseDate("01/15/2025") => "2025-01-15"
 */
export function parseDate(dateStr) {
  if (!dateStr) return null;

  const str = String(dateStr).trim();

  // Already in ISO format?
  if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
    return str;
  }

  // Try parsing as Date object (handles most formats)
  try {
    const d = new Date(str);
    if (!isNaN(d.getTime())) {
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    }
  } catch (e) {
    // Fallback to manual parsing
  }

  // Manual parsing for DD/MM/YYYY
  if (str.includes('/')) {
    const parts = str.split('/');
    if (parts.length >= 3) {
      const day = parts[0].padStart(2, '0');
      const month = parts[1].padStart(2, '0');
      const year = fixYear(parts[2]);
      return `${year}-${month}-${day}`;
    }
  }

  // Manual parsing for DD-MM-YYYY
  if (str.includes('-') && !str.includes('/')) {
    const parts = str.split('-');
    if (parts.length === 3) {
      // Check if likely DD-MM-YYYY (first two parts are 2 digits)
      if (parts[0].length === 2 && parts[1].length === 2) {
        const day = parts[0];
        const month = parts[1];
        const year = fixYear(parts[2]);
        return `${year}-${month}-${day}`;
      }
      // Otherwise assume YYYY-MM-DD
      if (parts[0].length === 4) {
        return str;
      }
    }
  }

  console.warn(`Could not parse date: ${dateStr}`);
  return null;
}

/**
 * Parse month from any date format to YYYY-MM format
 * 
 * @param {string} dateStr - Date string in various formats
 * @returns {string} Month string in YYYY-MM format or empty string
 * 
 * @example
 * parseMonth("15/01/2025") => "2025-01"
 * parseMonth("2025-01-15") => "2025-01"
 * parseMonth("01/15/2025") => "2025-01"
 */
export function parseMonth(dateStr) {
  if (!dateStr) return '';

  const str = String(dateStr).trim();

  // Already in YYYY-MM format?
  if (/^\d{4}-\d{2}$/.test(str)) {
    return str;
  }

  // Already in YYYY-MM-DD format?
  if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
    return str.slice(0, 7);
  }

  // Parse full date and extract month
  const parsedDate = parseDate(str);
  if (parsedDate) {
    return parsedDate.slice(0, 7);
  }

  // Try manual parsing for month extraction
  if (str.includes('/')) {
    const parts = str.split('/');
    if (parts.length >= 3) {
      const month = parts[1].padStart(2, '0');
      const year = fixYear(parts[2]);
      return `${year}-${month}`;
    }
  }

  if (str.includes('-')) {
    const parts = str.split('-');
    if (parts.length >= 2) {
      // Check if YYYY-MM or YYYY-MM-DD
      if (parts[0].length === 4) {
        return `${parts[0]}-${parts[1].padStart(2, '0')}`;
      }
      // Might be DD-MM-YYYY
      if (parts.length === 3 && parts[0].length === 2) {
        const month = parts[1].padStart(2, '0');
        const year = fixYear(parts[2]);
        return `${year}-${month}`;
      }
    }
  }

  return '';
}

/**
 * Fix year string to 4-digit format
 * 
 * @param {string} yearStr - Year string (1, 2, or 4 digits)
 * @returns {string} 4-digit year string
 * 
 * @example
 * fixYear("25") => "2025"
 * fixYear("2") => "2025"
 * fixYear("2025") => "2025"
 */
function fixYear(yearStr) {
  const str = String(yearStr).trim();

  if (str.length === 1) {
    // Single digit: assume current decade (e.g., "2" -> "2025")
    return '2025';
  } else if (str.length === 2) {
    // Two digits: add 20 prefix
    const year = '20' + str;
    // If year seems too old, assume 2025+
    if (parseInt(year) < 2024) {
      return '2025';
    }
    return year;
  } else if (str.length === 4) {
    return str;
  }

  return '2025'; // Default fallback
}

/**
 * Format month string for display (YYYY-MM -> "Month YYYY")
 * 
 * @param {string} monthStr - Month in YYYY-MM format
 * @returns {string} Formatted string like "January 2025"
 */
export function formatMonthForDisplay(monthStr) {
  if (!monthStr || monthStr.length < 7) {
    return '';
  }

  try {
    const [year, month] = monthStr.slice(0, 7).split('-');
    const d = new Date(parseInt(year), parseInt(month) - 1, 1);
    return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  } catch (e) {
    return monthStr;
  }
}

/**
 * Get current month in YYYY-MM format
 * 
 * @returns {string} Current month as YYYY-MM
 */
export function getCurrentMonth() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  return `${year}-${month}`;
}

/**
 * Check if month string is in valid YYYY-MM format
 * 
 * @param {string} monthStr - Month string to validate
 * @returns {boolean} True if valid YYYY-MM format
 */
export function isValidMonth(monthStr) {
  if (!monthStr || monthStr.length < 7) {
    return false;
  }

  try {
    const [year, month] = monthStr.slice(0, 7).split('-');
    const y = parseInt(year);
    const m = parseInt(month);
    return year.length === 4 && month.length === 2 && y >= 2000 && y <= 2100 && m >= 1 && m <= 12;
  } catch (e) {
    return false;
  }
}

// Backward compatibility: export formatMonth
export function formatMonth(dateStr) {
  return parseMonth(dateStr);
}

