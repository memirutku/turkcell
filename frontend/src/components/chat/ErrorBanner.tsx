"use client";
import { useEffect } from "react";
import { useChatStore } from "@/stores/chatStore";

export function ErrorBanner() {
  const error = useChatStore((s) => s.error);
  const setError = useChatStore((s) => s.setError);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const messages = useChatStore((s) => s.messages);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 10000);
      return () => clearTimeout(timer);
    }
  }, [error, setError]);

  if (!error) return null;

  const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");

  return (
    <div
      className="mx-4 mb-2 px-4 py-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-xl flex items-center justify-between"
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      <span className="text-sm text-red-800 dark:text-red-300">{error}</span>
      {lastUserMsg && (
        <button
          onClick={() => {
            setError(null);
            sendMessage(lastUserMsg.content);
          }}
          className="ml-3 px-3 py-1 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors shrink-0"
          aria-label="Son mesajı tekrar gönder"
        >
          Tekrar Dene
        </button>
      )}
    </div>
  );
}
