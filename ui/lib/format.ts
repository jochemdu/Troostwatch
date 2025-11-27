/** Formatting utilities for the Troostwatch UI. */

export function formatCurrency(value: number | null | undefined, fallback = '—'): string {
  if (value == null) return fallback;
  return `€${value.toLocaleString('nl-NL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatCurrencyWhole(value: number | null | undefined, fallback = '—'): string {
  if (value == null) return fallback;
  return `€${value.toLocaleString('nl-NL', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

export function formatDateTime(value: string | null | undefined, fallback = '—'): string {
  if (!value) return fallback;
  try {
    return new Date(value).toLocaleString('nl-NL', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return fallback;
  }
}

export function formatDateOnly(value: string | null | undefined, fallback = '—'): string {
  if (!value) return fallback;
  try {
    return new Date(value).toLocaleDateString('nl-NL', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch {
    return fallback;
  }
}

export function formatNumber(value: number | null | undefined, fallback = '—'): string {
  if (value == null) return fallback;
  return value.toLocaleString('nl-NL');
}

export function truncate(value: string | null | undefined, maxLength: number): string {
  if (!value) return '';
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 3)}...`;
}