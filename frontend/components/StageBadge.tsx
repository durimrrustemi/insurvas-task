import { stageColor } from "@/lib/utils";

export function StageBadge({ stage }: { stage: string }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${stageColor(stage)}`}>
      {stage.replace(/_/g, " ")}
    </span>
  );
}
