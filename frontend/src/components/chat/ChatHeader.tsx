"use client";
import { useChatStore } from "@/stores/chatStore";
import { CustomerSelector } from "./CustomerSelector";
import { ThemeToggle } from "./ThemeToggle";
import { Plus } from "lucide-react";

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
      className="h-14 bg-card border-b border-border flex items-center justify-between px-4 shrink-0"
      role="banner"
      aria-label="Umay Umay başlık"
    >
      <div className="flex items-center gap-3">
        <img src="/umay-logo.gif" alt="Umay" className="h-8 w-auto object-contain" />
        <h1 className="text-xl text-foreground">
          <span className="font-normal">Umay</span>{" "}
          <span className="font-bold">Umay</span>
        </h1>
      </div>
      <nav className="flex items-center gap-2" aria-label="Sohbet işlemleri">
        <CustomerSelector />
        <ThemeToggle />
        <button
          onClick={handleNewChat}
          className="flex items-center gap-1.5 text-sm text-primary hover:text-primary/80 transition-colors font-medium rounded-md px-2 py-1"
          aria-label="Yeni sohbet başlat"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          <span className="hidden sm:inline">Yeni Sohbet</span>
        </button>
      </nav>
    </header>
  );
}
