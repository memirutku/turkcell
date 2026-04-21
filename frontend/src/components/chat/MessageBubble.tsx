"use client";
import { Message } from "@/types";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { StructuredContent } from "./StructuredContent";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const senderLabel = isUser ? "Siz" : "Umay Umay";
  const timeStr = new Date(message.timestamp).toLocaleTimeString("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <article
      id={`msg-${message.id}`}
      tabIndex={-1}
      className={`flex ${isUser ? "flex-row-reverse items-start gap-3" : "flex-col gap-0"}`}
      role="article"
      aria-label={`${senderLabel}, ${timeStr}`}
    >
      <div className={`flex gap-3 items-start ${isUser ? "flex-row-reverse" : "flex-row"}`}>
        {/* Avatar */}
        <div
          className={`h-8 w-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${
            isUser
              ? "bg-umay-blue text-white"
              : "bg-umay-yellow text-umay-dark"
          }`}
          aria-hidden="true"
        >
          {isUser ? "S" : "U"}
        </div>

        {/* Bubble */}
        <div className={`max-w-[80%] sm:max-w-[80%] md:max-w-[75%] rounded-2xl px-4 py-2 ${
          isUser
            ? "bg-umay-blue text-white rounded-tr-sm"
            : "bg-card border border-border text-foreground rounded-tl-sm"
        }`}>
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          ) : (
            <>
              <MarkdownRenderer content={message.content} />
              {message.isStreaming && (
                <span
                  className="inline-block w-0.5 h-4 bg-umay-blue animate-pulse ml-1 align-middle"
                  aria-hidden="true"
                />
              )}
              {/* Phase 7: TTS indicator placeholder -- activate when wasSpoken tracking is added */}
            </>
          )}
        </div>
      </div>

      {/* Structured content below bubble, aligned with bubble text (ml-11 = 44px for avatar 32px + gap 12px) */}
      {!isUser && message.structuredData && message.structuredData.length > 0 && (
        <div className="ml-11 mt-4 max-w-[80%] sm:max-w-[80%] md:max-w-[75%]" aria-label="Detayli bilgi kartlari">
          {message.structuredData.map((data, i) => (
            <StructuredContent key={i} data={data} />
          ))}
        </div>
      )}
    </article>
  );
}
