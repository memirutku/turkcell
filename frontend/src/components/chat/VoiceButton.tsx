"use client";
import { VoiceState } from "@/types";
import { Mic, MicOff, Loader2, Volume2 } from "lucide-react";

interface VoiceButtonProps {
  voiceState: VoiceState;
  onClick: () => void;
  disabled: boolean;
  isVoiceSupported: boolean;
  conversationActive?: boolean;
}

export function VoiceButton({ voiceState, onClick, disabled, isVoiceSupported, conversationActive }: VoiceButtonProps) {
  const isDisabledOrUnsupported = disabled || !isVoiceSupported || !!conversationActive;
  const isClickable = voiceState === "idle" || voiceState === "recording";

  const getIcon = () => {
    switch (voiceState) {
      case "idle":
        return <Mic className="h-5 w-5" />;
      case "recording":
        return <MicOff className="h-5 w-5" />;
      case "processing":
        return <Loader2 className="h-5 w-5 animate-spin" />;
      case "playing":
        return <Volume2 className="h-5 w-5 animate-pulse" />;
    }
  };

  const getAriaLabel = () => {
    if (isDisabledOrUnsupported && voiceState === "idle") {
      return "Metin yaniti devam ediyor";
    }
    switch (voiceState) {
      case "idle":
        return "Ses kaydi baslat";
      case "recording":
        return "Ses kaydini durdur";
      case "processing":
        return "Ses isleniyor";
      case "playing":
        return "Sesli yanit oynatuluyor";
    }
  };

  const getTitle = () => {
    if (isDisabledOrUnsupported) return undefined;
    switch (voiceState) {
      case "idle":
        return "Ses ile soru sorun";
      case "recording":
        return "Kaydi durdurmak icin tiklayin";
      default:
        return undefined;
    }
  };

  const getStyles = () => {
    if (isDisabledOrUnsupported) {
      return "text-gray-300 bg-white border border-gray-200 opacity-50 cursor-not-allowed";
    }
    switch (voiceState) {
      case "idle":
        return "text-gray-500 bg-white border border-gray-200 hover:text-gray-700 hover:bg-gray-50 hover:border-gray-300 cursor-pointer";
      case "recording":
        return "text-white bg-red-500 ring-4 ring-red-500/30 animate-pulse cursor-pointer";
      case "processing":
        return "text-turkcell-blue bg-white border border-gray-200 cursor-not-allowed";
      case "playing":
        return "text-turkcell-blue bg-turkcell-blue/10 border border-turkcell-blue/20 cursor-not-allowed";
    }
  };

  return (
    <button
      type="button"
      onClick={isClickable && !isDisabledOrUnsupported ? onClick : undefined}
      disabled={isDisabledOrUnsupported || !isClickable}
      aria-label={getAriaLabel()}
      title={getTitle()}
      className={`h-12 w-12 rounded-xl flex items-center justify-center shrink-0 transition-all ${getStyles()}`}
    >
      {getIcon()}
    </button>
  );
}
