"use client";
import { useChatStore } from "@/stores/chatStore";

const CUSTOMER_NAMES: Record<string, string> = {
  "cust-001": "Ahmet",
  "cust-002": "Elif",
  "cust-003": "Mehmet",
};

export function EmptyState() {
  const customerId = useChatStore((s) => s.customerId);
  const customerName = customerId ? CUSTOMER_NAMES[customerId] : null;

  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-8">
      <div className="h-16 w-16 rounded-full bg-turkcell-yellow flex items-center justify-center text-2xl font-bold text-turkcell-dark mb-6">
        T
      </div>
      <h2 className="text-xl font-semibold text-turkcell-dark mb-2">
        {customerName
          ? `Merhaba! ${customerName} hesabi hakkinda soru sorabilirsiniz.`
          : "Merhaba! Size nasil yardimci olabilirim?"}
      </h2>
      <p className="text-sm text-gray-500 max-w-md">
        {customerName
          ? "Fatura detaylari, tarife bilgisi ve kullanim durumu hakkinda sorularinizi yazabilirsiniz."
          : "Fatura, tarife, paket ve teknik destek konularinda sorularinizi yazabilirsiniz."}
      </p>
    </div>
  );
}
