"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, BookOpen, Library, Route, School, Users } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { Landing } from "@/components/landing";
import { NewLessonDialog } from "@/components/new-lesson-dialog";
import { Button } from "@/components/ui/button";
import { Frame } from "@/components/ui/frame";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api";
import { useMe } from "@/lib/session";

export function HomeScreen() {
  const me = useMe();
  const t = useTranslations("desk");
  const learn = useTranslations("learn");
  const [open, setOpen] = useState(false);
  const lessons = useQuery({
    queryKey: ["conversations"],
    enabled: me.data?.role === "student",
    queryFn: async () => (await api.GET("/api/v1/conversations")).data ?? [],
  });

  if (me.isPending) {
    return null;
  }
  if (!me.data) {
    return <Landing />;
  }

  const role = me.data.role;
  const body =
    role === "student" ? t("studentBody") : role === "teacher" ? t("teacherBody") : t("adminBody");

  return (
    <Frame
      title={t("title")}
      description={t("greeting", { name: me.data.display_name })}
      action={
        role === "student" ? (
          <Button type="button" onClick={() => setOpen(true)}>
            {learn("start")}
          </Button>
        ) : null
      }
    >
      <p className="-mt-4 max-w-2xl text-base leading-7 text-muted">{body}</p>
      <div className="grid gap-3 sm:grid-cols-3">
        {role === "student" ? (
          <>
            <DeskLink
              href="/learn"
              icon={<BookOpen className="size-4" />}
              title={t("openLessons")}
              body={learn("body")}
            />
            <DeskLink
              href="/chapters"
              icon={<Library className="size-4" />}
              title={t("openLibrary")}
              body={t("libraryBody")}
            />
            <DeskLink
              href="/sequences"
              icon={<Route className="size-4" />}
              title={t("openSequences")}
              body={t("sequenceBody")}
            />
          </>
        ) : null}
        {role === "teacher" || role === "admin" ? (
          <DeskLink
            href="/teacher"
            icon={<Users className="size-4" />}
            title={t("openClasses")}
            body={t("classBody")}
          />
        ) : null}
        {role === "admin" ? (
          <DeskLink
            href="/admin"
            icon={<School className="size-4" />}
            title={t("openSchool")}
            body={t("schoolBody")}
          />
        ) : null}
        {role !== "student" ? (
          <DeskLink
            href="/chapters"
            icon={<Library className="size-4" />}
            title={t("openLibrary")}
            body={t("libraryBody")}
          />
        ) : null}
      </div>
      {role === "student" ? (
        <section>
          <h2 className="font-serif text-2xl tracking-tight">{t("recent")}</h2>
          {lessons.data && lessons.data.length > 0 ? (
            <ul className="mt-4 grid gap-3 sm:grid-cols-2">
              {lessons.data.slice(0, 4).map((lesson) => (
                <li key={lesson.id}>
                  <Link
                    href={`/learn/${lesson.id}`}
                    className="flex items-center justify-between rounded-2xl border border-line bg-panel px-5 py-4 transition hover:border-accent/40"
                  >
                    <span className="font-medium">{lesson.title}</span>
                    <ArrowUpRight aria-hidden className="size-4 text-muted" />
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-muted">{t("empty")}</p>
          )}
        </section>
      ) : null}
      <NewLessonDialog open={open} onOpenChange={setOpen} />
    </Frame>
  );
}

function DeskLink({
  href,
  icon,
  title,
  body,
}: {
  href: "/learn" | "/chapters" | "/sequences" | "/teacher" | "/admin";
  icon: ReactNode;
  title: string;
  body: string;
}) {
  return (
    <Link
      href={href}
      className="rounded-3xl border border-line bg-panel p-5 transition hover:-translate-y-0.5 hover:border-accent/40"
    >
      <span className="grid size-10 place-items-center rounded-2xl bg-mist text-accent-strong">
        {icon}
      </span>
      <span className="mt-4 block font-serif text-2xl tracking-tight">{title}</span>
      <span className="mt-1 block text-sm leading-6 text-muted">{body}</span>
    </Link>
  );
}
