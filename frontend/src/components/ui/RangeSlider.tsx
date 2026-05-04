import { useCallback, useId, useMemo } from 'react';
import { cn } from '@/lib/cn';

export interface RangeSliderProps {
  min: number;
  max: number;
  step?: number;
  value: [number, number];
  onChange: (value: [number, number]) => void;
  formatValue?: (n: number) => string;
  label?: string;
  className?: string;
}

export function RangeSlider({
  min,
  max,
  step = 1,
  value,
  onChange,
  formatValue,
  label,
  className,
}: RangeSliderProps): JSX.Element {
  const id = useId();
  const [low, high] = value;

  const pct = useMemo(() => {
    const range = max - min || 1;
    return {
      low: ((low - min) / range) * 100,
      high: ((high - min) / range) * 100,
    };
  }, [low, high, min, max]);

  const handleLow = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const next = Math.min(Number(e.target.value), high);
      onChange([next, high]);
    },
    [high, onChange],
  );

  const handleHigh = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const next = Math.max(Number(e.target.value), low);
      onChange([low, next]);
    },
    [low, onChange],
  );

  const formatter = formatValue ?? ((n: number) => n.toString());

  return (
    <div className={cn('w-full', className)}>
      {label && (
        <div className="mb-2 flex items-center justify-between text-xs font-medium text-text-1">
          <label htmlFor={`${id}-low`}>{label}</label>
          <span className="text-text-0">
            {formatter(low)} – {formatter(high)}
          </span>
        </div>
      )}
      <div className="relative h-8">
        <div className="pointer-events-none absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-bg-3" />
        <div
          className="pointer-events-none absolute top-1/2 h-1 -translate-y-1/2 rounded-full bg-accent"
          style={{ left: `${pct.low}%`, right: `${100 - pct.high}%` }}
        />
        <input
          id={`${id}-low`}
          type="range"
          min={min}
          max={max}
          step={step}
          value={low}
          onChange={handleLow}
          className="range-input"
          aria-label={label ? `${label} min` : 'Range min'}
        />
        <input
          id={`${id}-high`}
          type="range"
          min={min}
          max={max}
          step={step}
          value={high}
          onChange={handleHigh}
          className="range-input"
          aria-label={label ? `${label} max` : 'Range max'}
        />
        <style>{`
          .range-input {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            background: transparent;
            pointer-events: none;
            -webkit-appearance: none;
            appearance: none;
          }
          .range-input::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            pointer-events: auto;
            height: 18px;
            width: 18px;
            border-radius: 9999px;
            background: #fff;
            border: 2px solid #e50914;
            box-shadow: 0 1px 4px rgba(0,0,0,0.7);
            cursor: pointer;
          }
          .range-input::-moz-range-thumb {
            pointer-events: auto;
            height: 18px;
            width: 18px;
            border-radius: 9999px;
            background: #fff;
            border: 2px solid #e50914;
            box-shadow: 0 1px 4px rgba(0,0,0,0.7);
            cursor: pointer;
          }
          .range-input:focus-visible::-webkit-slider-thumb {
            outline: 2px solid #e50914;
            outline-offset: 2px;
          }
        `}</style>
      </div>
    </div>
  );
}
