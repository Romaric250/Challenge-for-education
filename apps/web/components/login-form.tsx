"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Field, inputClass } from "@/components/ui/field";
import { useRouter } from "@/i18n/navigation";
import { api } from "@/lib/api";

const schema = z.object({
  school_code: z.string().min(2).max(32),
  username: z.string().min(2).max(64),
  password: z.string().min(1).max(200),
});

type LoginValues = z.infer<typeof schema>;

export function LoginForm() {
  const t = useTranslations("login");
  const router = useRouter();
  const queryClient = useQueryClient();
  const [failed, setFailed] = useState(false);
  const form = useForm<LoginValues>({
    resolver: zodResolver(schema),
    defaultValues: { school_code: "", username: "", password: "" },
  });

  async function onSubmit(values: LoginValues) {
    setFailed(false);
    const result = await api.POST("/api/v1/auth/login", { body: values });
    if (!result.data) {
      setFailed(true);
      return;
    }
    await queryClient.invalidateQueries({ queryKey: ["me"] });
    if (result.data.must_change_password) {
      router.push("/settings");
      return;
    }
    router.push("/");
  }

  return (
    <form className="grid gap-4" onSubmit={form.handleSubmit(onSubmit)}>
      <Field label={t("school")}>
        <input
          autoComplete="organization"
          className={inputClass}
          {...form.register("school_code")}
        />
      </Field>
      <Field label={t("username")}>
        <input autoComplete="username" className={inputClass} {...form.register("username")} />
      </Field>
      <Field label={t("password")}>
        <input
          type="password"
          autoComplete="current-password"
          className={inputClass}
          {...form.register("password")}
        />
      </Field>
      {failed ? <p className="text-sm text-danger">{t("failed")}</p> : null}
      <Button
        className="mt-1 w-full"
        size="lg"
        type="submit"
        disabled={form.formState.isSubmitting}
      >
        {t("submit")}
      </Button>
    </form>
  );
}
