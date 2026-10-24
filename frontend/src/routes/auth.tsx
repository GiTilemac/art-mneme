import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { api } from "@/services";
import { MIN_PASSWORD_LENGTH } from "@/lib/domain";

export const Route = createFileRoute("/auth")({
  validateSearch: (s: Record<string, unknown>): { mode?: "signup" | undefined; redirect?: string | undefined } => ({
    mode: s["mode"] === "signup" ? "signup" : undefined,
    redirect: typeof s["redirect"] === "string" && s["redirect"].startsWith("/") ? s["redirect"] : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Sign in — ArtMneme" },
      { name: "description", content: "Sign in or create your ArtMneme account." },
      { property: "og:title", content: "Sign in — ArtMneme" },
      { property: "og:description", content: "Sign in or create your ArtMneme account." },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const { mode, redirect } = Route.useSearch();
  const navigate = useNavigate();
  const signup = mode === "signup";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await (signup ? api.register : api.login)(email, password);
      navigate({ to: redirect ?? "/collection" });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <Link to="/" className="font-display text-2xl">ArtMneme</Link>
        <h1 className="mt-10 text-4xl">{signup ? "Create your account" : "Welcome back"}</h1>
        <form onSubmit={submit} className="mt-8 space-y-5">
          <div className="space-y-1.5">
            <Label className="eyebrow" htmlFor="email">Email</Label>
            <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label className="eyebrow" htmlFor="password">Password</Label>
            <Input id="password" type="password" autoComplete={signup ? "new-password" : "current-password"} required value={password} onChange={(e) => setPassword(e.target.value)} />
            {signup && <p className="text-xs text-muted-foreground">At least {MIN_PASSWORD_LENGTH} characters.</p>}
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full" disabled={busy}>{busy ? "…" : signup ? "Create account" : "Sign in"}</Button>
        </form>
        <p className="mt-6 text-sm text-muted-foreground">
          {signup ? "Already have an account? " : "New here? "}
          <Link to="/auth" search={{ mode: signup ? undefined : "signup", redirect }} className="text-primary underline-offset-4 hover:underline">
            {signup ? "Sign in" : "Create an account"}
          </Link>
        </p>
      </div>
    </div>
  );
}
