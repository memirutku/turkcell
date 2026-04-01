"use client";
import { useChatStore } from "@/stores/chatStore";
import { CustomerSelector } from "./CustomerSelector";

export function ChatHeader() {
  const resetSession = useChatStore((s) => s.resetSession);
  const messagesCount = useChatStore((s) => s.messages.length);

  const handleNewChat = () => {
    if (messagesCount > 0) {
      const confirmed = window.confirm("Mevcut sohbet silinecek. Devam etmek istiyor musunuz?");
      if (!confirmed) return;
    }
    resetSession();
  };

  return (
    <header
      className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4 shrink-0"
      role="banner"
      aria-label="Turkcell Asistan baslik"
    >
      <div className="flex items-center gap-3">
        <div
          className="h-8 w-8 rounded-full bg-turkcell-yellow flex items-center justify-center text-sm font-bold text-turkcell-dark"
          aria-hidden="true"
        >
          T
        </div>
        <h1 className="text-xl font-semibold text-turkcell-dark">Turkcell Asistan</h1>
      </div>
      <nav className="flex items-center gap-3" aria-label="Sohbet islemleri">
        <CustomerSelector />
        <button
          onClick={handleNewChat}
          className="text-sm text-turkcell-blue hover:text-turkcell-blue/80 transition-colors font-medium rounded-md px-2 py-1"
          aria-label="Yeni sohbet baslat"
        >
          Yeni Sohbet
        </button>
      </nav>
    </header>
  );
}
