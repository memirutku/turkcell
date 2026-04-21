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
      return "Metin yanıtı devam ediyor";
    }
    switch (voiceState) {
      case "idle":
        return "Ses kaydı başlat";
      case "recording":
        return "Ses kaydını durdur";
      case "processing":
        return "Ses işleniyor";
      case "playing":
        return "Sesli yanıt oynatılıyor";
    }
  };

  const getTitle = () => {
    if (isDisabledOrUnsupported) return undefined;
    switch (voiceState) {
      case "idle":
        return "Ses ile soru sorun";
      case "recording":
        return "Kaydı durdurmak için tıklayın";
      default:
        return undefined;
    }
  };

  const getStyles = () => {
    if (isDisabledOrUnsupported) {
      return "text-muted-foreground/50 bg-card border border-border opacity-50 cursor-not-allowed";
    }
    switch (voiceState) {
      case "idle":
        return "text-muted-foreground bg-card border border-border hover:text-foreground hover:bg-muted cursor-pointer";
      case "recording":
        return "text-white bg-red-500 ring-4 ring-red-500/30 animate-pulse cursor-pointer";
      case "processing":
        return "text-umay-blue bg-card border border-border cursor-not-allowed";
      case "playing":
        return "text-umay-blue bg-umay-blue/10 border border-umay-blue/20 cursor-not-allowed";
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
