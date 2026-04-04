"use client";
import { VoiceState, ConversationState, LiveConversationState } from "@/types";
import { Loader2, Volume2, Radio } from "lucide-react";
import { SilenceIndicator } from "./SilenceIndicator";

interface VoiceStatusBannerProps {
  voiceState: VoiceState;
  conversationState?: ConversationState | LiveConversationState;
}

export function VoiceStatusBanner({ voiceState, conversationState }: VoiceStatusBannerProps) {
  // Conversation mode states take priority over push-to-talk states
  if (conversationState && conversationState !== "off") {
    return (
      <div className="flex items-center gap-2 mt-1" role="status" aria-live="polite">
        {getConversationContent(conversationState)}
      </div>
    );
  }

  if (voiceState === "idle") return null;

  const getContent = () => {
    switch (voiceState) {
      case "recording":
        return (
          <>
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-xs text-gray-500">Kayit yapiliyor — durdurmak icin tekrar tiklayin</span>
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

function getConversationContent(state: ConversationState | LiveConversationState) {
  switch (state) {
    case "listening":
      return (
        <>
          <span className="w-2 h-2 rounded-full bg-turkcell-blue animate-breathing" />
          <span className="text-xs text-gray-500">Konusmanizi bekliyorum...</span>
        </>
      );
    case "connected":
      return (
        <>
          <Radio className="h-3.5 w-3.5 text-turkcell-blue animate-pulse" />
          <span className="text-xs text-gray-500">Canli konusma aktif</span>
        </>
      );
    case "connecting":
      return (
        <>
          <Loader2 className="h-3.5 w-3.5 text-turkcell-blue animate-spin" />
          <span className="text-xs text-gray-500">Baglanti kuruluyor...</span>
        </>
      );
    case "speech-detected":
      return (
        <>
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-xs text-gray-500">Dinleniyor...</span>
          <SilenceIndicator />
        </>
      );
    case "processing":
      return (
        <>
          <Loader2 className="h-3.5 w-3.5 text-turkcell-blue animate-spin" />
          <span className="text-xs text-gray-500">Yanitiniz hazirlaniyor...</span>
        </>
      );
    case "playing":
    case "model-speaking":
      return (
        <>
          <Volume2 className="h-3.5 w-3.5 text-turkcell-blue animate-pulse" />
          <span className="text-xs text-gray-500">Yanit okunuyor...</span>
        </>
      );
    case "action-pending":
      return (
        <>
          <Loader2 className="h-3.5 w-3.5 text-yellow-500 animate-spin" />
          <span className="text-xs text-yellow-700">Islem onayiniz bekleniyor</span>
        </>
      );
    default:
      return null;
  }
}
