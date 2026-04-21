"use client";
import { Loader2 } from "lucide-react";

export function ActionProcessingIndicator() {
  return (
    <div
      className="flex items-center gap-2 py-2"
      role="status"
      aria-live="assertive"
    >
      <Loader2 className="h-5 w-5 text-umay-blue animate-spin" aria-hidden="true" />
      <span className="text-sm text-foreground">
        İşlem yürütülüyor...
      </span>
    </div>
  );
}
