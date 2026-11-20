"use client";

import { BookOpen, Library, Route } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { LoginForm } from "@/components/login-form";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/dialog";
import { Link, usePathname, useRouter } from "@/i18n/navigation";

export function Landing({ signInOpen = false }: { signInOpen?: boolean }) {
  const t = useTranslations("home");
  const nav = useTranslations("nav");
  const login = useTranslations("login");
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(signInOpen);

  function setSignIn(next: boolean) {
    setOpen(next);
    if (!next && pathname === "/login") {
      router.push("/");
    }
  }

  return (
    <div className="min-h-dvh bg-paper text-ink">
      <header className="sticky top-0 z-20 border-b border-line/80 bg-paper/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="inline-flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-xl bg-forest text-white">
              <BookOpen aria-hidden className="size-4" />
            </span>
            <BrandName />
          </Link>
          <div className="flex items-center gap-2">
            <Link
              href={pathname || "/"}
              locale={locale === "en" ? "rw" : "en"}
              className="hidden rounded-full px-3 py-2 text-sm text-muted hover:text-ink sm:inline"
            >
              {nav("language")}
            </Link>
            <Button type="button" onClick={() => setSignIn(true)}>
              {nav("signIn")}
            </Button>
          </div>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 py-16 sm:px-8 lg:grid-cols-[1.1fr_0.9fr] lg:py-24">
          <div>
            <p className="text-xs font-semibold tracking-[0.18em] text-accent uppercase">
              {t("eyebrow")}
            </p>
            <h1 className="mt-4 max-w-xl font-serif text-5xl leading-[1.05] tracking-tight sm:text-6xl">
              {t("title")}
            </h1>
            <p className="mt-5 max-w-lg text-lg leading-8 text-muted">{t("body")}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button type="button" size="lg" onClick={() => setSignIn(true)}>
                {t("start")}
              </Button>
              <a
                href="#how"
                className="inline-flex h-12 items-center rounded-full border border-line bg-panel px-5 text-sm font-medium"
              >
                {t("stepsTitle")}
              </a>
            </div>
          </div>
          <Preview />
        </section>

        <section className="border-y border-line bg-panel">
          <div className="mx-auto grid max-w-6xl gap-8 px-5 py-14 sm:px-8 md:grid-cols-3">
            <Feature
              icon={<BookOpen className="size-4" />}
              title={t("featureCiteTitle")}
              body={t("featureCiteBody")}
            />
            <Feature
              icon={<Route className="size-4" />}
              title={t("featureHintTitle")}
              body={t("featureHintBody")}
            />
            <Feature
              icon={<Library className="size-4" />}
              title={t("featureLanguageTitle")}
              body={t("featureLanguageBody")}
            />
          </div>
        </section>

        <section id="how" className="mx-auto max-w-6xl px-5 py-16 sm:px-8">
          <h2 className="font-serif text-4xl tracking-tight">{t("stepsTitle")}</h2>
          <ol className="mt-8 grid gap-4 md:grid-cols-3">
            <Step index="01" title={t("step1Title")} body={t("step1Body")} />
            <Step index="02" title={t("step2Title")} body={t("step2Body")} />
            <Step index="03" title={t("step3Title")} body={t("step3Body")} />
          </ol>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-6 text-sm text-muted sm:px-8">
          <BrandName />
          <p>{t("footer")}</p>
        </div>
      </footer>

      <Modal
        open={open}
        onOpenChange={setSignIn}
        title={login("title")}
        description={login("body")}
        closeLabel={nav("close")}
      >
        <LoginForm />
      </Modal>
    </div>
  );
}

function BrandName() {
  const brand = useTranslations()("brand");
  return <span className="font-serif text-lg tracking-tight">{brand}</span>;
}

function Preview() {
  const t = useTranslations("home");
  return (
    <div className="rounded-[1.75rem] border border-line bg-forest p-3 shadow-[0_24px_60px_rgba(16,36,28,0.16)]">
      <div className="rounded-[1.35rem] bg-panel p-5">
        <p className="text-xs font-semibold tracking-[0.16em] text-accent uppercase">
          {t("previewLabel")}
        </p>
        <div className="mt-5 ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-forest px-4 py-3 text-sm leading-6 text-white">
          <p className="mb-1 text-[11px] tracking-wide text-white/60 uppercase">
            {t("previewYou")}
          </p>
          {t("previewQuestion")}
        </div>
        <div className="mt-3 max-w-[90%] rounded-2xl rounded-bl-md border border-line bg-paper px-4 py-3 text-sm leading-6">
          <p className="mb-1 text-[11px] tracking-wide text-muted uppercase">{t("previewTutor")}</p>
          {t("previewAnswer")}
          <p className="mt-3 inline-flex rounded-full bg-mist px-2.5 py-1 text-xs font-medium text-accent-strong">
            {t("previewSource")}
          </p>
        </div>
      </div>
    </div>
  );
}

function Feature({ icon, title, body }: { icon: ReactNode; title: string; body: string }) {
  return (
    <article>
      <span className="grid size-10 place-items-center rounded-2xl bg-mist text-accent-strong">
        {icon}
      </span>
      <h2 className="mt-4 font-serif text-2xl tracking-tight">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-muted">{body}</p>
    </article>
  );
}

function Step({ index, title, body }: { index: string; title: string; body: string }) {
  return (
    <li className="rounded-3xl border border-line bg-panel p-6">
      <p className="font-serif text-3xl text-accent">{index}</p>
      <h3 className="mt-4 font-serif text-2xl tracking-tight">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-muted">{body}</p>
    </li>
  );
}
