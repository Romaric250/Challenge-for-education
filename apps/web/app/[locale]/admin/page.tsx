"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/dialog";
import { Field, inputClass } from "@/components/ui/field";
import { EmptyState, Frame } from "@/components/ui/frame";
import { api } from "@/lib/api";

export default function AdminPage() {
  const t = useTranslations("admin");
  const nav = useTranslations("nav");
  const roles = useTranslations("roles");
  const queryClient = useQueryClient();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [providerOpen, setProviderOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [provider, setProvider] = useState("none");
  const [model, setModel] = useState("claude-sonnet-4-5");
  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: async () => (await api.GET("/api/v1/documents")).data ?? [],
  });
  const users = useQuery({
    queryKey: ["users"],
    queryFn: async () => (await api.GET("/api/v1/users")).data?.items ?? [],
  });

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    form.set("title", title);
    const response = await fetch("/api/v1/documents", {
      method: "POST",
      body: form,
      credentials: "include",
      headers: { "X-Requested-With": "tutor" },
    });
    if (response.ok) {
      setTitle("");
      setUploadOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
    }
  }

  async function saveProvider(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const saved = await api.PUT("/api/v1/admin/provider", { body: { provider, model } });
    if (!saved.error) {
      setProviderOpen(false);
    }
  }

  return (
    <Frame
      title={t("title")}
      description={t("body")}
      action={
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="quiet" onClick={() => setProviderOpen(true)}>
            {t("provider")}
          </Button>
          <Button type="button" onClick={() => setUploadOpen(true)}>
            {t("upload")}
          </Button>
        </div>
      }
    >
      <section>
        <h2 className="mb-4 font-serif text-2xl tracking-tight">{t("documents")}</h2>
        {(documents.data ?? []).length === 0 ? (
          <EmptyState title={t("documents")} body={t("emptyDocuments")} />
        ) : (
          <ul className="overflow-hidden rounded-3xl border border-line bg-panel">
            {(documents.data ?? []).map((item) => (
              <li
                key={item.id}
                className="flex items-center justify-between gap-4 border-b border-line px-5 py-4 last:border-b-0"
              >
                <div>
                  <p className="font-medium">{item.title}</p>
                  <p className="text-sm text-muted">
                    {item.source_name} · {item.page_count}
                  </p>
                </div>
                <Badge tone={item.status === "ready" ? "good" : "warn"}>{item.status}</Badge>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="mb-4 font-serif text-2xl tracking-tight">{t("users")}</h2>
        <div className="overflow-hidden rounded-3xl border border-line bg-panel">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line text-xs tracking-wide text-muted uppercase">
              <tr>
                <th className="px-5 py-3 font-medium">{t("name")}</th>
                <th className="px-5 py-3 font-medium">{t("username")}</th>
                <th className="px-5 py-3 font-medium">{t("role")}</th>
              </tr>
            </thead>
            <tbody>
              {(users.data ?? []).map((user) => (
                <tr key={user.id} className="border-b border-line last:border-b-0">
                  <td className="px-5 py-3 font-medium">{user.display_name}</td>
                  <td className="px-5 py-3 text-muted">{user.username}</td>
                  <td className="px-5 py-3">
                    <Badge>{roleName(roles, user.role)}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <Modal
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        title={t("upload")}
        description={t("uploadBody")}
        closeLabel={nav("close")}
      >
        <form className="grid gap-4" onSubmit={(event) => void upload(event)}>
          <Field label={t("titleField")}>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className={inputClass}
              required
            />
          </Field>
          <Field label={t("file")}>
            <input
              name="file"
              type="file"
              accept="application/pdf"
              required
              className="block w-full text-sm text-muted file:mr-3 file:rounded-full file:border-0 file:bg-mist file:px-4 file:py-2 file:text-sm file:font-medium file:text-accent-strong"
            />
          </Field>
          <div className="flex justify-end">
            <Button type="submit">{t("submit")}</Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={providerOpen}
        onOpenChange={setProviderOpen}
        title={t("provider")}
        description={t("providerBody")}
        closeLabel={nav("close")}
      >
        <form className="grid gap-4" onSubmit={(event) => void saveProvider(event)}>
          <Field label={t("provider")}>
            <select
              value={provider}
              onChange={(event) => setProvider(event.target.value)}
              className={inputClass}
            >
              <option value="none">{t("none")}</option>
              <option value="anthropic">{t("anthropic")}</option>
              <option value="openai_compatible">{t("openai")}</option>
            </select>
          </Field>
          <Field label={t("model")}>
            <input
              value={model}
              onChange={(event) => setModel(event.target.value)}
              className={inputClass}
            />
          </Field>
          <div className="flex justify-end">
            <Button type="submit">{t("save")}</Button>
          </div>
        </form>
      </Modal>
    </Frame>
  );
}

function roleName(roles: (key: "student" | "teacher" | "admin") => string, role: string) {
  if (role === "student" || role === "teacher" || role === "admin") {
    return roles(role);
  }
  return role;
}
