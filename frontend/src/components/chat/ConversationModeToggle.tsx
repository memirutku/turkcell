"use client";
import { ConversationState, LiveConversationState } from "@/types";
import { MessageSquare, PhoneOff, Loader2, AlertTriangle } from "lucide-react";

interface ConversationModeToggleProps {
  conversationState: ConversationState | LiveConversationState;
  onToggle: () => void;
  disabled: boolean;
  isVADLoading?: boolean;
  isVADErrored?: boolean;
}

export function ConversationModeToggle({
  conversationState,
  onToggle,
  disabled,
  isVADLoading,
  isVADErrored,
}: ConversationModeToggleProps) {
  const isActive = conversationState !== "off";

  const getIcon = () => {
    if (isActive) return <PhoneOff className="h-5 w-5" />;
    if (isVADErrored) return <AlertTriangle className="h-5 w-5" />;
    if (isVADLoading) return <Loader2 className="h-5 w-5 animate-spin" />;
    return <MessageSquare className="h-5 w-5" />;
  };

  const getAriaLabel = () => {
    if (isVADErrored) return "Ses tanıma modeli yüklenemedi";
    if (isVADLoading) return "Ses tanıma modeli yükleniyor";
    if (disabled && !isActive) return "Metin yanıtı devam ediyor";
    if (isActive) return "Serbest konuşma modunu kapat";
    return "Serbest konuşma modunu başlat";
  };

  const getTitle = () => {
    if (isVADErrored) return "Ses tanıma modeli yüklenemedi — sayfayı yenileyin";
    if (isVADLoading) return "Ses tanıma modeli yükleniyor...";
    if (disabled) return undefined;
    if (isActive) return "Serbest konuşma modunu kapatın";
    return "Serbest konuşma modunu başlatın";
  };

  const getStyles = () => {
    if (isVADErrored && !isActive) {
      return "text-red-400 bg-card border border-red-200 dark:border-red-800 cursor-pointer";
    }
    if (isVADLoading && !isActive) {
      return "text-muted-foreground bg-card border border-border cursor-wait";
    }
    if (disabled && !isActive) {
      return "text-muted-foreground/50 bg-card border border-border opacity-50 cursor-not-allowed";
    }
    if (isActive) {
      return "text-white bg-umay-blue ring-2 ring-umay-blue/30 cursor-pointer";
    }
    return "text-muted-foreground bg-card border border-border hover:text-foreground hover:bg-muted cursor-pointer";
  };

  return (
    <button
      type="button"
      onClick={!disabled || isActive ? onToggle : undefined}
      disabled={disabled && !isActive}
      aria-label={getAriaLabel()}
      aria-pressed={isActive}
      title={getTitle()}
      className={`h-12 w-12 rounded-xl flex items-center justify-center shrink-0 transition-all ${getStyles()}`}
    >
      {getIcon()}
    </button>
  );
}
