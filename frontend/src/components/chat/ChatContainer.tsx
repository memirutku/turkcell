"use client";
import { useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { ChatHeader } from "./ChatHeader";
import { MessageBubble } from "./MessageBubble";
import { MessageInput } from "./MessageInput";
import { TypingIndicator } from "./TypingIndicator";
import { EmptyState } from "./EmptyState";
import { ErrorBanner } from "./ErrorBanner";

export function ChatContainer() {
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Show typing indicator: streaming is true AND either no messages yet or last assistant message is empty
  const showTypingIndicator = isStreaming && (
    messages.length === 0 ||
    (messages[messages.length - 1]?.role === "assistant" && messages[messages.length - 1]?.content === "")
  );

  return (
    <div className="flex flex-col h-screen bg-turkcell-gray">
      <ChatHeader />

      {/* Message area */}
      <main
        id="main-content"
        className="flex-1 overflow-y-auto"
        role="log"
        aria-live="polite"
        aria-label="Sohbet mesajlari"
        tabIndex={-1}
      >
        <div className="max-w-3xl mx-auto px-4 sm:px-8 py-6">
          {messages.length === 0 && !isStreaming ? (
            <EmptyState />
          ) : (
            <div className="flex flex-col gap-6">
              {messages.map((msg) =>
                msg.content || msg.role === "user" ? (
                  <MessageBubble key={msg.id} message={msg} />
                ) : null
              )}
              {showTypingIndicator && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </main>

      {/* Error banner */}
      <ErrorBanner />

      {/* Input area */}
      <MessageInput />
    </div>
  );
}
