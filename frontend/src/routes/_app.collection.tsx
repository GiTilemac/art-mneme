import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { ArtworkBrowser, parseBrowseSearch } from "@/components/artmneme/artwork-browser";

export const Route = createFileRoute("/_app/collection")({
  validateSearch: parseBrowseSearch,
  head: () => ({
    meta: [
      { title: "My collection — ArtMneme" },
      { name: "description", content: "Artworks you have personally encountered." },
      { property: "og:title", content: "My collection — ArtMneme" },
      { property: "og:description", content: "Artworks you have personally encountered." },
    ],
  }),
  component: () => {
    const search = Route.useSearch();
    const navigate = useNavigate({ from: "/collection" });
    return (
      <>
        <h1 className="mb-8 text-4xl">Collection</h1>
        <ArtworkBrowser state="COLLECTION" search={search} onChange={(p) => navigate({ search: (prev) => ({ ...prev, ...p }), replace: true })} />
      </>
    );
  },
});
