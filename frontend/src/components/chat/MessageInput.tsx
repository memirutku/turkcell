"use client";
import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { useChatStore } from "@/stores/chatStore";
import { Send, Loader2, Volume2, Radio } from "lucide-react";
import { useVoiceChat } from "@/hooks/useVoiceChat";
import { useVoiceConversation } from "@/hooks/useVoiceConversation";
import { useVoiceLive } from "@/hooks/useVoiceLive";
import { VoiceButton } from "./VoiceButton";
import { AudioWaveform } from "./AudioWaveform";
import { VoiceStatusBanner } from "./VoiceStatusBanner";
import { ConversationModeToggle } from "./ConversationModeToggle";
import { ConversationState, LiveConversationState, VoiceState } from "@/types";

const IS_LIVE_API = process.env.NEXT_PUBLIC_VOICE_LIVE_ENABLED === "true";

interface VoiceChatProps {
  voiceState: VoiceState;
  startRecording: () => void;
  stopRecording: () => void;
  isVoiceSupported: boolean;
  mediaRecorder: MediaRecorder | null;
}

interface ConversationProps {
  conversationState: ConversationState | LiveConversationState;
  startConversation: () => void;
  stopConversation: () => void;
  isVADLoading: boolean;
  isVADErrored: boolean | string;
}

function ConversationStatusArea({ conversationState }: { conversationState: ConversationState | LiveConversationState }) {
  const getStyles = () => {
    switch (conversationState) {
      case "listening":
      case "connected":
        return "border-turkcell-blue/20 bg-turkcell-blue/5";
      case "speech-detected":
        return "border-green-200 bg-green-50";
      case "connecting":
      case "processing":
      case "playing":
      case "model-speaking":
      case "action-pending":
      default:
        return "border-gray-200 bg-white";
    }
  };

  const getContent = () => {
    switch (conversationState) {
      case "listening":
        return (
          <>
            <span className="w-2 h-2 rounded-full bg-turkcell-blue animate-breathing shrink-0" />
            <span className="text-sm text-turkcell-blue">Konusmanizi bekliyorum...</span>
          </>
        );
      case "connected":
        return (
          <>
            <Radio className="h-4 w-4 text-turkcell-blue animate-pulse shrink-0" />
            <span className="text-sm text-turkcell-blue">Canli konusma aktif — konusabilirsiniz</span>
          </>
        );
      case "connecting":
        return (
          <>
            <Loader2 className="h-4 w-4 text-turkcell-blue animate-spin shrink-0" />
            <span className="text-sm text-gray-500">Baglanti kuruluyor...</span>
          </>
        );
      case "speech-detected":
        return (
          <>
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse shrink-0" />
            <span className="text-sm text-green-700">Dinleniyor...</span>
          </>
        );
      case "processing":
        return (
          <>
            <Loader2 className="h-4 w-4 text-turkcell-blue animate-spin shrink-0" />
            <span className="text-sm text-gray-500">Yanitiniz hazirlaniyor...</span>
          </>
        );
      case "playing":
      case "model-speaking":
        return (
          <>
            <Volume2 className="h-4 w-4 text-turkcell-blue animate-pulse shrink-0" />
            <span className="text-sm text-gray-500">Yanit okunuyor...</span>
          </>
        );
      case "action-pending":
        return (
          <>
            <Loader2 className="h-4 w-4 text-yellow-500 animate-spin shrink-0" />
            <span className="text-sm text-yellow-700">Islem onayiniz bekleniyor...</span>
          </>
        );
      default:
        return null;
    }
  };

  return (
    <div className={`flex items-center gap-2 flex-1 rounded-xl border px-4 py-3 ${getStyles()}`}>
      {getContent()}
    </div>
  );
}

function MessageInputInner({ voiceChat, conversation }: { voiceChat: VoiceChatProps; conversation: ConversationProps }) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const isStreaming = useChatStore((s) => s.isStreaming);

  const { voiceState, startRecording, stopRecording, isVoiceSupported, mediaRecorder } = voiceChat;
  const { conversationState, startConversation, stopConversation, isVADLoading, isVADErrored } = conversation;

  const isVoiceActive = voiceState !== "idle";
  const isConversationActive = conversationState !== "off";

  const canSend = input.trim().length > 0 && !isStreaming;

  const handleSend = () => {
    if (!canSend) return;
    sendMessage(input.trim());
    setInput("");
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleVoiceClick = () => {
    if (voiceState === "idle") {
      startRecording();
    } else if (voiceState === "recording") {
      stopRecording();
    }
  };

  const handleConversationToggle = () => {
    if (isConversationActive) {
      stopConversation();
      useChatStore.getState().announce("Sesli konusma modu kapatildi.");
    } else {
      if (isVADErrored) {
        useChatStore.getState().setError(
          "Ses tanima modeli yuklenemedi. Sayfayi yenileyip tekrar deneyin."
        );
        return;
      }
      if (isVADLoading) {
        useChatStore.getState().setError(
          "Ses tanima modeli yukleniyor, lutfen birka\u00e7 saniye bekleyin."
        );
        return;
      }
      startConversation();
      useChatStore.getState().announce("Sesli konusma modu aktif.");
    }
  };

  // Auto-grow textarea up to 4 lines
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      const lineHeight = 20; // ~14px font * 1.5 line-height
      const maxHeight = lineHeight * 4;
      textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
    }
  }, [input]);

  // Auto-focus on mount and after sending
  useEffect(() => {
    if (!isStreaming && !isVoiceActive && !isConversationActive) {
      textareaRef.current?.focus();
    }
  }, [isStreaming, isVoiceActive, isConversationActive]);

  return (
    <div className="p-4 bg-white border-t border-gray-200 shrink-0" role="region" aria-label="Mesaj gonderme alani">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-2">
          {voiceState === "recording" ? (
            <AudioWaveform mediaRecorder={mediaRecorder} />
          ) : isConversationActive ? (
            <ConversationStatusArea conversationState={conversationState} />
          ) : isVoiceActive ? (
            <div className="flex-1 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-500 opacity-50">
              Mesajinizi yazin...
            </div>
          ) : (
            <textarea
              id="message-input"
              name="message"
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Mesajinizi yazin..."
              disabled={isStreaming}
              rows={1}
              aria-label="Mesaj alani"
              aria-describedby="input-hint"
              aria-disabled={isStreaming}
              className="flex-1 resize-none rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm text-turkcell-dark placeholder:text-gray-500 focus:outline-none focus:border-turkcell-blue transition-colors disabled:opacity-50"
            />
          )}
          <ConversationModeToggle
            conversationState={conversationState}
            onToggle={handleConversationToggle}
            disabled={isStreaming || voiceState === "recording"}
            isVADLoading={isVADLoading}
            isVADErrored={!!isVADErrored}
          />
          <VoiceButton
            voiceState={voiceState}
            onClick={handleVoiceClick}
            disabled={isStreaming || isConversationActive}
            isVoiceSupported={isVoiceSupported}
            conversationActive={isConversationActive}
          />
          <button
            onClick={handleSend}
            disabled={!canSend || isVoiceActive || isConversationActive}
            aria-label="Mesaj gonder"
            aria-disabled={!canSend || isVoiceActive || isConversationActive}
            className="h-12 w-12 rounded-xl bg-turkcell-blue text-white flex items-center justify-center hover:bg-turkcell-blue/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
          >
            <Send className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
        <VoiceStatusBanner voiceState={voiceState} conversationState={conversationState} />
      </div>
      <p id="input-hint" className="sr-only">
        Gondermek icin Enter, yeni satir icin Shift+Enter tuslayiniz
      </p>
    </div>
  );
}

function LiveMessageInput() {
  const voiceChat = useVoiceChat();
  const conversation = useVoiceLive();
  return <MessageInputInner voiceChat={voiceChat} conversation={conversation} />;
}

function LegacyMessageInput() {
  const voiceChat = useVoiceChat();
  const conversation = useVoiceConversation();
  return <MessageInputInner voiceChat={voiceChat} conversation={conversation} />;
}

export function MessageInput() {
  return IS_LIVE_API ? <LiveMessageInput /> : <LegacyMessageInput />;
}
