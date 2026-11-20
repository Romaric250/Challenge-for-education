"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/dialog";
import { EmptyState, Frame } from "@/components/ui/frame";
import { useRouter } from "@/i18n/navigation";
import { api } from "@/lib/api";
import { useMe } from "@/lib/session";

export default function ChaptersPage() {
  const t = useTranslations("chapters");
  const nav = useTranslations("nav");
  const router = useRouter();
  const queryClient = useQueryClient();
  const me = useMe();
  const [selected, setSelected] = useState<string | null>(null);
  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: async () => (await api.GET("/api/v1/documents")).data ?? [],
  });
  const ready = (documents.data ?? []).filter((item) => item.status === "ready");
  const current = ready.find((item) => item.id === selected) ?? null;

  async function ask(title: string) {
    const created = await api.POST("/api/v1/conversations", { body: { title } });
    if (!created.data) {
      return;
    }
    await queryClient.invalidateQueries({ queryKey: ["conversations"] });
    router.push(`/learn/${created.data.id}`);
  }

  return (
    <Frame title={t("title")} description={t("body")}>
      {ready.length === 0 ? (
        <EmptyState title={t("empty")} body={t("emptyBody")} />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {ready.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className="flex h-full w-full flex-col rounded-3xl border border-line bg-panel p-5 text-left transition hover:-translate-y-0.5 hover:border-accent/40"
                onClick={() => setSelected(item.id)}
              >
                <Badge tone="good">{item.status}</Badge>
                <span className="mt-4 font-serif text-2xl tracking-tight">{item.title}</span>
                <span className="mt-2 text-sm text-muted">
                  {t("pages", { count: item.page_count })}
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
            setSelected(null);
          }
        }}
        title={current?.title ?? t("details")}
        description={current ? t("pages", { count: current.page_count }) : undefined}
        closeLabel={nav("close")}
      >
        {current ? (
          <div className="grid gap-4">
            <dl className="grid gap-3 text-sm">
              <div className="flex items-center justify-between gap-4 rounded-2xl bg-paper px-4 py-3">
                <dt className="text-muted">{t("source")}</dt>
                <dd className="text-right font-medium">{current.source_name}</dd>
              </div>
              <div className="flex items-center justify-between gap-4 rounded-2xl bg-paper px-4 py-3">
                <dt className="text-muted">{t("status")}</dt>
                <dd>
                  <Badge tone="good">{current.status}</Badge>
                </dd>
              </div>
            </dl>
            {me.data?.role === "student" ? (
              <div className="flex justify-end">
                <Button type="button" onClick={() => void ask(current.title)}>
                  {t("ask")}
                </Button>
              </div>
            ) : null}
          </div>
        ) : null}
      </Modal>
    </Frame>
  );
}
