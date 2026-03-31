"use client";
import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { useChatStore } from "@/stores/chatStore";
import { Send } from "lucide-react";
import { useVoiceChat } from "@/hooks/useVoiceChat";
import { VoiceButton } from "./VoiceButton";
import { AudioWaveform } from "./AudioWaveform";
import { VoiceStatusBanner } from "./VoiceStatusBanner";

export function MessageInput() {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const isStreaming = useChatStore((s) => s.isStreaming);

  const { voiceState, startRecording, stopRecording, isVoiceSupported, mediaRecorder } = useVoiceChat();
  const isVoiceActive = voiceState !== "idle";

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
    if (!isStreaming && !isVoiceActive) {
      textareaRef.current?.focus();
    }
  }, [isStreaming, isVoiceActive]);

  return (
    <div className="p-4 bg-white border-t border-gray-200 shrink-0">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-2">
          {voiceState === "recording" ? (
            <AudioWaveform mediaRecorder={mediaRecorder} />
          ) : isVoiceActive ? (
            <div className="flex-1 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-400 opacity-50">
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
              className="flex-1 resize-none rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm text-turkcell-dark placeholder:text-gray-400 focus:outline-none focus:border-turkcell-blue transition-colors disabled:opacity-50"
            />
          )}
          <VoiceButton
            voiceState={voiceState}
            onClick={handleVoiceClick}
            disabled={isStreaming}
            isVoiceSupported={isVoiceSupported}
          />
          <button
            onClick={handleSend}
            disabled={!canSend || isVoiceActive}
            aria-label="Mesaj Gonder"
            className="h-12 w-12 rounded-xl bg-turkcell-blue text-white flex items-center justify-center hover:bg-turkcell-blue/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
        <VoiceStatusBanner voiceState={voiceState} />
      </div>
    </div>
  );
}
