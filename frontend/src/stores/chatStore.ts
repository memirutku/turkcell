import { create } from "zustand";
import { Message, StructuredData, ActionProposal, ActionResult, RecommendationPayload } from "@/types";
import { streamChat, streamAgentChat, confirmAgentAction, fetchCustomer } from "@/lib/api";

const SESSION_STORAGE_KEY = "umay-chat-session-id";

function getOrCreateSessionId(): string {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(SESSION_STORAGE_KEY);
    if (stored) return stored;
    const newId = crypto.randomUUID();
    localStorage.setItem(SESSION_STORAGE_KEY, newId);
    return newId;
  }
  return typeof crypto !== "undefined" ? crypto.randomUUID() : "default-session";
}

interface ChatStore {
  messages: Message[];
  isStreaming: boolean;
  sessionId: string;
  error: string | null;
  customerId: string | null;
  pendingAction: ActionProposal | null;
  isActionProcessing: boolean;
  activeThreadId: string | null;
  srAnnouncement: string;
  liveConfirmCallback: ((approved: boolean) => void) | null;
  customerTariffs: Record<string, string>;
  announce: (text: string) => void;
  refreshCustomerTariff: (customerId: string) => Promise<void>;
  addMessage: (role: "user" | "assistant", content: string) => string; // returns message id
  appendToLastMessage: (token: string) => void;
  setStreaming: (streaming: boolean) => void;
  setError: (error: string | null) => void;
  addStructuredData: (data: StructuredData) => void;
  setCustomerId: (id: string | null) => void;
  setPendingAction: (action: ActionProposal | null) => void;
  setActionProcessing: (processing: boolean) => void;
  setLiveConfirmCallback: (cb: ((approved: boolean) => void) | null) => void;
  confirmAction: (threadId: string, approved: boolean) => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  clearMessages: () => void;
  resetSession: () => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isStreaming: false,
  sessionId: getOrCreateSessionId(),
  error: null,
  customerId: "cust-001",
  pendingAction: null,
  isActionProcessing: false,
  activeThreadId: null,
  srAnnouncement: "",
  liveConfirmCallback: null,
  customerTariffs: {},

  refreshCustomerTariff: async (customerId) => {
    try {
      const customer = await fetchCustomer(customerId);
      if (customer.tariff?.name) {
        set((state) => ({
          customerTariffs: { ...state.customerTariffs, [customerId]: customer.tariff!.name },
        }));
      }
    } catch (err) {
      console.error("[ChatStore] refreshCustomerTariff error:", err);
    }
  },

  announce: (text) => {
    set({ srAnnouncement: text });
    setTimeout(() => set({ srAnnouncement: "" }), 1000);
  },

  addMessage: (role, content) => {
    const id = crypto.randomUUID();
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id,
          role,
          content,
          timestamp: Date.now(),
          isStreaming: role === "assistant",
        },
      ],
    }));
    return id;
  },

  appendToLastMessage: (token) =>
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content: last.content + token };
      }
      return { messages: msgs };
    }),

  addStructuredData: (data) => {
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        const existing = last.structuredData || [];
        msgs[msgs.length - 1] = {
          ...last,
          structuredData: [...existing, data],
        };
      }
      return { messages: msgs };
    });

    // Screen reader announcements for structured content
    if (data.type === "recommendation") {
      const payload = data.payload as RecommendationPayload;
      if (payload.recommendations && payload.recommendations.length > 0) {
        const top = payload.recommendations[0];
        setTimeout(() => {
          get().announce(
            `Tarife onerisi alindi: ${top.tariff_name}, aylik ${top.savings} TL tasarruf.`
          );
        }, 100);
      }
    }
  },

  setStreaming: (isStreaming) => set({ isStreaming }),

  setError: (error) => set({ error }),

  setCustomerId: (id) => {
    const newSessionId = crypto.randomUUID();
    if (typeof window !== "undefined") {
      localStorage.setItem(SESSION_STORAGE_KEY, newSessionId);
    }
    set({
      customerId: id,
      messages: [],
      error: null,
      sessionId: newSessionId,
      isStreaming: false,
      pendingAction: null,
      isActionProcessing: false,
      activeThreadId: null,
    });
    // Screen reader announcement for customer change
    const CUSTOMER_NAMES: Record<string, string> = {
      "cust-001": "Ahmet",
      "cust-002": "Elif",
      "cust-003": "Mehmet",
    };
    if (id) {
      const name = CUSTOMER_NAMES[id] || id;
      setTimeout(() => get().announce(`Musteri degistirildi: ${name}`), 100);
    }
  },

  setPendingAction: (action) => set({ pendingAction: action, activeThreadId: action?.thread_id || null }),

  setActionProcessing: (processing) => set({ isActionProcessing: processing }),

  setLiveConfirmCallback: (cb) => set({ liveConfirmCallback: cb }),

  confirmAction: async (threadId, approved) => {
    const { liveConfirmCallback } = get();

    // Live API mode: route confirmation through WebSocket
    if (liveConfirmCallback) {
      get().setPendingAction(null);
      liveConfirmCallback(approved);
      return;
    }

    // Legacy mode: REST API confirmation
    const { appendToLastMessage, setStreaming, setError, addStructuredData } = get();
    const setPendingAction = get().setPendingAction;
    const setActionProcessing = get().setActionProcessing;
    setActionProcessing(true);
    setPendingAction(null);

    if (!approved) {
      // For rejection, add a cancelled result to structured data
      addStructuredData({
        type: "action_result",
        payload: {
          success: false,
          action_type: "package_activation",
          description: "Islem iptal edildi",
          details: {},
        },
      });
    }

    // Add empty assistant message for the response
    const { addMessage } = get();
    addMessage("assistant", "");
    setStreaming(true);

    try {
      await confirmAgentAction(
        threadId,
        approved,
        (token) => appendToLastMessage(token),
        () => {
          set((state) => {
            const msgs = [...state.messages];
            const last = msgs[msgs.length - 1];
            if (last?.role === "assistant") {
              msgs[msgs.length - 1] = { ...last, isStreaming: false };
            }
            return { messages: msgs };
          });
          setStreaming(false);
          setActionProcessing(false);
        },
        (errorMsg) => {
          setError(errorMsg);
          setStreaming(false);
          setActionProcessing(false);
        },
        (result) => {
          addStructuredData({
            type: "action_result",
            payload: result,
          });
          if (result.success) {
            const cid = get().customerId;
            if (cid) get().refreshCustomerTariff(cid);
          }
        },
      );
    } catch (err) {
      console.error("[ChatStore] confirmAction error:", err);
      setError("Onay islemi sirasinda bir sorun olustu. Lutfen tekrar deneyin.");
      setStreaming(false);
      setActionProcessing(false);
    }
  },

  sendMessage: async (message) => {
    const { sessionId, customerId, addMessage, appendToLastMessage, setStreaming, setError } = get();
    setError(null);
    setStreaming(true);
    addMessage("user", message);
    addMessage("assistant", "");

    try {
      if (customerId) {
        // Route through agent endpoint when customer context is available
        await streamAgentChat(
          message,
          sessionId,
          customerId,
          (token) => appendToLastMessage(token),
          () => {
            set((state) => {
              const msgs = [...state.messages];
              const last = msgs[msgs.length - 1];
              if (last?.role === "assistant") {
                msgs[msgs.length - 1] = { ...last, isStreaming: false };
              }
              return { messages: msgs };
            });
            setStreaming(false);
          },
          (errorMsg) => {
            setError(errorMsg);
            setStreaming(false);
            set((state) => {
              const msgs = [...state.messages];
              const last = msgs[msgs.length - 1];
              if (last?.role === "assistant" && last.content === "") {
                msgs.pop();
              }
              return { messages: msgs };
            });
          },
          (proposal) => {
            // Action proposal received -- store it and add as structured data
            const { setPendingAction, addStructuredData } = get();
            setPendingAction(proposal);
            addStructuredData({
              type: "action_proposal",
              payload: proposal,
            });
          },
          (result) => {
            const { addStructuredData } = get();
            addStructuredData({
              type: "action_result",
              payload: result,
            });
            if (result.success) {
              const cid = get().customerId;
              if (cid) get().refreshCustomerTariff(cid);
            }
          },
          (structuredData) => {
            const { addStructuredData } = get();
            addStructuredData(structuredData);
          },
        );
      } else {
        // Standard chat endpoint for non-customer context
        await streamChat(
          message,
          sessionId,
          customerId,
          (token) => appendToLastMessage(token),
          () => {
            set((state) => {
              const msgs = [...state.messages];
              const last = msgs[msgs.length - 1];
              if (last?.role === "assistant") {
                msgs[msgs.length - 1] = { ...last, isStreaming: false };
              }
              return { messages: msgs };
            });
            setStreaming(false);
          },
          (errorMsg) => {
            setError(errorMsg);
            setStreaming(false);
            set((state) => {
              const msgs = [...state.messages];
              const last = msgs[msgs.length - 1];
              if (last?.role === "assistant" && last.content === "") {
                msgs.pop();
              }
              return { messages: msgs };
            });
          },
          (structuredData) => {
            const { addStructuredData } = get();
            addStructuredData(structuredData);
          },
        );
      }
    } catch (err) {
      console.error("[ChatStore] sendMessage error:", err);
      setError("Bir hata olustu. Lutfen tekrar deneyin.");
      setStreaming(false);
    }
  },

  clearMessages: () => set({ messages: [], error: null, pendingAction: null, isActionProcessing: false, activeThreadId: null }),

  resetSession: () => {
    const newId = crypto.randomUUID();
    if (typeof window !== "undefined") {
      localStorage.setItem(SESSION_STORAGE_KEY, newId);
    }
    set({
      messages: [],
      error: null,
      sessionId: newId,
      isStreaming: false,
      pendingAction: null,
      isActionProcessing: false,
      activeThreadId: null,
    });
  },
}));
