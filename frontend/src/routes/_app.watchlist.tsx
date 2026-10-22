import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { ArtworkBrowser, parseBrowseSearch } from "@/components/artmneme/artwork-browser";

export const Route = createFileRoute("/_app/watchlist")({
  validateSearch: parseBrowseSearch,
  head: () => ({
    meta: [
      { title: "Watchlist — ArtMneme" },
      { name: "description", content: "Artworks you hope to see in person." },
      { property: "og:title", content: "Watchlist — ArtMneme" },
      { property: "og:description", content: "Artworks you hope to see in person." },
    ],
  }),
  component: () => {
    const search = Route.useSearch();
    const navigate = useNavigate({ from: "/watchlist" });
    return (
      <>
        <h1 className="text-4xl">Watchlist</h1>
        <p className="mb-8 mt-2 text-sm text-muted-foreground">Add a photo once you've seen one in person and it moves to your collection.</p>
        <ArtworkBrowser state="WATCHLIST" search={search} onChange={(p) => navigate({ search: (prev) => ({ ...prev, ...p }), replace: true })} />
      </>
    );
  },
});
