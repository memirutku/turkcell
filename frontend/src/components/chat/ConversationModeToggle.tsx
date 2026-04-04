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
    if (isVADErrored) return "Ses tanima modeli yuklenemedi";
    if (isVADLoading) return "Ses tanima modeli yukleniyor";
    if (disabled && !isActive) return "Metin yaniti devam ediyor";
    if (isActive) return "Serbest konusma modunu kapat";
    return "Serbest konusma modunu baslat";
  };

  const getTitle = () => {
    if (isVADErrored) return "Ses tanima modeli yuklenemedi — sayfayi yenileyin";
    if (isVADLoading) return "Ses tanima modeli yukleniyor...";
    if (disabled) return undefined;
    if (isActive) return "Serbest konusma modunu kapatin";
    return "Serbest konusma modunu baslatin";
  };

  const getStyles = () => {
    if (isVADErrored && !isActive) {
      return "text-red-400 bg-white border border-red-200 cursor-pointer";
    }
    if (isVADLoading && !isActive) {
      return "text-gray-400 bg-white border border-gray-200 cursor-wait";
    }
    if (disabled && !isActive) {
      return "text-gray-300 bg-white border border-gray-200 opacity-50 cursor-not-allowed";
    }
    if (isActive) {
      return "text-white bg-turkcell-blue ring-2 ring-turkcell-blue/30 cursor-pointer";
    }
    return "text-gray-500 bg-white border border-gray-200 hover:text-gray-700 hover:bg-gray-50 hover:border-gray-300 cursor-pointer";
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
