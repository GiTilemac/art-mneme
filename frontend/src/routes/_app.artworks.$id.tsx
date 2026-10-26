import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Compass, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { ArtworkForm } from "@/components/artmneme/artwork-form";
import { PhotoButton } from "@/components/artmneme/photo-button";
import { api } from "@/services";
import type { Artwork } from "@/lib/domain";

export const Route = createFileRoute("/_app/artworks/$id")({
  head: () => ({
    meta: [
      { title: "Artwork — ArtMneme" },
      { name: "description", content: "Artwork details and notes." },
      { property: "og:title", content: "Artwork — ArtMneme" },
      { property: "og:description", content: "Artwork details and notes." },
    ],
  }),
  component: ArtworkPage,
});

function MainPhoto({ a }: { a: Artwork }) {
  const url = api.photoUrl(a);
  if (!url)
    return (
      <div className="flex aspect-[4/5] items-center justify-center rounded-sm bg-muted">
        <span className="eyebrow">On your watchlist — not yet seen</span>
      </div>
    );
  return <img src={url} alt="" className="w-full rounded-sm" />;
}

function ArtworkPage() {
  const { id } = Route.useParams();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [editingNotes, setEditingNotes] = useState(false);
  const [notes, setNotes] = useState("");
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
          submitLabel="Save"
          onCancel={() => setEditing(false)}
          onSubmit={async (v) => {
            refresh(await api.updateArtwork(a.id, v));
            toast.success("Saved");
            setEditing(false);
          }}
        />
      </div>
    );

  const rows: [string, string][] = [
    ["Subject", a.subject?.name ?? ""],
    ["Movement", a.movement?.name ?? ""],
    ["Museum", a.museum],
  ];

  return (
    <div className="grid gap-12 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
      <div className="space-y-4">
        <MainPhoto a={a} />
        <PhotoButton variant={state === "COLLECTION" ? "outline" : "default"} size="sm" onPhoto={(b) => run(() => api.setArtworkPhoto(a.id, b), state === "COLLECTION" ? "Photo replaced" : "Moved to your collection")}>
          {state === "COLLECTION" ? "Replace photo" : "I've seen it — add my photo"}
        </PhotoButton>
        {state === "WATCHLIST" && (
          <p className="text-xs text-muted-foreground">
            Adding your own photo moves this artwork into your collection{a.hasPhoto ? " and replaces this one" : ""}.
          </p>
        )}
      </div>

      <div>
        <p className="eyebrow">{state === "COLLECTION" ? "Collection" : "Watchlist"}</p>
        <h1 className="mt-2 text-5xl leading-tight">{a.title || "Untitled"}</h1>
        <p className="mt-2 text-lg text-muted-foreground">
          {[a.artist?.name, a.date?.display].filter(Boolean).join(" · ") || "No artist or date yet"}
        </p>

        <dl className="mt-8 divide-y border-y">
          {rows.map(([k, val]) => (
            <div key={k} className="flex justify-between gap-4 py-2.5 text-sm">
              <dt className="eyebrow pt-0.5">{k}</dt>
              <dd className="text-right">{val || <span className="text-muted-foreground">—</span>}</dd>
            </div>
          ))}
        </dl>

        {a.tags.length > 0 && (
          <div className="mt-5 flex flex-wrap gap-1.5">
            {a.tags.map((t) => <span key={t.id} className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">{t.name}</span>)}
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

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="ghost" size="sm" className="mt-8 text-destructive"><Trash2 /> Delete artwork</Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete this artwork?</AlertDialogTitle>
              <AlertDialogDescription>Its photo and notes are removed permanently.</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={async () => {
                  try {
                    await api.deleteArtwork(a.id);
                  } catch (e) {
                    return void toast.error((e as Error).message);
                  }
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
    </div>
  );
}
