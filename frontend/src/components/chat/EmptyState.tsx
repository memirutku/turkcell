"use client";
import { useChatStore } from "@/stores/chatStore";
import { Receipt, Smartphone, HelpCircle, BarChart3 } from "lucide-react";
import type { LucideIcon } from "lucide-react";

const CUSTOMER_NAMES: Record<string, string> = {
  "cust-001": "Ahmet",
  "cust-002": "Elif",
  "cust-003": "Mehmet",
};

interface Suggestion {
  icon: LucideIcon;
  text: string;
  message: string;
}

const CUSTOMER_SUGGESTIONS: Suggestion[] = [
  { icon: Receipt, text: "Faturamı gör", message: "Faturamı görmek istiyorum" },
  { icon: Smartphone, text: "Tarifemi değiştir", message: "Tarifemi değiştirmek istiyorum" },
  { icon: BarChart3, text: "Kullanım detaylarım", message: "Kullanım detaylarımı göster" },
  { icon: HelpCircle, text: "Paket önerileri", message: "Bana uygun paket önerir misin?" },
];

const GENERAL_SUGGESTIONS: Suggestion[] = [
  { icon: Smartphone, text: "Umay tarifeleri", message: "Umay tarifeleri hakkında bilgi verir misin?" },
  { icon: HelpCircle, text: "Teknik destek", message: "Teknik destek almak istiyorum" },
  { icon: Receipt, text: "Fatura sorgulama", message: "Fatura sorgulama hakkında bilgi ver" },
  { icon: BarChart3, text: "Paket karşılaştırma", message: "Paketleri karşılaştırmak istiyorum" },
];

export function EmptyState() {
  const customerId = useChatStore((s) => s.customerId);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const customerName = customerId ? CUSTOMER_NAMES[customerId] : null;
  const suggestions = customerId ? CUSTOMER_SUGGESTIONS : GENERAL_SUGGESTIONS;

  return (
    <div
      className="flex flex-col items-center justify-center h-full text-center px-8 animate-in fade-in duration-500"
      role="status"
      aria-label="Sohbet başlangıcı"
    >
      {/* Animated logo */}
      <div className="relative mb-6">
        <img src="/umay-amblem.png" alt="Umay" className="h-20 w-auto object-contain drop-shadow-lg" />
      </div>

      {/* Greeting */}
      <p className="text-sm text-muted-foreground mb-1">Hoşgeldiniz</p>
      <h2 className="text-2xl font-bold text-foreground mb-2">
        {customerName
          ? `Merhaba! ${customerName} hesabı hakkında soru sorabilirsiniz.`
          : "Merhaba! Size nasıl yardımcı olabilirim?"}
      </h2>
      <p className="text-sm text-muted-foreground max-w-md mb-8">
        {customerName
          ? "Fatura detayları, tarife bilgisi ve kullanım durumu hakkında sorularınızı yazabilirsiniz."
          : "Fatura, tarife, paket ve teknik destek konularında sorularınızı yazabilirsiniz."}
      </p>

      {/* Suggestion cards */}
      <div
        className="grid grid-cols-2 gap-3 w-full max-w-md"
        role="group"
        aria-label="Önerilen sorular"
      >
        {suggestions.map((suggestion) => {
          const Icon = suggestion.icon;
          return (
            <button
              key={suggestion.text}
              onClick={() => sendMessage(suggestion.message)}
              className="flex items-center gap-3 bg-card border border-border rounded-xl px-4 py-3 text-left hover:bg-muted transition-colors group"
              aria-label={suggestion.text}
            >
              <Icon className="h-5 w-5 text-umay-blue shrink-0 group-hover:scale-110 transition-transform" aria-hidden="true" />
              <span className="text-sm text-foreground">{suggestion.text}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
