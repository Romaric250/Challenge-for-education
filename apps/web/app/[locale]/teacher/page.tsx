"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/dialog";
import { EmptyState, Frame } from "@/components/ui/frame";
import { api } from "@/lib/api";
import { initials } from "@/lib/session";
import { cn } from "@/lib/utils";

export default function TeacherPage() {
  const t = useTranslations("teacher");
  const nav = useTranslations("nav");
  const chat = useTranslations("chat");
  const [classId, setClassId] = useState<string | null>(null);
  const [studentId, setStudentId] = useState<string | null>(null);
  const classes = useQuery({
    queryKey: ["classes"],
    queryFn: async () => (await api.GET("/api/v1/classes")).data?.items ?? [],
  });
  const students = useQuery({
    queryKey: ["class-students", classId],
    enabled: classId !== null,
    queryFn: async () => {
      if (classId === null) {
        return [];
      }
      const result = await api.GET("/api/v1/classes/{class_id}/students", {
        params: { path: { class_id: classId } },
      });
      return result.data?.items ?? [];
    },
  });
  const transcript = useQuery({
    queryKey: ["transcript", classId, studentId],
    enabled: classId !== null && studentId !== null,
    queryFn: async () => {
      if (classId === null || studentId === null) {
        return [];
      }
      const result = await api.GET("/api/v1/teacher/transcripts", {
        params: { query: { class_id: classId, student_id: studentId } },
      });
      if (result.error) {
        throw new Error("transcripts");
      }
      return result.data ?? [];
    },
  });
  const student = (students.data ?? []).find((item) => item.id === studentId) ?? null;

  return (
    <Frame title={t("title")} description={t("body")}>
      {(classes.data ?? []).length === 0 ? (
        <EmptyState title={t("title")} body={t("empty")} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[18rem_1fr]">
          <ul className="grid content-start gap-2">
            {(classes.data ?? []).map((group) => (
              <li key={group.id}>
                <button
                  type="button"
                  className={cn(
                    "w-full rounded-2xl border px-4 py-3 text-left",
                    classId === group.id
                      ? "border-forest bg-forest text-white"
                      : "border-line bg-panel",
                  )}
                  onClick={() => {
                    setClassId(group.id);
                    setStudentId(null);
                  }}
                >
                  <span className="block font-medium">{group.name}</span>
                  <span
                    className={cn("text-xs", classId === group.id ? "text-white/70" : "text-muted")}
                  >
                    {group.subject_code}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <section className="rounded-3xl border border-line bg-panel p-5">
            <h2 className="font-serif text-2xl tracking-tight">{t("students")}</h2>
            {(students.data ?? []).length === 0 ? (
              <p className="mt-3 text-sm text-muted">{classId ? t("noStudents") : t("body")}</p>
            ) : (
              <ul className="mt-4 divide-y divide-line">
                {(students.data ?? []).map((item) => (
                  <li key={item.id} className="flex items-center justify-between gap-3 py-3">
                    <div className="flex items-center gap-3">
                      <span className="grid size-10 place-items-center rounded-full bg-mist text-sm font-medium text-accent-strong">
                        {initials(item.display_name)}
                      </span>
                      <div>
                        <p className="font-medium">{item.display_name}</p>
                        <p className="text-xs text-muted">{item.username}</p>
                      </div>
                    </div>
                    <Button type="button" variant="quiet" onClick={() => setStudentId(item.id)}>
                      {t("open")}
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
      <Modal
        open={studentId !== null}
        onOpenChange={(open) => {
          if (!open) {
            setStudentId(null);
          }
        }}
        title={student?.display_name ?? t("transcript")}
        description={t("transcriptBody")}
        closeLabel={nav("close")}
        size="lg"
      >
        {transcript.isError ? <p className="text-sm text-muted">{t("transcriptsOff")}</p> : null}
        {transcript.data && transcript.data.length > 0 ? (
          <ul className="grid gap-3">
            {transcript.data.map((item) => (
              <li
                key={item.id}
                className={cn(
                  "rounded-2xl px-4 py-3 text-sm leading-6",
                  item.role === "student" ? "bg-forest text-white" : "bg-paper",
                )}
              >
                <p
                  className={cn(
                    "mb-1 text-[11px] tracking-wide uppercase",
                    item.role === "student" ? "text-white/60" : "text-muted",
                  )}
                >
                  {item.role === "student" ? chat("you") : chat("tutor")}
                </p>
                {item.content}
              </li>
            ))}
          </ul>
        ) : null}
        {transcript.data && transcript.data.length === 0 ? (
          <p className="text-sm text-muted">{t("emptyTranscript")}</p>
        ) : null}
      </Modal>
    </Frame>
  );
}
