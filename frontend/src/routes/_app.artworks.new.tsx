import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArtworkForm } from "@/components/artmneme/artwork-form";
import { PhotoButton } from "@/components/artmneme/photo-button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { api } from "@/services";
import { emptyDraft, validateNewArtwork, type ArtworkState } from "@/lib/domain";

export const Route = createFileRoute("/_app/artworks/new")({
  head: () => ({
    meta: [
      { title: "Add artwork — ArtMneme" },
      { name: "description", content: "Add an artwork to your collection or watchlist." },
      { property: "og:title", content: "Add artwork — ArtMneme" },
      { property: "og:description", content: "Add an artwork to your collection or watchlist." },
    ],
  }),
  component: NewArtwork,
});

function NewArtwork() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [state, setState] = useState<ArtworkState>("COLLECTION");
  const [photo, setPhoto] = useState<Blob | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-4xl">Add artwork</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Your collection is for artworks you have seen, and needs your photo. Your watchlist is for ones you want to see; a photo is optional. Everything else can be filled in later.
      </p>
      <div className="mt-10">
        <ArtworkForm
          initial={emptyDraft()}
          submitLabel={state === "COLLECTION" ? "Add to collection" : "Add to watchlist"}
          extra={
            <div className="space-y-4">
              <ToggleGroup type="single" variant="outline" className="justify-start" value={state} onValueChange={(v) => v && setState(v as ArtworkState)}>
                <ToggleGroupItem value="COLLECTION">Collection</ToggleGroupItem>
                <ToggleGroupItem value="WATCHLIST">Watchlist</ToggleGroupItem>
              </ToggleGroup>
              <div className="flex items-center gap-4">
                <div className="size-24 overflow-hidden rounded-sm bg-muted">
                  {preview && <img src={preview} alt="Selected" className="h-full w-full object-cover" />}
                </div>
                <div className="space-y-2">
                  <PhotoButton variant="outline" onPhoto={(b) => { setPhoto(b); setPreview(URL.createObjectURL(b)); }}>
                    {photo ? "Change photo" : "Add artwork photo"}
                  </PhotoButton>
                  {photo && <button type="button" className="block text-xs text-muted-foreground underline" onClick={() => { setPhoto(null); setPreview(null); }}>Remove photo</button>}
                </div>
              </div>
            </div>
          }
          onSubmit={async (v) => {
            const invalid = validateNewArtwork(state, !!photo);
            if (invalid) throw new Error(invalid);
            const a = await api.createArtwork(v, state, photo);
            await qc.invalidateQueries({ queryKey: ["artworks"] });
            toast.success(state === "COLLECTION" ? "Added to your collection" : "Added to your watchlist");
            navigate({ to: "/artworks/$id", params: { id: a.id } });
          }}
        />
      </div>
    </div>
  );
}
