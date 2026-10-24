import { Link } from "@tanstack/react-router";
import { usePhotoUrl } from "@/hooks/use-artmneme";
import { api } from "@/services";
import { formatDate, type Artwork } from "@/lib/domain";

export function ArtworkThumb({ a, className = "" }: { a: Artwork; className?: string }) {
  const url = usePhotoUrl(a.hasPhoto ? () => api.getArtworkPhoto(a.id) : null, a);
  return (
    <div className={`overflow-hidden bg-muted ${className}`}>
      {url ? (
        <img src={url} alt="" className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full w-full items-center justify-center eyebrow">{a.hasPhoto ? "" : "Not yet seen"}</div>
      )}
    </div>
  );
}

export function ArtworkCard({ a, view = "grid" }: { a: Artwork; view?: "grid" | "list" }) {
  const meta = [a.artist?.name, formatDate(a.date)].filter(Boolean).join(" · ");
  if (view === "list")
    return (
      <Link to="/artworks/$id" params={{ id: a.id }} className="flex items-center gap-4 border-b py-3">
        <ArtworkThumb a={a} className="size-14 shrink-0 rounded-sm" />
        <div className="min-w-0">
          <p className="truncate font-display text-lg">{a.title || "Untitled"}</p>
          <p className="truncate text-sm text-muted-foreground">{meta}</p>
        </div>
      </Link>
    );
  return (
    <Link to="/artworks/$id" params={{ id: a.id }} className="group block">
      <ArtworkThumb a={a} className="aspect-[4/5] rounded-sm" />
      <p className="mt-3 font-display text-lg leading-tight">{a.title || "Untitled"}</p>
      <p className="mt-0.5 text-sm text-muted-foreground">{meta}</p>
    </Link>
  );
}
