"use client";
import { StructuredData, RecommendationPayload, ActionProposal, ActionResult } from "@/types";
import { RecommendationCard } from "./RecommendationCard";
import { UsageBar } from "./UsageBar";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ActionConfirmationCard } from "./ActionConfirmationCard";
import { ActionResultCard } from "./ActionResultCard";
import { ActionProcessingIndicator } from "./ActionProcessingIndicator";
import { useChatStore } from "@/stores/chatStore";

interface StructuredContentProps {
  data: StructuredData;
}

export function StructuredContent({ data }: StructuredContentProps) {
  if (data.type === "recommendation") {
    return <RecommendationContent payload={data.payload as RecommendationPayload} />;
  }

  if (data.type === "action_proposal") {
    return <ActionProposalContent proposal={data.payload as ActionProposal} />;
  }

  if (data.type === "action_result") {
    return <ActionResultCard result={data.payload as ActionResult} />;
  }

  return null; // Unknown structured type -- graceful degradation
}

function ActionProposalContent({ proposal }: { proposal: ActionProposal }) {
  const { confirmAction, isActionProcessing, pendingAction } = useChatStore();

  // Only show buttons if this is the active pending action (text chat mode)
  const isActive = pendingAction?.thread_id === proposal.thread_id;

  if (isActive && isActionProcessing) {
    return (
      <div>
        <ActionConfirmationCard
          proposal={proposal}
          onConfirm={() => {}}
          isProcessing={true}
        />
        <ActionProcessingIndicator />
      </div>
    );
  }

  if (isActive) {
    return (
      <ActionConfirmationCard
        proposal={proposal}
        onConfirm={confirmAction}
        isProcessing={false}
      />
    );
  }

  // No active pending action — info card only (live voice mode or already handled)
  return (
    <ActionConfirmationCard
      proposal={proposal}
      onConfirm={() => {}}
      isProcessing={false}
      hideButtons
    />
  );
}

function RecommendationContent({ payload }: { payload: RecommendationPayload }) {
  const { usage_summary, recommendations, current_tariff } = payload;

  return (
    <section className="space-y-3" aria-label="Tarife önerisi ve kullanım özeti">
      {/* Usage summary card */}
      <Card className="border-umay-blue/20" role="region" aria-label="Kullanım özeti">
        <CardHeader className="pb-2 px-4 pt-4">
          <CardTitle className="text-base font-semibold leading-snug">
            Kullanım Özeti
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 space-y-3">
          <UsageBar
            label="Veri"
            used={usage_summary.data_used_gb}
            limit={usage_summary.data_limit_gb}
            unit="GB"
            percent={usage_summary.data_percent}
          />
          <UsageBar
            label="Arama"
            used={usage_summary.voice_used_minutes}
            limit={usage_summary.voice_limit_minutes}
            unit="dk"
            percent={usage_summary.voice_percent}
          />
          <UsageBar
            label="SMS"
            used={usage_summary.sms_used}
            limit={usage_summary.sms_limit}
            unit=""
            percent={usage_summary.sms_percent}
          />
        </CardContent>
      </Card>

      {/* Recommendation cards */}
      {recommendations.map((rec, i) => (
        <RecommendationCard
          key={i}
          recommendation={rec}
          currentTariff={current_tariff}
          index={i}
        />
      ))}
    </section>
  );
}
