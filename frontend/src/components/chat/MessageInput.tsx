"use client";
import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { useChatStore } from "@/stores/chatStore";
import { Send, Loader2, Volume2 } from "lucide-react";
import { useVoiceChat } from "@/hooks/useVoiceChat";
import { useVoiceConversation } from "@/hooks/useVoiceConversation";
import { VoiceButton } from "./VoiceButton";
import { AudioWaveform } from "./AudioWaveform";
import { VoiceStatusBanner } from "./VoiceStatusBanner";
import { ConversationModeToggle } from "./ConversationModeToggle";
import { ConversationState } from "@/types";

function ConversationStatusArea({ conversationState }: { conversationState: ConversationState }) {
  const getStyles = () => {
    switch (conversationState) {
      case "listening":
        return "border-turkcell-blue/20 bg-turkcell-blue/5";
      case "speech-detected":
        return "border-green-200 bg-green-50";
      case "processing":
      case "playing":
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
        return (
          <>
            <Volume2 className="h-4 w-4 text-turkcell-blue animate-pulse shrink-0" />
            <span className="text-sm text-gray-500">Yanit okunuyor...</span>
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

export function MessageInput() {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const isStreaming = useChatStore((s) => s.isStreaming);

  const { voiceState, startRecording, stopRecording, isVoiceSupported, mediaRecorder } = useVoiceChat();
  const { conversationState, startConversation, stopConversation } = useVoiceConversation();

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
    } else {
      startConversation();
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
        {/* Screen reader announcement for conversation mode changes */}
        <div className="sr-only" aria-live="assertive">
          {isConversationActive ? "Serbest konusma modu aktif" : ""}
        </div>
      </div>
      <p id="input-hint" className="sr-only">
        Gondermek icin Enter, yeni satir icin Shift+Enter tuslayiniz
      </p>
    </div>
  );
}
