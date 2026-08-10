import { describe, expect, it } from 'vitest';
import { cn, formatDate, formatDelta, formatMoney } from './format';

describe('format utilities', () => {
  it('formats hidden money without leaking the amount', () => {
    expect(formatMoney(123.45, 'CAD', true)).toBe('••••••');
  });

  it('formats signed deltas', () => {
    expect(formatDelta(2.34)).toBe('▲ 2.3%');
    expect(formatDelta(-1.25)).toBe('▼ 1.3%');
  });

  it('formats dates without timezone drift', () => {
    expect(formatDate('2026-04-28')).toBe('Apr 28');
  });

  it('joins class names while ignoring falsey values', () => {
    expect(cn('a', null, 'b', false, '')).toBe('a b');
  });
});
