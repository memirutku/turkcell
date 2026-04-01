"use client";
import { ActionResult } from "@/types";
import { CheckCircle2, XCircle, Info } from "lucide-react";

interface ActionResultCardProps {
  result: ActionResult;
}

export function ActionResultCard({ result }: ActionResultCardProps) {
  if (result.success) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <CheckCircle2 className="h-5 w-5 text-green-700" aria-hidden="true" />
          <h3 className="text-base font-semibold leading-snug text-green-700">
            Islem Basarili
          </h3>
        </div>
        <p className="text-sm leading-relaxed text-green-700 mb-2">
          {result.description}
        </p>
        {Object.keys(result.details).length > 0 && (
          <div className="space-y-1 mt-2">
            {Object.entries(result.details).map(([key, value]) => (
              <div key={key} className="flex justify-between text-sm">
                <span className="font-semibold text-green-700">{key}:</span>
                <span className="text-green-700">{value}</span>
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
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <Info className="h-5 w-5 text-gray-500" aria-hidden="true" />
          <h3 className="text-base font-semibold leading-snug text-gray-500">
            Islem Iptal Edildi
          </h3>
        </div>
        <p className="text-sm leading-relaxed text-gray-500">
          {result.description}
        </p>
      </div>
    );
  }

  // Failure state
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <XCircle className="h-5 w-5 text-red-700" aria-hidden="true" />
        <h3 className="text-base font-semibold leading-snug text-red-700">
          Islem Basarisiz
        </h3>
      </div>
      <p className="text-sm leading-relaxed text-red-700">
        {result.description}
      </p>
    </div>
  );
}
