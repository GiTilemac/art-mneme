import { useState, type FormEvent, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { EntityPicker } from "./entity-picker";
import { TagInput } from "./tag-input";
import { api } from "@/services";
import { formatDate, toInput, type ArtworkDate, type ArtworkDraft, type ArtworkInput } from "@/lib/domain";

function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <div className="space-y-1.5">
      <Label className="eyebrow">{label}</Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

function DateInput({ value, onChange }: { value: ArtworkDate | null; onChange: (d: ArtworkDate | null) => void }) {
  const [from, setFrom] = useState(value ? String(value.fromYear) : "");
  const [to, setTo] = useState(value?.toYear != null ? String(value.toYear) : "");
  const [circa, setCirca] = useState(value?.circa ?? false);
  const [bc, setBc] = useState(value?.bc ?? false);
  const emit = (f: string, t: string, c: boolean, b: boolean) => {
    const fy = parseInt(f, 10);
    const ty = parseInt(t, 10);
    onChange(Number.isFinite(fy) && fy > 0 ? { fromYear: fy, toYear: Number.isFinite(ty) && ty > 0 ? ty : null, circa: c, bc: b } : null);
  };
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Input inputMode="numeric" className="w-24" placeholder="From" value={from} onChange={(e) => { setFrom(e.target.value); emit(e.target.value, to, circa, bc); }} />
        <span className="text-muted-foreground">–</span>
        <Input inputMode="numeric" className="w-24" placeholder="To" value={to} onChange={(e) => { setTo(e.target.value); emit(from, e.target.value, circa, bc); }} />
        <label className="flex items-center gap-1.5 text-sm">
          <Checkbox checked={circa} onCheckedChange={(v) => { setCirca(!!v); emit(from, to, !!v, bc); }} /> Circa
        </label>
        <label className="flex items-center gap-1.5 text-sm">
          <Checkbox checked={bc} onCheckedChange={(v) => { setBc(!!v); emit(from, to, circa, !!v); }} /> BC
        </label>
      </div>
      {value && <p className="text-xs text-muted-foreground">Shown as <span className="text-foreground">{formatDate(value)}</span></p>}
    </div>
  );
}

export function ArtworkForm({
  initial,
  excludeId,
  submitLabel,
  onSubmit,
  onCancel,
  extra,
}: {
  initial: ArtworkDraft;
  excludeId?: string;
  submitLabel: string;
  onSubmit: (v: ArtworkInput) => Promise<void>;
  onCancel?: () => void;
  extra?: ReactNode;
}) {
  const [v, setV] = useState<ArtworkDraft>(initial);
  const [busy, setBusy] = useState(false);
  const set = <K extends keyof ArtworkDraft>(k: K, val: ArtworkDraft[K]) => setV((p) => ({ ...p, [k]: val }));

  const { data: dups = [] } = useQuery({
    queryKey: ["duplicates", v.title, v.artist?.id, v.date, excludeId],
    queryFn: () => api.findDuplicates(toInput(v), excludeId),
  });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await onSubmit(toInput(v));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-6">
      {extra}
      <Field label="Title">
        <Input value={v.title} onChange={(e) => set("title", e.target.value)} placeholder="The Night Watch" />
      </Field>
      <div className="grid gap-6 sm:grid-cols-2">
        <Field label="Artist">
          <EntityPicker kind="artists" value={v.artist} onChange={(e) => set("artist", e)} placeholder="Search or create" />
        </Field>
        <Field label="Date">
          <DateInput value={v.date} onChange={(d) => set("date", d)} />
        </Field>
      </div>
      {dups.length > 0 && (
        <div className="flex gap-2 rounded-md bg-warning p-3 text-sm text-warning-foreground">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" />
          <span>You already have an artwork with this title, artist and date. You can still save it.</span>
        </div>
      )}
      <div className="grid gap-6 sm:grid-cols-2">
        <Field label="Subject">
          <EntityPicker kind="subjects" value={v.subject} onChange={(e) => set("subject", e)} placeholder="Search or create" />
        </Field>
        <Field label="Movement">
          <EntityPicker kind="movements" value={v.movement} onChange={(e) => set("movement", e)} placeholder="Search or create" />
        </Field>
      </div>
      <Field label="Museum" hint="Where you encountered it.">
        <Input value={v.museum} onChange={(e) => set("museum", e.target.value)} placeholder="Louvre" />
      </Field>
      <Field label="Tags">
        <TagInput value={v.tags} onChange={(tags) => set("tags", tags)} />
      </Field>
      <Field label="Notes">
        <Textarea rows={4} value={v.notes} onChange={(e) => set("notes", e.target.value)} />
      </Field>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={busy}>{busy ? "Saving…" : submitLabel}</Button>
        {onCancel && <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>}
      </div>
    </form>
  );
}
