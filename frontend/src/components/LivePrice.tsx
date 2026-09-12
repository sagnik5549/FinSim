import React from 'react';

export interface LivePriceProps {
  price: number;
  flash?: 'UP' | 'DOWN' | null;
  className?: string;
  prefix?: string;
  decimals?: number;
}

export function formatIndianCurrency(num: number, decimals: number = 2): string {
  if (isNaN(num) || num === null || num === undefined) return '0.00';
  return num.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export const LivePrice: React.FC<LivePriceProps> = ({
  price,
  flash,
  className = '',
  prefix = '₹',
  decimals = 2,
}) => {
  const flashClass =
    flash === 'UP'
      ? 'text-flash-up text-[#00d09c]'
      : flash === 'DOWN'
      ? 'text-flash-down text-[#eb5b3c]'
      : '';

  return (
    <span className={`inline-flex items-center font-mono transition-colors duration-300 ${flashClass} ${className}`}>
      {prefix}
      {formatIndianCurrency(price, decimals)}
    </span>
  );
};

export interface LiveChangeBadgeProps {
  changePct: number; // e.g. 1.25 for +1.25%
  changeAmount?: number; // e.g. 15.40 for +₹15.40
  flash?: 'UP' | 'DOWN' | null;
  className?: string;
  showIcon?: boolean;
}

export const LiveChangeBadge: React.FC<LiveChangeBadgeProps> = ({
  changePct,
  changeAmount,
  flash,
  className = '',
  showIcon = true,
}) => {
  const isPositive = changePct > 0;
  const isNegative = changePct < 0;

  const badgeClass = isPositive
    ? 'badge-groww-gain'
    : isNegative
    ? 'badge-groww-loss'
    : 'badge-groww-neutral';

  const flashClass =
    flash === 'UP'
      ? 'shadow-[0_0_8px_rgba(0,208,156,0.5)]'
      : flash === 'DOWN'
      ? 'shadow-[0_0_8px_rgba(235,91,60,0.5)]'
      : '';

  return (
    <span className={`${badgeClass} ${flashClass} ${className}`}>
      {showIcon && (
        <span className="text-[10px] font-bold leading-none">
          {isPositive ? '▲' : isNegative ? '▼' : '—'}
        </span>
      )}
      {changeAmount !== undefined && (
        <span>
          {isPositive ? '+' : isNegative ? '-' : ''}₹{formatIndianCurrency(Math.abs(changeAmount), 2)}{' '}
        </span>
      )}
      <span>
        {isPositive ? '+' : ''}
        {changePct.toFixed(2)}%
      </span>
    </span>
  );
};
