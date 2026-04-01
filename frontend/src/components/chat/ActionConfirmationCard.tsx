"use client";
import { ActionProposal } from "@/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Loader2 } from "lucide-react";

interface ActionConfirmationCardProps {
  proposal: ActionProposal;
  onConfirm: (threadId: string, approved: boolean) => void;
  isProcessing: boolean;
}

export function ActionConfirmationCard({
  proposal,
  onConfirm,
  isProcessing,
}: ActionConfirmationCardProps) {
  const title =
    proposal.action_type === "package_activation"
      ? "Paket Tanimlama"
      : "Tarife Degisikligi";

  return (
    <Card className="border-turkcell-yellow/40 border-l-4 border-l-turkcell-yellow">
      <CardHeader className="pb-2 px-4 pt-4">
        <CardTitle className="text-base font-semibold leading-snug">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <p className="text-sm leading-relaxed text-turkcell-dark mb-3">
          {proposal.description}
        </p>

        {/* Action details */}
        <div className="bg-turkcell-gray/50 rounded-lg p-3 space-y-1">
          {Object.entries(proposal.details).map(([key, value]) => (
            <div key={key} className="flex justify-between text-sm">
              <span className="font-semibold text-turkcell-dark">{key}:</span>
              <span className="text-turkcell-dark">{value}</span>
            </div>
          ))}
        </div>

        <Separator className="my-4" />

        {/* Action buttons */}
        <div className="flex gap-2">
          <Button
            size="lg"
            className="min-h-[44px]"
            onClick={() => onConfirm(proposal.thread_id, true)}
            disabled={isProcessing}
          >
            {isProcessing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Isleniyor...
              </>
            ) : (
              "Evet, Onayla"
            )}
          </Button>
          <Button
            variant="outline"
            size="lg"
            className="min-h-[44px]"
            onClick={() => onConfirm(proposal.thread_id, false)}
            disabled={isProcessing}
          >
            Vazgec
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
