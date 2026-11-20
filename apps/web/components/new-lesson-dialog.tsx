"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, inputClass } from "@/components/ui/field";
import { Modal } from "@/components/ui/dialog";
import { useRouter } from "@/i18n/navigation";
import { api } from "@/lib/api";

export function NewLessonDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const t = useTranslations("learn");
  const closeLabel = useTranslations("nav")("close");
  const router = useRouter();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");

  async function create() {
    const created = await api.POST("/api/v1/conversations", {
      body: { title: title.trim() || "New lesson" },
    });
    if (!created.data) {
      return;
    }
    setTitle("");
    onOpenChange(false);
    await queryClient.invalidateQueries({ queryKey: ["conversations"] });
    router.push(`/learn/${created.data.id}`);
  }

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={t("modalTitle")}
      description={t("modalBody")}
      closeLabel={closeLabel}
    >
      <form
        className="grid gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          void create();
        }}
      >
        <Field label={t("name")}>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className={inputClass}
            autoFocus
          />
        </Field>
        <div className="flex justify-end">
          <Button type="submit">{t("create")}</Button>
        </div>
      </form>
    </Modal>
  );
}
