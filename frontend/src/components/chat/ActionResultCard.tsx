"use client";
import { ActionResult } from "@/types";
import { CheckCircle2, XCircle, Info } from "lucide-react";

interface ActionResultCardProps {
  result: ActionResult;
}

export function ActionResultCard({ result }: ActionResultCardProps) {
  if (result.success) {
    return (
      <div className="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <CheckCircle2 className="h-5 w-5 text-green-700 dark:text-green-300" aria-hidden="true" />
          <h3 className="text-base font-semibold leading-snug text-green-700 dark:text-green-300">
            İşlem Başarılı
          </h3>
        </div>
        <p className="text-sm leading-relaxed text-green-700 dark:text-green-300 mb-2">
          {result.description}
        </p>
        {Object.keys(result.details).length > 0 && (
          <div className="space-y-1 mt-2">
            {Object.entries(result.details).map(([key, value]) => (
              <div key={key} className="flex justify-between text-sm">
                <span className="font-semibold text-green-700 dark:text-green-300">{key}:</span>
                <span className="text-green-700 dark:text-green-300">{value}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Check if this is a cancellation vs. a failure
  const isCancelled = result.description.includes("iptal");

  if (isCancelled) {
    return (
      <div className="bg-muted border border-border rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <Info className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          <h3 className="text-base font-semibold leading-snug text-muted-foreground">
            İşlem İptal Edildi
          </h3>
        </div>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {result.description}
        </p>
      </div>
    );
  }

  // Failure state
  return (
    <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <XCircle className="h-5 w-5 text-red-700 dark:text-red-300" aria-hidden="true" />
        <h3 className="text-base font-semibold leading-snug text-red-700 dark:text-red-300">
          İşlem Başarısız
        </h3>
      </div>
      <p className="text-sm leading-relaxed text-red-700 dark:text-red-300">
        {result.description}
      </p>
    </div>
  );
}
