"use client";

import { streamTutorEvents } from "@rwanda-ai-tutor/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Send } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/dialog";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api";
import { citationLabel } from "@/lib/utils";
import { cn } from "@/lib/utils";

type TutorAction = "hint" | "full_answer" | "explain_en" | "explain_rw";

export function ChatPanel({ conversationId }: { conversationId: string }) {
  const t = useTranslations("chat");
  const nav = useTranslations("nav");
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [live, setLive] = useState("");
  const [busy, setBusy] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [ratings, setRatings] = useState<Record<string, 1 | -1>>({});
  const bottom = useRef<HTMLDivElement>(null);
  const lessons = useQuery({
    queryKey: ["conversations"],
    queryFn: async () => (await api.GET("/api/v1/conversations")).data ?? [],
  });
  const messages = useQuery({
    queryKey: ["messages", conversationId],
    queryFn: async () => {
      const result = await api.GET("/api/v1/conversations/{conversation_id}/messages", {
        params: { path: { conversation_id: conversationId } },
      });
      return result.data ?? [];
    },
  });

  const items = messages.data ?? [];
  const title = lessons.data?.find((lesson) => lesson.id === conversationId)?.title ?? t("tutor");
  const lastTutor = [...items].reverse().find((item) => item.role === "tutor");

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [items.length, live]);

  async function send(action?: TutorAction) {
    const content = draft.trim();
    if (!action && content.length === 0) {
      return;
    }
    setBusy(true);
    setLive("");
    try {
      let text = "";
      for await (const event of streamTutorEvents(
        `/api/v1/conversations/${conversationId}/messages`,
        { content: content || "Continue.", action: action ?? null },
      )) {
        if (event.event === "token" && typeof event.data.text === "string") {
          text += event.data.text;
          setLive(text);
        }
      }
      if (!action) {
        setDraft("");
      }
      await queryClient.invalidateQueries({ queryKey: ["messages", conversationId] });
      setLive("");
    } finally {
      setBusy(false);
    }
  }

  async function rate(messageId: string, rating: 1 | -1) {
    setRatings((current) => ({ ...current, [messageId]: rating }));
    await api.POST("/api/v1/messages/{message_id}/feedback", {
      params: { path: { message_id: messageId } },
      body: { rating },
    });
  }

  return (
    <div className="flex h-full flex-col bg-paper">
      <header className="flex items-center gap-3 border-b border-line bg-panel/90 px-4 py-3 backdrop-blur sm:px-6">
        <Link
          href="/learn"
          className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink"
        >
          <ArrowLeft aria-hidden className="size-4" />
          {t("back")}
        </Link>
        <h1 className="min-w-0 flex-1 truncate text-center font-serif text-xl tracking-tight">
          {title}
        </h1>
        <Button type="button" variant="quiet" onClick={() => setSourcesOpen(true)}>
          {t("sources")}
        </Button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-8 sm:px-6">
          {items.length === 0 && !live ? (
            <div className="mx-auto mt-16 max-w-md text-center">
              <p className="font-serif text-3xl tracking-tight">{title}</p>
              <p className="mt-3 text-sm leading-6 text-muted">{t("empty")}</p>
            </div>
          ) : null}
          {items.map((item) => (
            <Message
              key={item.id}
              role={item.role}
              text={item.content}
              youLabel={t("you")}
              tutorLabel={t("tutor")}
              helpful={t("helpful")}
              notHelpful={t("notHelpful")}
              recorded={ratings[item.id] ? t("recorded") : null}
              onRate={
                item.role === "tutor"
                  ? (rating) => {
                      void rate(item.id, rating);
                    }
                  : undefined
              }
            />
          ))}
          {live ? (
            <Message role="tutor" text={live} youLabel={t("you")} tutorLabel={t("writing")} />
          ) : null}
          {busy && !live ? <p className="text-sm text-muted">{t("writing")}</p> : null}
          <div ref={bottom} />
        </div>
      </div>

      <footer className="border-t border-line bg-panel px-4 py-4 sm:px-6">
        <div className="mx-auto w-full max-w-3xl">
          <div className="mb-3 flex flex-wrap gap-2">
            <Chip disabled={busy} onClick={() => void send("hint")}>
              {t("hint")}
            </Chip>
            <Chip disabled={busy} onClick={() => void send("full_answer")}>
              {t("answer")}
            </Chip>
            <Chip disabled={busy} onClick={() => void send("explain_en")}>
              {t("english")}
            </Chip>
            <Chip disabled={busy} onClick={() => void send("explain_rw")}>
              {t("kinyarwanda")}
            </Chip>
          </div>
          <form
            className="flex items-end gap-2 rounded-3xl border border-line bg-white p-2 shadow-[0_10px_30px_rgba(16,36,28,0.04)]"
            onSubmit={(event) => {
              event.preventDefault();
              void send();
            }}
          >
            <textarea
              value={draft}
              rows={1}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void send();
                }
              }}
              placeholder={t("placeholder")}
              className="max-h-36 min-h-11 flex-1 resize-none bg-transparent px-3 py-2.5 text-sm outline-none"
            />
            <Button
              type="submit"
              size="icon"
              disabled={busy || draft.trim().length === 0}
              aria-label={t("send")}
            >
              <Send className="size-4" />
            </Button>
          </form>
        </div>
      </footer>

      <Modal
        open={sourcesOpen}
        onOpenChange={setSourcesOpen}
        title={t("sources")}
        description={t("sourcesBody")}
        closeLabel={nav("close")}
      >
        {lastTutor && lastTutor.citations.length > 0 ? (
          <ul className="grid gap-2">
            {lastTutor.citations.map((item, index) => (
              <li
                key={`${citationLabel(asRecord(item))}-${index}`}
                className="rounded-2xl bg-paper px-4 py-3 text-sm"
              >
                {citationLabel(asRecord(item))}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">{t("noSources")}</p>
        )}
      </Modal>
    </div>
  );
}

function Message({
  role,
  text,
  youLabel,
  tutorLabel,
  helpful,
  notHelpful,
  recorded,
  onRate,
}: {
  role: string;
  text: string;
  youLabel: string;
  tutorLabel: string;
  helpful?: string;
  notHelpful?: string;
  recorded?: string | null;
  onRate?: (rating: 1 | -1) => void;
}) {
  const own = role === "student" || role === "user";
  return (
    <article className={cn("flex", own ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[40rem] rounded-3xl px-4 py-3 text-sm",
          own ? "rounded-br-md bg-forest text-white" : "rounded-bl-md border border-line bg-panel",
        )}
      >
        <p
          className={cn(
            "mb-1 text-[11px] tracking-wide uppercase",
            own ? "text-white/60" : "text-muted",
          )}
        >
          {own ? youLabel : tutorLabel}
        </p>
        <MessageBody text={text} invert={own} />
        {onRate && helpful && notHelpful ? (
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              className="text-xs text-muted hover:text-ink"
              onClick={() => onRate(1)}
            >
              {helpful}
            </button>
            <button
              type="button"
              className="text-xs text-muted hover:text-ink"
              onClick={() => onRate(-1)}
            >
              {notHelpful}
            </button>
            {recorded ? <span className="text-xs text-accent">{recorded}</span> : null}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function MessageBody({ text, invert }: { text: string; invert: boolean }) {
  return (
    <div className={cn("tutor-md", invert && "tutor-md-invert")}>
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
        {text}
      </ReactMarkdown>
    </div>
  );
}

function Chip({
  children,
  disabled,
  onClick,
}: {
  children: string;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="rounded-full border border-line bg-paper px-3 py-1.5 text-xs font-medium text-ink transition hover:border-accent/40 disabled:opacity-50"
    >
      {children}
    </button>
  );
}

function asRecord(value: unknown) {
  if (value !== null && typeof value === "object" && !Array.isArray(value)) {
    return value as {
      marker?: unknown;
      document?: unknown;
      page_start?: unknown;
      page_end?: unknown;
    };
  }
  return {};
}
