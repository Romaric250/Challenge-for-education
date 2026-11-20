"use client";

import { useQueryClient } from "@tanstack/react-query";
import { BookOpen, Library, LogOut, Menu, Route, School, Settings, Users } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState, type ReactNode } from "react";

import { LoginForm } from "@/components/login-form";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/dialog";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { api } from "@/lib/api";
import { initials, useMe } from "@/lib/session";
import { cn } from "@/lib/utils";

const links = [
  ["learn", "/learn", BookOpen],
  ["chapters", "/chapters", Library],
  ["sequences", "/sequences", Route],
  ["teacher", "/teacher", Users],
  ["admin", "/admin", School],
  ["settings", "/settings", Settings],
] as const;

export function Shell({ children }: { children: ReactNode }) {
  const t = useTranslations();
  const me = useMe();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);
  const publicPage = pathname === "/" || pathname === "/login";

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || me.isPending) {
    return (
      <div className="grid min-h-dvh place-items-center bg-paper">
        <p className="font-serif text-2xl tracking-tight">{t("brand")}</p>
      </div>
    );
  }

  if (!me.data) {
    if (publicPage) {
      return children;
    }
    return <SignedOutGate />;
  }

  return (
    <AppFrame role={me.data.role} name={me.data.display_name}>
      {children}
    </AppFrame>
  );
}

function AppFrame({ children, role, name }: { children: ReactNode; role: string; name: string }) {
  const t = useTranslations();
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [menuOpen, setMenuOpen] = useState(false);
  const items = links.filter(([key]) => visible(key, role));

  async function signOut() {
    await api.POST("/api/v1/auth/logout", { body: {} });
    queryClient.removeQueries({ queryKey: ["me"] });
    router.push("/");
  }

  return (
    <div className="flex h-dvh bg-paper text-ink">
      <aside className="hidden w-64 shrink-0 flex-col bg-forest text-white md:flex">
        <Link href="/" className="flex items-center gap-3 px-5 pt-6">
          <span className="grid size-9 place-items-center rounded-xl bg-white/10">
            <BookOpen aria-hidden className="size-4" />
          </span>
          <span className="font-serif text-lg leading-tight tracking-tight">{t("brand")}</span>
        </Link>
        <nav className="mt-8 grid gap-1 px-3">
          {items.map(([key, href, Icon]) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm",
                  active
                    ? "bg-white text-forest"
                    : "text-white/75 hover:bg-white/10 hover:text-white",
                )}
              >
                <Icon aria-hidden className="size-4" />
                {t(`nav.${key}`)}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto border-t border-white/10 p-4">
          <div className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-full bg-white/10 text-sm font-medium">
              {initials(name)}
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{name}</p>
              <p className="text-xs text-white/60">{roleLabel(t, role)}</p>
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between">
            <Link
              href={pathname || "/"}
              locale={locale === "en" ? "rw" : "en"}
              className="text-xs text-white/70"
            >
              {t("nav.language")}
            </Link>
            <button
              type="button"
              className="inline-flex items-center gap-1 text-xs text-white/70"
              onClick={() => void signOut()}
            >
              <LogOut aria-hidden className="size-3.5" />
              {t("nav.signOut")}
            </button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-line bg-panel px-4 md:hidden">
          <Link href="/" className="font-serif tracking-tight">
            {t("brand")}
          </Link>
          <Button
            type="button"
            variant="quiet"
            size="icon"
            onClick={() => setMenuOpen(true)}
            aria-label={t("nav.menu")}
          >
            <Menu className="size-4" />
          </Button>
        </header>
        <main className="min-h-0 flex-1 overflow-hidden">{children}</main>
      </div>

      <Modal
        open={menuOpen}
        onOpenChange={setMenuOpen}
        title={t("nav.menu")}
        closeLabel={t("nav.close")}
      >
        <nav className="grid gap-1">
          {items.map(([key, href]) => (
            <Link
              key={href}
              href={href}
              className="rounded-2xl px-3 py-3 text-sm hover:bg-paper"
              onClick={() => setMenuOpen(false)}
            >
              {t(`nav.${key}`)}
            </Link>
          ))}
        </nav>
        <Button
          className="mt-4 w-full"
          variant="quiet"
          type="button"
          onClick={() => void signOut()}
        >
          {t("nav.signOut")}
        </Button>
      </Modal>
    </div>
  );
}

function SignedOutGate() {
  const t = useTranslations("gate");
  const nav = useTranslations("nav");
  const login = useTranslations("login");
  const [open, setOpen] = useState(false);
  return (
    <div className="grid min-h-dvh place-items-center bg-paper px-5">
      <div className="w-full max-w-md rounded-3xl border border-line bg-panel p-8 text-center shadow-[0_20px_50px_rgba(16,36,28,0.06)]">
        <p className="font-serif text-3xl tracking-tight">{t("title")}</p>
        <p className="mt-3 text-sm leading-6 text-muted">{t("body")}</p>
        <Button className="mt-6" type="button" onClick={() => setOpen(true)}>
          {nav("signIn")}
        </Button>
      </div>
      <Modal
        open={open}
        onOpenChange={setOpen}
        title={login("title")}
        description={login("body")}
        closeLabel={nav("close")}
      >
        <LoginForm />
      </Modal>
    </div>
  );
}

function visible(key: (typeof links)[number][0], role: string) {
  if (key === "teacher") {
    return role === "teacher" || role === "admin";
  }
  if (key === "admin") {
    return role === "admin";
  }
  if (key === "learn" || key === "sequences") {
    return role === "student";
  }
  return true;
}

function roleLabel(t: ReturnType<typeof useTranslations>, role: string) {
  if (role === "student" || role === "teacher" || role === "admin") {
    return t(`roles.${role}`);
  }
  return role;
}
