import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { ArtworkCard } from "@/components/artmneme/artwork-card";
import { api, type Dimension } from "@/services";

export const Route = createFileRoute("/_app/artworks/$id_/explore")({
  head: () => ({
    meta: [
      { title: "Explore relationships — ArtMneme" },
      { name: "description", content: "Find artworks related by artist, subject, movement, museum or museum." },
      { property: "og:title", content: "Explore relationships — ArtMneme" },
      { property: "og:description", content: "Find artworks related by artist, subject, movement, museum or museum." },
    ],
  }),
  component: Explore,
});

const DIMS: { key: Dimension; label: string }[] = [
  { key: "artist", label: "Same artist" },
  { key: "subject", label: "Same subject" },
  { key: "movement", label: "Same movement" },
  { key: "museum", label: "Same museum" },
];

function Explore() {
  const { id } = Route.useParams();
  const { data: src } = useQuery({ queryKey: ["artwork", id], queryFn: () => api.getArtwork(id) });
  const [dimension, setDimension] = useState<Dimension | null>(null);
  const [sources, setSources] = useState({ includeCollection: true, includeWatchlist: false });

  const ready = !!src && !!dimension;
  const { data, isFetching } = useQuery({
    queryKey: ["explore", id, dimension, sources],
    queryFn: () => api.explore(id, { by: dimension!, ...sources }),
    enabled: ready,
  });

  if (!src) return null;
  const available: Record<Dimension, boolean> = {
    artist: !!src.artist,
    subject: !!src.subject,
    movement: !!src.movement,
    museum: !!src.museum,
  };
  const total = data ? data.collection.length + data.watchlist.length : 0;

  return (
    <div>
      <Link to="/artworks/$id" params={{ id }} className="inline-flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="size-4" /> {src.title || "Untitled"}
      </Link>
      <h1 className="mt-4 text-4xl">Explore relationships</h1>

      <div className="mt-8 flex flex-wrap gap-2">
        {DIMS.map((d) => (
          <Button key={d.key} variant={dimension === d.key ? "default" : "outline"} size="sm" disabled={!available[d.key]} onClick={() => setDimension(d.key)}>
            {d.label}
          </Button>
        ))}
      </div>

      <div className="mt-6 flex flex-wrap gap-6 border-y py-3 text-sm">
        {([["includeCollection", "My collection"], ["includeWatchlist", "Watchlist"]] as const).map(([k, label]) => (
          <label key={k} className="flex items-center gap-2">
            <Switch checked={sources[k]} onCheckedChange={(v) => setSources((s) => ({ ...s, [k]: v }))} /> {label}
          </label>
        ))}
      </div>

      <div className="mt-10">
        {!dimension ? (
          <p className="text-muted-foreground">Choose a relationship to explore.</p>
        ) : isFetching && !data ? (
          <p className="text-sm text-muted-foreground">Looking…</p>
        ) : total === 0 ? (
          <p className="text-muted-foreground">No related artworks{sources.includeWatchlist ? "" : " — try turning on Watchlist"}.</p>
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
          </div>
        )}
      </div>
    </div>
  );
}
