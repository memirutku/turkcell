"use client";

interface UsageBarProps {
  label: string;
  used: number;
  limit: number;
  unit: string;
  percent: number;
}

export function UsageBar({ label, used, limit, unit, percent }: UsageBarProps) {
  const isOverLimit = percent > 100;
  const isNearLimit = percent > 80 && percent <= 100;
  const clampedPercent = Math.min(percent, 100);

  // Color based on state (from UI-SPEC)
  let barColor = "bg-turkcell-blue";        // normal
  if (isNearLimit) barColor = "bg-turkcell-yellow"; // near limit (80-100%)
  if (isOverLimit) barColor = "bg-orange-700";      // over limit (>100%)

  const overageAmount = isOverLimit ? (used - limit) : 0;

  const valueText = isOverLimit
    ? `${used}/${limit} ${unit} (+${overageAmount.toFixed(1)} ${unit} asim)`
    : `${used}/${limit} ${unit}`;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="font-semibold leading-snug">{label}</span>
        <span className={`leading-relaxed ${isOverLimit ? "text-orange-700 font-semibold" : "text-gray-600"}`}>
          {valueText}
        </span>
      </div>
      <div
        className="h-2 w-full rounded-full bg-turkcell-gray overflow-hidden"
        role="progressbar"
        aria-label={`${label} kullanimi`}
        aria-valuenow={Math.round(percent)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuetext={`${label}: ${valueText}, yuzde ${Math.round(percent)}`}
      >
        <div
          className={`h-full rounded-full transition-all ${barColor}`}
          style={{ width: `${clampedPercent}%` }}
        />
      </div>
    </div>
  );
}
