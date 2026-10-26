import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { LayoutGrid, List, SlidersHorizontal } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ArtworkCard } from "./artwork-card";
import { EntityPicker } from "./entity-picker";
import { TagInput } from "./tag-input";
import { api } from "@/services";
import type { ArtworkState, Entity } from "@/lib/domain";

export interface BrowseSearch {
  q?: string | undefined;
  view?: "grid" | "list" | undefined;
  page?: number | undefined;
  artist?: Entity | undefined;
  movement?: Entity | undefined;
  museum?: string | undefined;
  tags?: Entity[] | undefined;
  from?: number | undefined;
  fromBc?: boolean | undefined;
  to?: number | undefined;
  toBc?: boolean | undefined;
}

const str = (v: unknown) => (typeof v === "string" && v ? v : undefined);
const entity = (v: unknown): Entity | undefined => {
  const e = v as Partial<Entity> | null;
  return typeof e?.id === "string" && typeof e.name === "string" ? { id: e.id, name: e.name } : undefined;
};
const entities = (v: unknown) => {
  const list = Array.isArray(v) ? v.map(entity).filter((e): e is Entity => !!e) : [];
  return list.length ? list : undefined;
};
const num = (v: unknown) => (v === "" || v == null || isNaN(Number(v)) ? undefined : Number(v));
export const parseBrowseSearch = (s: Record<string, unknown>): BrowseSearch => ({
  q: str(s["q"]),
  view: s["view"] === "list" ? "list" : undefined,
  page: num(s["page"]),
  artist: entity(s["artist"]),
  movement: entity(s["movement"]),
  museum: str(s["museum"]),
  tags: entities(s["tags"]),
  from: num(s["from"]),
  fromBc: s["fromBc"] === true ? true : undefined,
  to: num(s["to"]),
  toBc: s["toBc"] === true ? true : undefined,
});


export function ArtworkBrowser({
  state,
  search,
  onChange,
}: {
  state: ArtworkState;
  search: BrowseSearch;
  onChange: (patch: Partial<BrowseSearch>) => void;
}) {
  const [showFilters, setShowFilters] = useState(false);
  const tags = search.tags ?? [];
  const page = search.page ?? 1;
  const view = search.view ?? "grid";
  const set = (p: Partial<BrowseSearch>) => onChange({ ...p, page: undefined });

  const { data, isLoading } = useQuery({
    queryKey: ["artworks", state, search],
    queryFn: () =>
      api.listArtworks({
        state,
        q: search.q,
        artistId: search.artist?.id,
        movementId: search.movement?.id,
        museum: search.museum,
        tagIds: tags.map((t) => t.id),
        fromYear: search.from,
        fromBc: search.fromBc,
        toYear: search.to,
        toBc: search.toBc,
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
          <div className="space-y-1"><span className="eyebrow">Artist</span>
            <EntityPicker kind="artists" allowCreate={false} value={search.artist ?? null} onChange={(e) => set({ artist: e ?? undefined })} placeholder="Any" />
          </div>
          <div className="space-y-1"><span className="eyebrow">Movement</span>
            <EntityPicker kind="movements" allowCreate={false} value={search.movement ?? null} onChange={(e) => set({ movement: e ?? undefined })} placeholder="Any" />
          </div>
          <label className="space-y-1"><span className="eyebrow">Museum</span>
            <Input defaultValue={search.museum} onChange={(e) => set({ museum: e.target.value || undefined })} />
          </label>
          <div className="space-y-1"><span className="eyebrow">Date range</span>
            <div className="flex items-center gap-2">
              <Input inputMode="numeric" placeholder="From" defaultValue={search.from} onChange={(e) => set({ from: num(e.target.value) })} />
              <label className="flex items-center gap-1.5 text-sm">
                <Checkbox checked={!!search.fromBc} onCheckedChange={(v) => set({ fromBc: v === true ? true : undefined })} /> BC
              </label>
              <span>–</span>
              <Input inputMode="numeric" placeholder="To" defaultValue={search.to} onChange={(e) => set({ to: num(e.target.value) })} />
              <label className="flex items-center gap-1.5 text-sm">
                <Checkbox checked={!!search.toBc} onCheckedChange={(v) => set({ toBc: v === true ? true : undefined })} /> BC
              </label>
            </div>
          </div>
          <div className="space-y-1 sm:col-span-2"><span className="eyebrow">Tags (all must match)</span>
            <TagInput allowCreate={false} value={tags} onChange={(t) => set({ tags: t.length ? t : undefined })} />
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
