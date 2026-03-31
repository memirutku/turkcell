"use client";
import { Message } from "@/types";
import { MarkdownRenderer } from "./MarkdownRenderer";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 items-start ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div className={`h-8 w-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${
        isUser
          ? "bg-turkcell-blue text-white"
          : "bg-turkcell-yellow text-turkcell-dark"
      }`}>
        {isUser ? "S" : "T"}
      </div>

      {/* Bubble */}
      <div className={`max-w-[80%] sm:max-w-[80%] md:max-w-[75%] rounded-2xl px-4 py-2 ${
        isUser
          ? "bg-turkcell-blue text-white rounded-tr-sm"
          : "bg-white border border-gray-200 text-turkcell-dark rounded-tl-sm"
      }`}>
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        ) : (
          <>
            <MarkdownRenderer content={message.content} />
            {message.isStreaming && (
              <span className="inline-block w-0.5 h-4 bg-turkcell-blue animate-pulse ml-1 align-middle" />
            )}
          </>
        )}
      </div>
    </div>
  );
}
