// Health check response from backend /api/health
export interface ServiceStatus {
  status: string;
  latency_ms?: number;
  error?: string;
  customers?: number;
  tariffs?: number;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  services: {
    redis: ServiceStatus;
    milvus: ServiceStatus;
    mock_bss: ServiceStatus;
  };
  timestamp: string;
}

// Mock BSS types (will be used in later phases, defined now for contract)
export interface Tariff {
  id: string;
  name: string;
  data_gb: number;
  voice_minutes: number;
  sms_count: number;
  monthly_price_tl: string;
  description: string;
  features: string[];
  is_active: boolean;
}

export interface Customer {
  id: string;
  name: string;
  phone_number: string;
  email: string;
  tariff_id: string;
  address_city: string;
  tariff?: Tariff;
}

// Chat types (Phase 3)
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  isStreaming?: boolean;
  structuredData?: StructuredData[];  // Phase 6: rich UI data
}

export interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  sessionId: string;
  error: string | null;
}

export interface SSETokenEvent {
  content: string;
}

export interface SSEDoneEvent {
  status: "complete";
}

export interface SSEErrorEvent {
  message: string;
}

// Customer selector types (Phase 5)
export interface CustomerOption {
  id: string;
  name: string;
  tariff: string;
}

// Structured data types (Phase 6 -- rich UI cards)
export interface UsageSummaryPayload {
  data_used_gb: number;
  data_limit_gb: number;
  data_percent: number;
  voice_used_minutes: number;
  voice_limit_minutes: number;
  voice_percent: number;
  sms_used: number;
  sms_limit: number;
  sms_percent: number;
  has_overage: boolean;
  overage_cost: string;
}

export interface TariffRecommendation {
  tariff_name: string;
  monthly_price: string;
  projected_cost: string;
  savings: string;
  data_gb: number;
  voice_minutes: number;
  sms_count: number;
  fit_score: number;
  reasons: string[];
}

export interface RecommendationPayload {
  current_tariff: string;
  current_cost: string;
  usage_summary: UsageSummaryPayload;
  recommendations: TariffRecommendation[];
}

export interface StructuredData {
  type: "recommendation";
  payload: RecommendationPayload;
}

export interface SSEStructuredEvent {
  type: string;
  payload: Record<string, unknown>;
}
