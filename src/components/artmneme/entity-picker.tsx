import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import * as api from "@/lib/api";
import { entitiesKey } from "@/hooks/use-artmneme";
import { normalizeName, type Entity, type EntityKind } from "@/lib/domain";

/** Select an existing shared entry or create a new one. Tap-friendly, no hover. */
export function EntityPicker({
  kind,
  options,
  value,
  onChange,
  placeholder,
}: {
  kind: Exclude<EntityKind, "tags">;
  options: Entity[];
  value: string | null;
  onChange: (id: string | null) => void;
  placeholder?: string;
}) {
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const selected = options.find((o) => o.id === value);

  if (selected)
    return (
      <div className="flex h-9 items-center justify-between rounded-md border border-input bg-card px-3 text-sm">
        <span>{selected.name}</span>
        <button type="button" aria-label="Clear" onClick={() => onChange(null)} className="text-muted-foreground">
          <X className="size-4" />
        </button>
      </div>
    );

  const q = normalizeName(text);
  const matches = q ? options.filter((o) => o.name.toLowerCase().includes(q)).slice(0, 8) : options.slice(0, 8);
  const exact = options.some((o) => normalizeName(o.name) === q);

  async function create() {
    try {
      const e = await api.createEntity(kind, text);
      await qc.invalidateQueries({ queryKey: entitiesKey });
      onChange(e.id);
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
      {open && (matches.length > 0 || (q && !exact)) && (
        <div className="absolute z-20 mt-1 w-full rounded-md border bg-popover p-1 shadow-sm">
          {matches.map((o) => (
            <button
              key={o.id}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                onChange(o.id);
                setText("");
                setOpen(false);
              }}
              className="block w-full rounded-sm px-2 py-1.5 text-left text-sm active:bg-accent"
            >
              {o.name}
            </button>
          ))}
          {q && !exact && (
            <Button type="button" variant="ghost" size="sm" className="w-full justify-start text-primary" onMouseDown={(e) => e.preventDefault()} onClick={create}>
              Create “{text.trim()}”
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
