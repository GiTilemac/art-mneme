import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Compass, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { ArtworkForm } from "@/components/artmneme/artwork-form";
import { ArtworkThumb } from "@/components/artmneme/artwork-card";
import { PhotoButton } from "@/components/artmneme/photo-button";
import { useEntities, usePhotoUrl } from "@/hooks/use-artmneme";
import * as api from "@/lib/api";
import { canBeDiscoverable, formatDate, type Artwork } from "@/lib/domain";

export const Route = createFileRoute("/_app/artworks/$id")({
  head: () => ({
    meta: [
      { title: "Artwork — ArtMneme" },
      { name: "description", content: "Artwork details, notes and detail photos." },
      { property: "og:title", content: "Artwork — ArtMneme" },
      { property: "og:description", content: "Artwork details, notes and detail photos." },
    ],
  }),
  component: ArtworkPage,
});

function MainPhoto({ photoId }: { photoId: string | null }) {
  const url = usePhotoUrl(photoId);
  if (!url)
    return (
      <div className="flex aspect-[4/5] items-center justify-center rounded-sm bg-muted">
        <span className="eyebrow">On your watchlist — not yet seen</span>
      </div>
    );
  return <img src={url} alt="" className="w-full rounded-sm" />;
}

function DetailPhoto({ photoId, onOpen, onDelete }: { photoId: string; onOpen: () => void; onDelete: () => void }) {
  return (
    <div className="relative">
      <button type="button" onClick={onOpen} className="block w-full" aria-label="View detail photo">
        <ArtworkThumb photoId={photoId} className="aspect-square rounded-sm" />
      </button>
      <button type="button" onClick={onDelete} aria-label="Delete detail photo" className="absolute right-1 top-1 rounded-full bg-background/90 p-1">
        <X className="size-3.5" />
      </button>
    </div>
  );
}

function Viewer({ photoId, onClose }: { photoId: string | null; onClose: () => void }) {
  const url = usePhotoUrl(photoId);
  return (
    <Dialog open={!!photoId} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-4xl p-2">
        <DialogTitle className="sr-only">Detail photo</DialogTitle>
        {url && <img src={url} alt="Detail" className="max-h-[80vh] w-full object-contain" />}
      </DialogContent>
    </Dialog>
  );
}

function ArtworkPage() {
  const { id } = Route.useParams();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const ent = useEntities();
  const [editing, setEditing] = useState(false);
  const [editingNotes, setEditingNotes] = useState(false);
  const [notes, setNotes] = useState("");
  const [viewing, setViewing] = useState<string | null>(null);
  const { data: a, error } = useQuery({ queryKey: ["artwork", id], queryFn: () => api.getArtwork(id) });

  if (error) return <p className="text-muted-foreground">{(error as Error).message}</p>;
  if (!a) return null;

  const refresh = (next: Artwork) => {
    qc.setQueryData(["artwork", id], { ...next });
    qc.invalidateQueries({ queryKey: ["artworks"] });
  };
  const run = async (fn: () => Promise<Artwork>, ok?: string) => {
    try {
      refresh(await fn());
      if (ok) toast.success(ok);
    } catch (e) {
      toast.error((e as Error).message);
    }
  };
  const state = a.state;

  if (editing)
    return (
      <div className="mx-auto max-w-2xl">
        <h1 className="mb-10 text-4xl">Edit artwork</h1>
        <ArtworkForm
          initial={a}
          excludeId={a.id}
          submitLabel="Save"
          onCancel={() => setEditing(false)}
          onSubmit={async (v) => {
            await run(() => api.updateArtwork(a.id, v), "Saved");
            setEditing(false);
          }}
        />
      </div>
    );

  const rows: [string, string][] = [
    ["Subject", ent.subjectName(a.subjectId)],
    ["Movement", ent.movementName(a.movementId)],
    ["Museum", a.museum],
  ];

  return (
    <div className="grid gap-12 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
      <div className="space-y-4">
        <MainPhoto photoId={a.photoId} />
        <PhotoButton variant={state === "COLLECTION" ? "outline" : "default"} size="sm" onPhoto={(b) => run(() => api.setArtworkPhoto(a.id, b), state === "COLLECTION" ? "Photo replaced" : "Moved to your collection")}>
          {state === "COLLECTION" ? "Replace photo" : "I've seen it — add my photo"}
        </PhotoButton>
        {state === "WATCHLIST" && a.photoId && (
          <p className="text-xs text-muted-foreground">Adding your own photo moves it to your collection and replaces this one.</p>
        )}
      </div>

      <div>
        <p className="eyebrow">{state === "COLLECTION" ? "Collection" : "Watchlist"}</p>
        <h1 className="mt-2 text-5xl leading-tight">{a.title || "Untitled"}</h1>
        <p className="mt-2 text-lg text-muted-foreground">
          {[ent.artistName(a.artistId), formatDate(a.date)].filter(Boolean).join(" · ") || "No artist or date yet"}
        </p>

        <dl className="mt-8 divide-y border-y">
          {rows.map(([k, val]) => (
            <div key={k} className="flex justify-between gap-4 py-2.5 text-sm">
              <dt className="eyebrow pt-0.5">{k}</dt>
              <dd className="text-right">{val || <span className="text-muted-foreground">—</span>}</dd>
            </div>
          ))}
        </dl>

        {a.tagIds.length > 0 && (
          <div className="mt-5 flex flex-wrap gap-1.5">
            {a.tagIds.map((t) => <span key={t} className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">{ent.tagName(t)}</span>)}
          </div>
        )}

        <div className="mt-6 flex flex-wrap gap-2">
          <Button asChild><Link to="/artworks/$id/explore" params={{ id: a.id }}><Compass /> Explore relationships</Link></Button>
          <Button variant="outline" onClick={() => setEditing(true)}>Edit details</Button>
        </div>

        <section className="mt-10">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl">Notes</h2>
            {!editingNotes && <Button variant="ghost" size="sm" onClick={() => { setNotes(a.notes); setEditingNotes(true); }}>Edit notes</Button>}
          </div>
          {editingNotes ? (
            <div className="mt-2 space-y-2">
              <Textarea rows={5} value={notes} onChange={(e) => setNotes(e.target.value)} />
              <div className="flex gap-2">
                <Button size="sm" onClick={async () => { await run(() => api.updateArtwork(a.id, { notes })); setEditingNotes(false); }}>Save</Button>
                <Button size="sm" variant="ghost" onClick={() => setEditingNotes(false)}>Cancel</Button>
              </div>
            </div>
          ) : (
            <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">{a.notes || "No notes yet."}</p>
          )}
        </section>

        <section className="mt-10">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl">Details</h2>
            <PhotoButton variant="ghost" size="sm" onPhoto={(b) => run(() => api.addDetailPhoto(a.id, b))}>Add detail photo</PhotoButton>
          </div>
          {a.detailPhotoIds.length ? (
            <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-4">
              {a.detailPhotoIds.map((p) => (
                <DetailPhoto key={p} photoId={p} onOpen={() => setViewing(p)} onDelete={() => run(() => api.deleteDetailPhoto(a.id, p))} />
              ))}
            </div>
          ) : (
            <p className="mt-2 text-sm text-muted-foreground">Brushstrokes, signatures, frames — close-ups live here.</p>
          )}
        </section>

        <section className="mt-10 space-y-4 rounded-md border bg-card p-5">
          <h2 className="text-2xl">Sharing</h2>
          <label className="flex items-start justify-between gap-4">
            <span className="text-sm">
              Discoverable
              <span className="block text-xs text-muted-foreground">
                Others can find title, artist, date, subject, movement, museum and tags while exploring. Photos are never shared.
                {!canBeDiscoverable(a) && " Requires title, artist and date."}
              </span>
            </span>
            <Switch checked={a.discoverable} onCheckedChange={(v) => run(() => api.updateArtwork(a.id, { discoverable: v }))} />
          </label>
          <label className="flex items-start justify-between gap-4">
            <span className="text-sm">
              Share notes
              <span className="block text-xs text-muted-foreground">Notes stay private unless you turn this on.</span>
            </span>
            <Switch checked={a.notesDiscoverable} onCheckedChange={(v) => run(() => api.updateArtwork(a.id, { notesDiscoverable: v }))} />
          </label>
        </section>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="ghost" size="sm" className="mt-8 text-destructive"><Trash2 /> Delete artwork</Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete this artwork?</AlertDialogTitle>
              <AlertDialogDescription>Its photos and notes are removed permanently.</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={async () => {
                  await api.deleteArtwork(a.id);
                  await qc.invalidateQueries({ queryKey: ["artworks"] });
                  navigate({ to: state === "COLLECTION" ? "/collection" : "/watchlist" });
                }}
              >
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
      <Viewer photoId={viewing} onClose={() => setViewing(null)} />
    </div>
  );
}
