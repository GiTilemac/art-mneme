import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api } from "@/services";
import { normalizeName, type Entity, type EntityKind } from "@/lib/domain";

/** Search the shared entries and select one, or create a new one. Tap-friendly, no hover. */
export function EntityPicker({
  kind,
  value,
  onChange,
  placeholder,
  allowCreate = true,
}: {
  kind: Exclude<EntityKind, "tags">;
  value: Entity | null;
  onChange: (e: Entity | null) => void;
  placeholder?: string;
  allowCreate?: boolean;
}) {
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const { data } = useQuery({
    queryKey: ["entities", kind, text],
    queryFn: () => api.searchEntities(kind, text),
    enabled: open && !value,
  });
  if (value)
    return (
      <div className="flex h-9 items-center justify-between rounded-md border border-input bg-card px-3 text-sm">
        <span>{value.name}</span>
        <button type="button" aria-label="Clear" onClick={() => onChange(null)} className="text-muted-foreground">
          <X className="size-4" />
        </button>
      </div>
    );

  const q = normalizeName(text);
  const options = data?.items ?? [];
  const matches = options.slice(0, 8);
  const exact = options.some((o) => normalizeName(o.name) === q);
  const canCreate = allowCreate && !!q && !exact;

  async function create() {
    try {
      onChange(await api.createEntity(kind, text));
      setText("");
      setOpen(false);
    } catch (err) {
      toast.error((err as Error).message);
    }
  }

  return (
    <div className="relative">
      <Input
        value={text}
        placeholder={placeholder}
        onChange={(e) => {
          setText(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      />
      {open && (matches.length > 0 || canCreate) && (
        <div className="absolute z-20 mt-1 w-full rounded-md border bg-popover p-1 shadow-sm">
          {matches.map((o) => (
            <button
              key={o.id}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                onChange(o);
                setText("");
                setOpen(false);
              }}
              className="block w-full rounded-sm px-2 py-1.5 text-left text-sm active:bg-accent"
            >
              {o.name}
            </button>
          ))}
          {canCreate && (
            <Button type="button" variant="ghost" size="sm" className="w-full justify-start text-primary" onMouseDown={(e) => e.preventDefault()} onClick={create}>
              Create “{text.trim()}”
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
