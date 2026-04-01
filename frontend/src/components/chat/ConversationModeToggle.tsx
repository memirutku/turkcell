"use client";
import { ConversationState } from "@/types";
import { MessageSquare, PhoneOff } from "lucide-react";

interface ConversationModeToggleProps {
  conversationState: ConversationState;
  onToggle: () => void;
  disabled: boolean;
}

export function ConversationModeToggle({
  conversationState,
  onToggle,
  disabled,
}: ConversationModeToggleProps) {
  const isActive = conversationState !== "off";

  const getIcon = () => {
    if (isActive) return <PhoneOff className="h-5 w-5" />;
    return <MessageSquare className="h-5 w-5" />;
  };

  const getAriaLabel = () => {
    if (disabled && !isActive) return "Metin yaniti devam ediyor";
    if (isActive) return "Serbest konusma modunu kapat";
    return "Serbest konusma modunu baslat";
  };

  const getTitle = () => {
    if (disabled) return undefined;
    if (isActive) return "Serbest konusma modunu kapatin";
    return "Serbest konusma modunu baslatin";
  };

  const getStyles = () => {
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
