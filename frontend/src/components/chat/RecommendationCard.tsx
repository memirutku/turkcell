"use client";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import { TariffRecommendation } from "@/types";

interface RecommendationCardProps {
  recommendation: TariffRecommendation;
  currentTariff: string;
  index: number;
}

function formatTL(amount: string): string {
  const num = parseFloat(amount);
  if (isNaN(num)) return amount + " TL";
  // Turkish format: period thousands, comma decimal
  const parts = num.toFixed(2).split(".");
  const intPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${intPart},${parts[1]} TL`;
}

export function RecommendationCard({
  recommendation,
  currentTariff,
  index,
}: RecommendationCardProps) {
  const savings = parseFloat(recommendation.savings);
  const savingsPositive = savings > 0;
  const isTopPick = index === 0;

  return (
    <Card
      className={`mt-3 border-turkcell-blue/20 ${isTopPick ? "border-l-4 border-l-turkcell-yellow" : ""}`}
      role="region"
      aria-label={`Tarife onerisi: ${recommendation.tariff_name}${isTopPick ? " - Onerilen" : ""}${savingsPositive ? `, aylik ${formatTL(recommendation.savings)} tasarruf` : ""}`}
    >
      <CardHeader className="pb-2 px-4 pt-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold leading-snug">
            {recommendation.tariff_name}
          </CardTitle>
          <div className="flex gap-1">
            {isTopPick && (
              <Badge className="bg-turkcell-yellow text-turkcell-dark text-xs" aria-label="Onerilen tarife">
                Onerilen
              </Badge>
            )}
            {savingsPositive && savings >= 30 && (
              <Badge className="bg-green-100 text-green-700 text-xs" aria-label="En cok tasarruf saglayan tarife">
                En Cok Tasarruf
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        {/* Comparison table */}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-sm font-semibold leading-snug">Ozellik</TableHead>
              <TableHead className="text-sm font-semibold leading-snug">Mevcut Tarife</TableHead>
              <TableHead className="text-sm font-semibold leading-snug">Onerilen Tarife</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell className="text-sm">Veri</TableCell>
              <TableCell className="text-sm">{currentTariff}</TableCell>
              <TableCell className="text-sm">{recommendation.data_gb} GB</TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="text-sm">Arama</TableCell>
              <TableCell className="text-sm">-</TableCell>
              <TableCell className="text-sm">{recommendation.voice_minutes} dk</TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="text-sm">SMS</TableCell>
              <TableCell className="text-sm">-</TableCell>
              <TableCell className="text-sm">{recommendation.sms_count}</TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="text-sm font-semibold">Tahmini Aylik</TableCell>
              <TableCell className="text-sm font-semibold">-</TableCell>
              <TableCell className="text-sm font-semibold">{formatTL(recommendation.projected_cost)}</TableCell>
            </TableRow>
          </TableBody>
        </Table>

        <Separator className="my-3" />

        {/* Savings callout */}
        {savingsPositive ? (
          <div className="p-2 bg-green-50 rounded-lg text-green-700 text-sm font-medium">
            Aylik {formatTL(recommendation.savings)} tasarruf
          </div>
        ) : savings < 0 ? (
          <div className="p-2 bg-red-50 rounded-lg text-red-700 text-sm font-medium">
            Aylik {formatTL(Math.abs(savings).toFixed(2))} daha fazla
          </div>
        ) : null}

        {/* Reasons */}
        {recommendation.reasons.length > 0 && (
          <div className="mt-3">
            <p className="text-sm font-semibold leading-snug mb-1">Neden bu tarife?</p>
            <ul className="list-disc list-inside space-y-0.5">
              {recommendation.reasons.map((reason, i) => (
                <li key={i} className="text-sm leading-relaxed text-gray-700">
                  {reason}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
