import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { ArtworkCard } from "@/components/artmneme/artwork-card";
import { api, type Dimension } from "@/services";
import { formatDate, type CommunityArtwork } from "@/lib/domain";
import { PREFILL_KEY } from "./_app.artworks.new";

export const Route = createFileRoute("/_app/artworks/$id_/explore")({
  head: () => ({
    meta: [
      { title: "Explore relationships — ArtMneme" },
      { name: "description", content: "Find artworks related by artist, subject, movement, museum or tags." },
      { property: "og:title", content: "Explore relationships — ArtMneme" },
      { property: "og:description", content: "Find artworks related by artist, subject, movement, museum or tags." },
    ],
  }),
  component: Explore,
});

const DIMS: { key: Dimension; label: string }[] = [
  { key: "artist", label: "Same artist" },
  { key: "subject", label: "Same subject" },
  { key: "movement", label: "Same movement" },
  { key: "museum", label: "Same museum" },
  { key: "tags", label: "Shared tags" },
];

function CommunityCard({ c }: { c: CommunityArtwork }) {
  const navigate = useNavigate();
  return (
    <div className="flex flex-col rounded-sm border bg-card p-4">
      <p className="eyebrow">Community</p>
      <p className="mt-2 font-display text-lg leading-tight">{c.title}</p>
      <p className="text-sm text-muted-foreground">{[c.artist?.name, formatDate(c.date)].filter(Boolean).join(" · ")}</p>
      {c.museum && <p className="mt-1 text-xs text-muted-foreground">{c.museum}</p>}
      {c.notes && <p className="mt-3 text-sm italic">“{c.notes}”</p>}
      <Button
        variant="ghost"
        size="sm"
        className="mt-auto self-start px-0 pt-4 text-primary"
        onClick={() => {
          const { title, artist, date, subject, movement, museum, tags } = c;
          sessionStorage.setItem(PREFILL_KEY, JSON.stringify({ title, artist, date, subject, movement, museum, tags }));
          navigate({ to: "/artworks/new", search: { from: c.id } });
        }}
      >
        + Add to my watchlist
      </Button>
    </div>
  );
}

function Explore() {
  const { id } = Route.useParams();
  const { data: src } = useQuery({ queryKey: ["artwork", id], queryFn: () => api.getArtwork(id) });
  const [dimension, setDimension] = useState<Dimension | null>(null);
  const [tagIds, setTagIds] = useState<string[]>([]);
  const [sources, setSources] = useState({ includeCollection: true, includeWatchlist: false, includeCommunity: false });

  const ready = !!src && !!dimension && (dimension !== "tags" || tagIds.length > 0);
  const { data, isFetching } = useQuery({
    queryKey: ["explore", id, dimension, tagIds, sources],
    queryFn: () => api.explore(id, { by: dimension!, tagIds, ...sources }),
    enabled: ready,
  });

  if (!src) return null;
  const available: Record<Dimension, boolean> = {
    artist: !!src.artist,
    subject: !!src.subject,
    movement: !!src.movement,
    museum: !!src.museum,
    tags: src.tags.length > 0,
  };
  const total = data ? data.collection.length + data.watchlist.length + data.community.length : 0;

  return (
    <div>
      <Link to="/artworks/$id" params={{ id }} className="inline-flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="size-4" /> {src.title || "Untitled"}
      </Link>
      <h1 className="mt-4 text-4xl">Explore relationships</h1>

      <div className="mt-8 flex flex-wrap gap-2">
        {DIMS.map((d) => (
          <Button key={d.key} variant={dimension === d.key ? "default" : "outline"} size="sm" disabled={!available[d.key]} onClick={() => { setDimension(d.key); if (d.key === "tags" && !tagIds.length) setTagIds(src.tags.slice(0, 1).map((t) => t.id)); }}>
            {d.label}
          </Button>
        ))}
      </div>

      {dimension === "tags" && (
        <div className="mt-4">
          <p className="eyebrow mb-2">Narrow by tags — results match all selected</p>
          <div className="flex flex-wrap gap-1.5">
            {src.tags.map((t) => {
              const on = tagIds.includes(t.id);
              return (
                <button key={t.id} type="button" onClick={() => setTagIds(on ? tagIds.filter((x) => x !== t.id) : [...tagIds, t.id])} className={`rounded-full border px-3 py-1 text-xs ${on ? "border-primary bg-primary text-primary-foreground" : "text-muted-foreground"}`}>
                  {t.name}
                </button>
              );
            })}
          </div>
        </div>
      )}

      <div className="mt-6 flex flex-wrap gap-6 border-y py-3 text-sm">
        {([["includeCollection", "My collection"], ["includeWatchlist", "Watchlist"], ["includeCommunity", "Community"]] as const).map(([k, label]) => (
          <label key={k} className="flex items-center gap-2">
            <Switch checked={sources[k]} onCheckedChange={(v) => setSources((s) => ({ ...s, [k]: v }))} /> {label}
          </label>
        ))}
      </div>

      <div className="mt-10">
        {!dimension ? (
          <p className="text-muted-foreground">Choose a relationship to explore.</p>
        ) : !ready ? (
          <p className="text-muted-foreground">Select at least one tag.</p>
        ) : isFetching && !data ? (
          <p className="text-sm text-muted-foreground">Looking…</p>
        ) : total === 0 ? (
          <p className="text-muted-foreground">No related artworks{sources.includeCommunity ? "" : " — try turning on Community or Watchlist"}.</p>
        ) : (
          <div className="space-y-12">
            {data!.collection.length > 0 && (
              <section>
                <h2 className="mb-4 text-2xl">From my collection</h2>
                <div className="grid grid-cols-2 gap-x-5 gap-y-8 sm:grid-cols-3 lg:grid-cols-4">{data!.collection.map((a) => <ArtworkCard key={a.id} a={a} />)}</div>
              </section>
            )}
            {data!.watchlist.length > 0 && (
              <section>
                <h2 className="mb-4 text-2xl">From my watchlist</h2>
                <div className="grid grid-cols-2 gap-x-5 gap-y-8 sm:grid-cols-3 lg:grid-cols-4">{data!.watchlist.map((a) => <ArtworkCard key={a.id} a={a} />)}</div>
              </section>
            )}
            {data!.community.length > 0 && (
              <section>
                <h2 className="mb-4 text-2xl">From the community</h2>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{data!.community.map((c) => <CommunityCard key={c.id} c={c} />)}</div>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
