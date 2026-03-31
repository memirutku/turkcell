"use client";
import { StructuredData, RecommendationPayload } from "@/types";
import { RecommendationCard } from "./RecommendationCard";
import { UsageBar } from "./UsageBar";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

interface StructuredContentProps {
  data: StructuredData;
}

export function StructuredContent({ data }: StructuredContentProps) {
  if (data.type === "recommendation") {
    return <RecommendationContent payload={data.payload as RecommendationPayload} />;
  }
  return null; // Unknown structured type -- graceful degradation
}

function RecommendationContent({ payload }: { payload: RecommendationPayload }) {
  const { usage_summary, recommendations, current_tariff } = payload;

  return (
    <div className="space-y-3">
      {/* Usage summary card */}
      <Card className="border-turkcell-blue/20">
        <CardHeader className="pb-2 px-4 pt-4">
          <CardTitle className="text-base font-semibold leading-snug">
            Kullanim Ozeti
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
    </div>
  );
}
