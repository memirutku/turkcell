"use client";
import { VoiceState } from "@/types";
import { Loader2, Volume2 } from "lucide-react";

interface VoiceStatusBannerProps {
  voiceState: VoiceState;
}

export function VoiceStatusBanner({ voiceState }: VoiceStatusBannerProps) {
  if (voiceState === "idle") return null;

  const getContent = () => {
    switch (voiceState) {
      case "recording":
        return (
          <>
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-xs text-gray-500">Dinleniyor...</span>
          </>
        );
      case "processing":
        return (
          <>
            <Loader2 className="h-3.5 w-3.5 text-turkcell-blue animate-spin" />
            <span className="text-xs text-gray-500">Sesiniz isleniyor...</span>
          </>
        );
      case "playing":
        return (
          <>
            <Volume2 className="h-3.5 w-3.5 text-turkcell-blue animate-pulse" />
            <span className="text-xs text-gray-500">Sesli yanit oynatuluyor...</span>
          </>
        );
    }
  };

  return (
    <div className="flex items-center gap-2 mt-1" role="status" aria-live="polite">
      {getContent()}
    </div>
  );
}
