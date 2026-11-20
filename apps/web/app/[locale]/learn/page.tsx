"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { NewLessonDialog } from "@/components/new-lesson-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, Frame } from "@/components/ui/frame";
import { useRouter } from "@/i18n/navigation";
import { api } from "@/lib/api";

export default function LearnPage() {
  const t = useTranslations("learn");
  const language = useTranslations("settings");
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const lessons = useQuery({
    queryKey: ["conversations"],
    queryFn: async () => (await api.GET("/api/v1/conversations")).data ?? [],
  });

  return (
    <Frame
      title={t("title")}
      description={t("body")}
      action={
        <Button type="button" onClick={() => setOpen(true)}>
          {t("start")}
        </Button>
      }
    >
      {lessons.data && lessons.data.length > 0 ? (
        <ul className="grid gap-3 sm:grid-cols-2">
          {lessons.data.map((lesson) => (
            <li key={lesson.id}>
              <button
                type="button"
                className="flex h-full w-full flex-col rounded-3xl border border-line bg-panel p-5 text-left transition hover:-translate-y-0.5 hover:border-accent/40"
                onClick={() => router.push(`/learn/${lesson.id}`)}
              >
                <Badge tone={lesson.flagged ? "warn" : "good"}>
                  {lesson.language === "rw" ? language("kinyarwanda") : language("english")}
                </Badge>
                <span className="mt-4 font-serif text-2xl tracking-tight">{lesson.title}</span>
                <span className="mt-6 text-sm text-muted">{t("open")}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState
          title={t("empty")}
          body={t("emptyBody")}
          action={
            <Button type="button" onClick={() => setOpen(true)}>
              {t("start")}
            </Button>
          }
        />
      )}
      <NewLessonDialog open={open} onOpenChange={setOpen} />
    </Frame>
  );
}
