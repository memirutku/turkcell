"use client";
import { useState, useRef, useCallback, useEffect } from "react";
import { useMicVAD } from "@ricky0123/vad-react";
import { ConversationState, ActionProposal, ActionResult } from "@/types";
import { useChatStore } from "@/stores/chatStore";
import { float32ToWavBlob } from "@/lib/audioUtils";
import { checkMicrophoneSupport, checkSecureContext } from "@/lib/audioUtils";
import { VAD_CONFIG, POST_PLAYBACK_DELAY_MS } from "@/lib/vadConfig";
import { getWsBaseUrl } from "@/lib/api";

const MAX_RECONNECT_ATTEMPTS = 3;
const RECONNECT_DELAYS = [1000, 2000, 4000];

export function useVoiceConversation() {
  const [conversationState, setConversationState] = useState<ConversationState>("off");
  const conversationStateRef = useRef<ConversationState>("off");
  const wsRef = useRef<WebSocket | null>(null);
  const audioQueueRef = useRef<Blob[]>([]);
  const isPlayingRef = useRef(false);
  const isMountedRef = useRef(true);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isFirstTokenRef = useRef(true);
  const audioDoneReceivedRef = useRef(false);

  // Keep ref in sync with state for use in callbacks
  useEffect(() => {
    conversationStateRef.current = conversationState;
  }, [conversationState]);

  const vad = useMicVAD({
    startOnLoad: false,
    positiveSpeechThreshold: VAD_CONFIG.positiveSpeechThreshold,
    negativeSpeechThreshold: VAD_CONFIG.negativeSpeechThreshold,
    redemptionMs: VAD_CONFIG.redemptionMs,
    minSpeechMs: VAD_CONFIG.minSpeechMs,
    preSpeechPadMs: VAD_CONFIG.preSpeechPadMs,
    model: VAD_CONFIG.model,
    baseAssetPath: VAD_CONFIG.baseAssetPath,
    onnxWASMBasePath: VAD_CONFIG.onnxWASMBasePath,
    onSpeechStart: () => {
      if (isMountedRef.current && conversationStateRef.current !== "off") {
        setConversationState("speech-detected");
      }
    },
    onSpeechEnd: (audio: Float32Array) => {
      if (!isMountedRef.current) return;
      setConversationState("processing");
      const wavBlob = float32ToWavBlob(audio, 16000);
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(wavBlob);
      }
    },
    onVADMisfire: () => {
      // Speech too short (< minSpeechMs), stay listening
      if (isMountedRef.current && conversationStateRef.current !== "off") {
        setConversationState("listening");
      }
    },
  });

  // Keep vad in a ref so callbacks don't depend on the vad object identity
  const vadRef = useRef(vad);
  useEffect(() => {
    vadRef.current = vad;
  }, [vad]);

  // -- Audio playback queue --
  const playNextInQueue = useCallback(() => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      // If audio_done was already received and queue is empty, resume listening
      if (audioDoneReceivedRef.current && isMountedRef.current) {
        audioDoneReceivedRef.current = false;
        setTimeout(() => {
          if (isMountedRef.current && conversationStateRef.current !== "off") {
            vadRef.current.start();
            setConversationState("listening");
          }
        }, POST_PLAYBACK_DELAY_MS);
      }
      return;
    }

    isPlayingRef.current = true;
    const blob = audioQueueRef.current.shift()!;
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);

    audio.onended = () => {
      URL.revokeObjectURL(url);
      playNextInQueue();
    };

    audio.onerror = () => {
      URL.revokeObjectURL(url);
      playNextInQueue(); // Skip failed chunk
    };

    audio.play().catch(() => {
      URL.revokeObjectURL(url);
      playNextInQueue();
    });
  }, []);

  const enqueueAudio = useCallback((blob: Blob) => {
    audioQueueRef.current.push(blob);
    if (!isPlayingRef.current) {
      // Pause VAD when first audio arrives to prevent echo loop
      vadRef.current.pause();
      setConversationState("playing");
      playNextInQueue();
    }
  }, [playNextInQueue]);

  // -- WebSocket connection --
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = `${getWsBaseUrl()}/ws/voice`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      reconnectAttemptRef.current = 0;
      const initMsg = {
        type: "init",
        session_id: useChatStore.getState().sessionId,
        customer_id: useChatStore.getState().customerId,
      };
      ws.send(JSON.stringify(initMsg));
    };

    ws.onmessage = (event: MessageEvent) => {
      if (!isMountedRef.current) return;

      // Binary data = audio_chunk (sentence-level TTS)
      if (event.data instanceof Blob) {
        enqueueAudio(event.data);
        return;
      }

      // Text data = JSON control message
      try {
        const msg = JSON.parse(event.data);

        switch (msg.type) {
          case "transcription": {
            if (msg.text) {
              const store = useChatStore.getState();
              store.addMessage("user", msg.text);
              store.setStreaming(true);
              isFirstTokenRef.current = true;
            }
            break;
          }

          case "token": {
            if (msg.content !== undefined) {
              const store = useChatStore.getState();
              if (isFirstTokenRef.current) {
                store.addMessage("assistant", "");
                isFirstTokenRef.current = false;
              }
              store.appendToLastMessage(msg.content);
            }
            break;
          }

          case "response_end": {
            useChatStore.setState((state) => {
              const msgs = [...state.messages];
              const last = msgs[msgs.length - 1];
              if (last?.role === "assistant") {
                msgs[msgs.length - 1] = { ...last, isStreaming: false };
              }
              return { messages: msgs };
            });
            useChatStore.getState().setStreaming(false);
            break;
          }

          case "audio_done": {
            audioDoneReceivedRef.current = true;
            // If no audio was playing (TTS unavailable), resume listening
            if (!isPlayingRef.current && isMountedRef.current) {
              audioDoneReceivedRef.current = false;
              setTimeout(() => {
                if (isMountedRef.current && conversationStateRef.current !== "off") {
                  vadRef.current.start();
                  setConversationState("listening");
                }
              }, POST_PLAYBACK_DELAY_MS);
            }
            // If audio is playing, playNextInQueue handles the transition
            break;
          }

          case "error": {
            useChatStore.getState().setError(
              msg.message || "Bir hata olustu. Lutfen tekrar deneyin."
            );
            // On error, pause briefly then resume listening (don't exit conversation mode)
            setTimeout(() => {
              if (isMountedRef.current && conversationStateRef.current !== "off") {
                vadRef.current.start();
                setConversationState("listening");
              }
            }, 2000);
            break;
          }

          case "action_proposal": {
            const store = useChatStore.getState();
            const proposal: ActionProposal = {
              action_type: (msg.action_type as "package_activation" | "tariff_change") || "package_activation",
              description: msg.description || "",
              details: msg.details || {},
              thread_id: msg.thread_id || "",
            };
            store.setPendingAction(proposal);
            store.addStructuredData({
              type: "action_proposal",
              payload: proposal,
            });
            // Screen reader announcement per UI-SPEC
            const title = proposal.action_type === "package_activation"
              ? "Paket Tanimlama"
              : "Tarife Degisikligi";
            store.announce(
              `Islem onerisi: ${title}. ${proposal.description}. Onaylamak icin Evet Onayla butonunu, iptal etmek icin Vazgec butonunu kullanin.`
            );
            break;
          }

          case "action_result": {
            const store = useChatStore.getState();
            const result: ActionResult = {
              success: !!msg.success,
              action_type: (msg.action_type as "package_activation" | "tariff_change") || "package_activation",
              description: msg.description || "",
              details: msg.details || {},
            };
            store.addStructuredData({
              type: "action_result",
              payload: result,
            });
            // Clear pending action
            store.setPendingAction(null);
            // Screen reader announcement
            if (result.success) {
              store.announce(`Islem basarili: ${result.description}`);
            } else {
              store.announce(`Islem basarisiz: ${result.description}`);
            }
            break;
          }

          case "confirmation_prompt": {
            // TTS handles the audio playback for the prompt.
            // The text is for screen reader users who may not hear TTS.
            const store = useChatStore.getState();
            if (msg.text) {
              store.announce(msg.text);
            }
            break;
          }
        }
      } catch {
        // Ignore malformed JSON
      }
    };

    ws.onclose = () => {
      if (!isMountedRef.current) return;
      if (reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = RECONNECT_DELAYS[reconnectAttemptRef.current] || 4000;
        reconnectAttemptRef.current++;
        reconnectTimerRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            connectWebSocket();
          }
        }, delay);
      } else if (conversationStateRef.current !== "off") {
        // Failed to reconnect -- exit conversation mode
        useChatStore.getState().setError(
          "Ses baglantisi kurulamadi. Lutfen tekrar deneyin."
        );
        setConversationState("off");
      }
    };

    ws.onerror = () => {
      // onclose handles reconnection
    };

    wsRef.current = ws;
  }, [enqueueAudio]);

  // -- Public API --
  const startConversation = useCallback(async () => {
    const store = useChatStore.getState();

    if (!checkSecureContext()) {
      store.setError("Ses ozelligi yalnizca guvenli baglantilarda (HTTPS veya localhost) kullanilabilir.");
      return;
    }
    if (!checkMicrophoneSupport()) {
      store.setError("Tarayiciniz ses kaydini desteklemiyor. Lutfen guncel bir tarayici kullanin.");
      return;
    }

    // Ensure WebSocket is connected
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connectWebSocket();
      await new Promise<void>((resolve) => setTimeout(resolve, 500));
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        store.setError("Ses baglantisi kurulamadi. Lutfen tekrar deneyin.");
        return;
      }
    }

    setConversationState("listening");
    vadRef.current.start();
  }, [connectWebSocket]);

  const stopConversation = useCallback(() => {
    vadRef.current.pause();
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    audioDoneReceivedRef.current = false;
    setConversationState("off");
  }, []);

  // Track mount state and clean up on unmount
  useEffect(() => {
    isMountedRef.current = true;

    return () => {
      isMountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  return {
    conversationState,
    startConversation,
    stopConversation,
    isVADLoading: vad.loading,
    isVADErrored: vad.errored,
  };
}
