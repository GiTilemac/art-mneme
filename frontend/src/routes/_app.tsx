import { createFileRoute, Link, Outlet, redirect, useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import * as api from "@/lib/api";

// Signed-in area. Session is mocked in the browser, so this only runs client-side.
export const Route = createFileRoute("/_app")({
  ssr: false,
  beforeLoad: ({ location }) => {
    const session = api.getSessionSync();
    if (!session) throw redirect({ to: "/auth", search: { redirect: location.href } });
    return { session };
  },
  component: AppLayout,
});

const navCls = "text-sm text-muted-foreground data-[status=active]:text-foreground data-[status=active]:underline underline-offset-8";

function AppLayout() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  async function signOut() {
    await qc.cancelQueries();
    qc.clear();
    await api.signOut();
    navigate({ to: "/auth", replace: true });
  }
  return (
    <div className="min-h-screen">
      <header className="border-b">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-5 py-4">
          <Link to="/collection" className="font-display text-2xl">ArtMneme</Link>
          <nav className="flex gap-5">
            <Link to="/collection" className={navCls}>Collection</Link>
            <Link to="/watchlist" className={navCls}>Watchlist</Link>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <Button asChild size="sm"><Link to="/artworks/new"><Plus /> Add</Link></Button>
            <Button variant="ghost" size="sm" onClick={signOut}>Sign out</Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-5 py-10">
        <Outlet />
      </main>
    </div>
  );
}
