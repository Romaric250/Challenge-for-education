"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/dialog";
import { Field, inputClass } from "@/components/ui/field";
import { Frame } from "@/components/ui/frame";
import { api } from "@/lib/api";
import { useMe } from "@/lib/session";

export default function SettingsPage() {
  const t = useTranslations("settings");
  const nav = useTranslations("nav");
  const queryClient = useQueryClient();
  const me = useMe();
  const [name, setName] = useState<string | null>(null);
  const [language, setLanguage] = useState<"en" | "rw" | null>(null);
  const [notice, setNotice] = useState<"profile" | "password" | null>(null);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [nextPassword, setNextPassword] = useState("");
  const displayName = name ?? me.data?.display_name ?? "";
  const preferred = language ?? me.data?.preferred_language ?? "en";

  async function saveProfile() {
    const saved = await api.PATCH("/api/v1/auth/me", {
      body: { display_name: displayName, preferred_language: preferred },
    });
    if (!saved.error) {
      setNotice("profile");
      await queryClient.invalidateQueries({ queryKey: ["me"] });
    }
  }

  async function changePassword() {
    const saved = await api.POST("/api/v1/auth/password", {
      body: { current_password: currentPassword, new_password: nextPassword },
    });
    if (!saved.error) {
      setCurrentPassword("");
      setNextPassword("");
      setPasswordOpen(false);
      setNotice("password");
      await queryClient.invalidateQueries({ queryKey: ["me"] });
    }
  }

  return (
    <Frame
      title={t("title")}
      description={t("body")}
      action={
        <Button type="button" variant="quiet" onClick={() => setPasswordOpen(true)}>
          {t("password")}
        </Button>
      }
    >
      <form
        className="grid max-w-lg gap-4 rounded-3xl border border-line bg-panel p-6"
        onSubmit={(event) => {
          event.preventDefault();
          void saveProfile();
        }}
      >
        <Field label={t("name")}>
          <input
            value={displayName}
            onChange={(event) => setName(event.target.value)}
            className={inputClass}
          />
        </Field>
        <Field label={t("language")}>
          <select
            value={preferred}
            onChange={(event) => setLanguage(event.target.value === "rw" ? "rw" : "en")}
            className={inputClass}
          >
            <option value="en">{t("english")}</option>
            <option value="rw">{t("kinyarwanda")}</option>
          </select>
        </Field>
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-accent">
            {notice === "profile" ? t("saved") : notice === "password" ? t("passwordSaved") : ""}
          </p>
          <Button type="submit">{t("save")}</Button>
        </div>
      </form>

      <Modal
        open={passwordOpen}
        onOpenChange={setPasswordOpen}
        title={t("change")}
        description={t("changeBody")}
        closeLabel={nav("close")}
      >
        <form
          className="grid gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            void changePassword();
          }}
        >
          <Field label={t("current")}>
            <input
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              className={inputClass}
            />
          </Field>
          <Field label={t("next")}>
            <input
              type="password"
              autoComplete="new-password"
              value={nextPassword}
              onChange={(event) => setNextPassword(event.target.value)}
              className={inputClass}
            />
          </Field>
          <div className="flex justify-end">
            <Button type="submit">{t("change")}</Button>
          </div>
        </form>
      </Modal>
    </Frame>
  );
}
