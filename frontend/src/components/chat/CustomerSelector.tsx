"use client";
import { useEffect } from "react";
import { useChatStore } from "@/stores/chatStore";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectSeparator,
  SelectTrigger,
} from "@/components/ui/select";
import { CustomerOption } from "@/types";

const DEMO_CUSTOMERS: CustomerOption[] = [
  { id: "cust-001", name: "Ahmet Y.", tariff: "Platinum 20GB" },
  { id: "cust-002", name: "Elif D.", tariff: "Silver 5GB" },
  { id: "cust-003", name: "Mehmet K.", tariff: "Dijital Hayat 15GB" },
];

const GENERAL_CHAT_VALUE = "__general__";

export function CustomerSelector() {
  const customerId = useChatStore((s) => s.customerId);
  const setCustomerId = useChatStore((s) => s.setCustomerId);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const customerTariffs = useChatStore((s) => s.customerTariffs);
  const refreshCustomerTariff = useChatStore((s) => s.refreshCustomerTariff);

  useEffect(() => {
    if (customerId) {
      refreshCustomerTariff(customerId);
    }
  }, [customerId, refreshCustomerTariff]);

  const handleValueChange = (value: string | null) => {
    if (value === GENERAL_CHAT_VALUE) {
      setCustomerId(null);
    } else if (value) {
      setCustomerId(value);
    }
  };

  const selectedCustomer = DEMO_CUSTOMERS.find((c) => c.id === customerId);
  const selectValue = customerId ?? GENERAL_CHAT_VALUE;

  return (
    <Select
      value={selectValue}
      onValueChange={handleValueChange}
      disabled={isStreaming}
    >
      <SelectTrigger
        className="min-w-[200px] max-w-[280px] h-9 px-2 gap-2 sm:min-w-[200px] min-w-[140px]"
        aria-label="Müşteri seçin"
        aria-haspopup="listbox"
      >
        <div className="flex items-center gap-2 truncate">
          {selectedCustomer ? (
            <>
              <div className="h-6 w-6 rounded-full bg-umay-blue/10 text-umay-blue text-xs font-bold flex items-center justify-center shrink-0">
                {selectedCustomer.name.charAt(0)}
              </div>
              <span className="text-sm font-semibold truncate">
                {selectedCustomer.name}
              </span>
              <span className="text-xs text-muted-foreground truncate hidden sm:inline">
                - {customerTariffs[selectedCustomer.id] || selectedCustomer.tariff}
              </span>
            </>
          ) : (
            <>
              <div className="h-6 w-6 rounded-full bg-muted text-muted-foreground text-xs font-bold flex items-center justify-center shrink-0">
                ~
              </div>
              <span className="text-sm font-semibold">Genel Sohbet</span>
            </>
          )}
        </div>
      </SelectTrigger>
      <SelectContent className="max-w-[300px]">
        {DEMO_CUSTOMERS.map((customer) => (
          <SelectItem key={customer.id} value={customer.id} className="h-9">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-full bg-umay-blue/10 text-umay-blue text-xs font-bold flex items-center justify-center shrink-0">
                {customer.name.charAt(0)}
              </div>
              <span className="text-sm font-semibold">{customer.name}</span>
              <span className="text-xs text-muted-foreground">- {customerTariffs[customer.id] || customer.tariff}</span>
            </div>
          </SelectItem>
        ))}
        <SelectSeparator className="my-1" />
        <SelectItem value={GENERAL_CHAT_VALUE} className="h-9">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-full bg-muted text-muted-foreground text-xs font-bold flex items-center justify-center shrink-0">
              ~
            </div>
            <span className="text-sm font-semibold">Genel Sohbet</span>
          </div>
        </SelectItem>
      </SelectContent>
    </Select>
  );
}
