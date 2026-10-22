import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { LayoutGrid, List, SlidersHorizontal } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ArtworkCard } from "./artwork-card";
import { TagInput } from "./tag-input";
import { useEntities } from "@/hooks/use-artmneme";
import * as api from "@/lib/api";
import type { ArtworkState } from "@/lib/domain";

export interface BrowseSearch {
  q?: string | undefined;
  view?: "grid" | "list" | undefined;
  page?: number | undefined;
  artist?: string | undefined;
  movement?: string | undefined;
  museum?: string | undefined;
  tags?: string | undefined;
  from?: number | undefined;
  to?: number | undefined;
}

const str = (v: unknown) => (typeof v === "string" && v ? v : undefined);
const num = (v: unknown) => (v === "" || v == null || isNaN(Number(v)) ? undefined : Number(v));
export const parseBrowseSearch = (s: Record<string, unknown>): BrowseSearch => ({
  q: str(s["q"]),
  view: s["view"] === "list" ? "list" : undefined,
  page: num(s["page"]),
  artist: str(s["artist"]),
  movement: str(s["movement"]),
  museum: str(s["museum"]),
  tags: str(s["tags"]),
  from: num(s["from"]),
  to: num(s["to"]),
});

const selectCls = "h-9 w-full rounded-md border border-input bg-card px-2 text-sm";

export function ArtworkBrowser({
  state,
  search,
  onChange,
}: {
  state: ArtworkState;
  search: BrowseSearch;
  onChange: (patch: Partial<BrowseSearch>) => void;
}) {
  const ent = useEntities();
  const [showFilters, setShowFilters] = useState(false);
  const tagIds = search.tags ? search.tags.split(",") : [];
  const page = search.page ?? 1;
  const view = search.view ?? "grid";
  const set = (p: Partial<BrowseSearch>) => onChange({ ...p, page: undefined });

  const { data, isLoading } = useQuery({
    queryKey: ["artworks", state, search],
    queryFn: () =>
      api.listArtworks({
        state,
        q: search.q,
        artistId: search.artist,
        movementId: search.movement,
        museum: search.museum,
        tagIds,
        fromYear: search.from,
        toYear: search.to,
        page,
      }),
  });
  const pages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;
  const filtered = !!(search.q || search.artist || search.movement || search.museum || search.tags || search.from != null || search.to != null);

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <Input className="min-w-0 flex-1 sm:max-w-sm" placeholder="Search title, artist, subject, tag, museum" defaultValue={search.q} onChange={(e) => set({ q: e.target.value || undefined })} />
        <Button variant={showFilters ? "secondary" : "ghost"} size="sm" onClick={() => setShowFilters((s) => !s)}>
          <SlidersHorizontal /> Filters
        </Button>
        <div className="ml-auto flex rounded-md border">
          <Button variant={view === "grid" ? "secondary" : "ghost"} size="icon" aria-label="Grid view" onClick={() => onChange({ view: undefined })}><LayoutGrid /></Button>
          <Button variant={view === "list" ? "secondary" : "ghost"} size="icon" aria-label="List view" onClick={() => onChange({ view: "list" })}><List /></Button>
        </div>
      </div>

      {showFilters && (
        <div className="mt-4 grid gap-4 rounded-md border bg-card p-4 sm:grid-cols-2 lg:grid-cols-3">
          <label className="space-y-1"><span className="eyebrow">Artist</span>
            <select className={selectCls} value={search.artist ?? ""} onChange={(e) => set({ artist: e.target.value || undefined })}>
              <option value="">Any</option>
              {ent.artists.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </label>
          <label className="space-y-1"><span className="eyebrow">Movement</span>
            <select className={selectCls} value={search.movement ?? ""} onChange={(e) => set({ movement: e.target.value || undefined })}>
              <option value="">Any</option>
              {ent.movements.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </label>
          <label className="space-y-1"><span className="eyebrow">Museum</span>
            <Input defaultValue={search.museum} onChange={(e) => set({ museum: e.target.value || undefined })} />
          </label>
          <div className="space-y-1"><span className="eyebrow">Date range</span>
            <div className="flex items-center gap-2">
              <Input inputMode="numeric" placeholder="From" defaultValue={search.from} onChange={(e) => set({ from: num(e.target.value) })} />
              <span>–</span>
              <Input inputMode="numeric" placeholder="To" defaultValue={search.to} onChange={(e) => set({ to: num(e.target.value) })} />
            </div>
            <p className="text-xs text-muted-foreground">Use negative years for BC.</p>
          </div>
          <div className="space-y-1 sm:col-span-2"><span className="eyebrow">Tags (all must match)</span>
            <TagInput allowCreate={false} value={tagIds} onChange={(ids) => set({ tags: ids.length ? ids.join(",") : undefined })} />
          </div>
        </div>
      )}

      <div className="mt-8">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : !data?.items.length ? (
          <div className="py-20 text-center">
            <p className="font-display text-2xl">{filtered ? "Nothing matches." : state === "COLLECTION" ? "Your collection is empty." : "Your watchlist is empty."}</p>
            {!filtered && (
              <Button asChild className="mt-5"><Link to="/artworks/new">Add an artwork</Link></Button>
            )}
          </div>
        ) : view === "grid" ? (
          <div className="grid grid-cols-2 gap-x-5 gap-y-8 sm:grid-cols-3 lg:grid-cols-4">
            {data.items.map((a) => <ArtworkCard key={a.id} a={a} />)}
          </div>
        ) : (
          <div>{data.items.map((a) => <ArtworkCard key={a.id} a={a} view="list" />)}</div>
        )}
      </div>

      {pages > 1 && (
        <div className="mt-10 flex items-center justify-center gap-4 text-sm">
          <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => onChange({ page: page - 1 })}>Previous</Button>
          <span className="text-muted-foreground">{page} / {pages}</span>
          <Button variant="ghost" size="sm" disabled={page >= pages} onClick={() => onChange({ page: page + 1 })}>Next</Button>
        </div>
      )}
    </div>
  );
}
