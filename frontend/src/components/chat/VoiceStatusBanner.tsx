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
            <span className="text-xs text-muted-foreground">Kayıt yapılıyor — durdurmak için tekrar tıklayın</span>
          </>
        );
      case "processing":
        return (
          <>
            <Loader2 className="h-3.5 w-3.5 text-umay-blue animate-spin" />
            <span className="text-xs text-muted-foreground">Sesiniz işleniyor...</span>
          </>
        );
      case "playing":
        return (
          <>
            <Volume2 className="h-3.5 w-3.5 text-umay-blue animate-pulse" />
            <span className="text-xs text-muted-foreground">Sesli yanıt oynatılıyor...</span>
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
          <span className="w-2 h-2 rounded-full bg-umay-blue animate-breathing" />
          <span className="text-xs text-muted-foreground">Konuşmanızı bekliyorum...</span>
        </>
      );
    case "connected":
      return (
        <>
          <Radio className="h-3.5 w-3.5 text-umay-blue animate-pulse" />
          <span className="text-xs text-muted-foreground">Canlı konuşma aktif</span>
        </>
      );
    case "connecting":
      return (
        <>
          <Loader2 className="h-3.5 w-3.5 text-umay-blue animate-spin" />
          <span className="text-xs text-muted-foreground">Bağlantı kuruluyor...</span>
        </>
      );
    case "speech-detected":
      return (
        <>
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-xs text-muted-foreground">Dinleniyor...</span>
          <SilenceIndicator />
        </>
      );
    case "processing":
      return (
        <>
          <Loader2 className="h-3.5 w-3.5 text-umay-blue animate-spin" />
          <span className="text-xs text-muted-foreground">Yanıtınız hazırlanıyor...</span>
        </>
      );
    case "playing":
    case "model-speaking":
      return (
        <>
          <Volume2 className="h-3.5 w-3.5 text-umay-blue animate-pulse" />
          <span className="text-xs text-muted-foreground">Yanıt okunuyor...</span>
        </>
      );
    case "action-pending":
      return (
        <>
          <Loader2 className="h-3.5 w-3.5 text-yellow-500 animate-spin" />
          <span className="text-xs text-yellow-700">İşlem onayınız bekleniyor</span>
        </>
      );
    default:
      return null;
  }
}
