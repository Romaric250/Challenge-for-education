"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/dialog";
import { EmptyState, Frame } from "@/components/ui/frame";
import { api } from "@/lib/api";

type SequenceItem = {
  code: string;
  title: string;
  steps: string[];
  stepIndex: number;
  completed: boolean;
};

export default function SequencesPage() {
  const t = useTranslations("sequences");
  const nav = useTranslations("nav");
  const queryClient = useQueryClient();
  const [active, setActive] = useState<string | null>(null);
  const sequences = useQuery({
    queryKey: ["sequences"],
    queryFn: async () => {
      const result = await api.GET("/api/v1/sequences");
      return (result.data ?? []).flatMap(readSequence);
    },
  });
  const current = (sequences.data ?? []).find((item) => item.code === active) ?? null;
  const step = current?.steps[current.stepIndex] ?? current?.steps[0] ?? "";
  const total = current?.steps.length ?? 0;
  const position = current ? Math.min(current.stepIndex, Math.max(total - 1, 0)) : 0;

  async function advance(code: string) {
    await api.POST("/api/v1/sequences/{code}/advance", { params: { path: { code } } });
    await queryClient.invalidateQueries({ queryKey: ["sequences"] });
  }

  return (
    <Frame title={t("title")} description={t("body")}>
      {(sequences.data ?? []).length === 0 ? (
        <EmptyState title={t("title")} body={t("empty")} />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {(sequences.data ?? []).map((item) => (
            <li key={item.code}>
              <button
                type="button"
                className="flex h-full w-full flex-col rounded-3xl border border-line bg-panel p-5 text-left transition hover:-translate-y-0.5 hover:border-accent/40"
                onClick={() => setActive(item.code)}
              >
                <Badge tone={item.completed ? "good" : "neutral"}>
                  {item.completed ? t("done") : t("prompts", { count: item.steps.length })}
                </Badge>
                <span className="mt-4 font-serif text-2xl tracking-tight">{item.title}</span>
                <span className="mt-6 text-sm text-accent">
                  {item.stepIndex > 0 ? t("open") : t("begin")}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <Modal
        open={current !== null}
        onOpenChange={(open) => {
          if (!open) {
            setActive(null);
          }
        }}
        title={current?.title ?? t("title")}
        description={total > 0 ? t("step", { current: position + 1, total }) : undefined}
        closeLabel={nav("close")}
      >
        {current ? (
          <div>
            <div className="mb-5 h-1.5 overflow-hidden rounded-full bg-paper">
              <div
                className="h-full rounded-full bg-accent"
                style={{ width: total === 0 ? "0%" : `${((position + 1) / total) * 100}%` }}
              />
            </div>
            <p className="font-serif text-2xl leading-snug tracking-tight">{step}</p>
            <div className="mt-6 flex justify-end">
              <Button
                type="button"
                disabled={current.completed}
                onClick={() => void advance(current.code)}
              >
                {current.completed ? t("done") : t("next")}
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>
    </Frame>
  );
}

function readSequence(item: { [key: string]: unknown }): SequenceItem[] {
  if (typeof item.code !== "string") {
    return [];
  }
  const steps = Array.isArray(item.steps)
    ? item.steps.flatMap((step) => {
        if (step !== null && typeof step === "object" && "prompt" in step) {
          return [String(step.prompt)];
        }
        return [];
      })
    : [];
  return [
    {
      code: item.code,
      title: typeof item.title === "string" ? item.title : item.code,
      steps,
      stepIndex: typeof item.step_index === "number" ? item.step_index : 0,
      completed: item.completed === true,
    },
  ];
}
