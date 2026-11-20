"use client";

import { useEffect } from "react";

import { Landing } from "@/components/landing";
import { useRouter } from "@/i18n/navigation";
import { useMe } from "@/lib/session";

export function LoginScreen() {
  const me = useMe();
  const router = useRouter();

  useEffect(() => {
    if (me.data) {
      router.replace(me.data.must_change_password ? "/settings" : "/");
    }
  }, [me.data, router]);

  if (me.isPending || me.data) {
    return null;
  }
  return <Landing signInOpen />;
}
