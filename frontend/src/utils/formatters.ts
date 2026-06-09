/**
 * Centralized utility to sanitize, normalize, and format internship stipend values.
 * Prevents double currency symbols (e.g. '$ ₹ 10,000') and returns clean formats.
 */
export interface FormattedStipend {
  formatted: string;
  currency: 'INR' | 'USD' | null;
}

export function formatStipend(stipendStr: string | null | undefined): FormattedStipend {
  if (!stipendStr) {
    return { formatted: 'Unspecified', currency: null };
  }

  let cleanStr = stipendStr.trim();

  // If stipend starts or contains double currency symbols like "$ ₹" or "₹ $", clean them up
  if (cleanStr.includes('$') && cleanStr.includes('₹')) {
    // Default to Rupee (INR) if both symbols exist, as INR is the primary currency for local listings
    cleanStr = cleanStr.replace(/\$/g, '').replace(/\s+/g, ' ').trim();
  }

  // Detect currency type
  let currency: 'INR' | 'USD' | null = null;
  if (cleanStr.includes('₹')) {
    currency = 'INR';
  } else if (cleanStr.includes('$')) {
    currency = 'USD';
  } else {
    // If no symbol is present but we have digits, assume INR as default
    const hasDigits = /\d+/.test(cleanStr);
    if (hasDigits) {
      currency = 'INR';
    }
  }

  let formatted = cleanStr;

  // Ensure consistent spacing and prefix placement
  if (currency === 'INR') {
    // Clean any leading symbol and re-apply cleanly as "₹ 7,000 /month"
    const stripSymbol = formatted.replace(/₹/g, '').trim();
    
    // Check if it starts with digits to format nicely
    const digitsMatch = stripSymbol.match(/^(\d+)/);
    if (digitsMatch) {
      const num = parseInt(digitsMatch[0], 10);
      const rest = stripSymbol.substring(digitsMatch[0].length);
      formatted = `₹ ${num.toLocaleString('en-IN')}${rest}`;
    } else {
      formatted = `₹ ${stripSymbol}`;
    }
  } else if (currency === 'USD') {
    // Clean any leading symbol and re-apply cleanly as "$500 /month" (no space for USD)
    const stripSymbol = formatted.replace(/\$/g, '').trim();
    
    const digitsMatch = stripSymbol.match(/^(\d+)/);
    if (digitsMatch) {
      const num = parseInt(digitsMatch[0], 10);
      const rest = stripSymbol.substring(digitsMatch[0].length);
      formatted = `$${num.toLocaleString('en-US')}${rest}`;
    } else {
      formatted = `$${stripSymbol}`;
    }
  }

  // Final visual normalization (compress multiple spaces, fix slash spacings)
  formatted = formatted
    .replace(/\s+/g, ' ')
    .replace(/\s*\/\s*/g, ' /') // Ensure space before slash, e.g. " /month"
    .trim();

  return { formatted, currency };
}
