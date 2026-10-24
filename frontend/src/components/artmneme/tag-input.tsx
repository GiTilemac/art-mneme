import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api } from "@/services";
import { normalizeName, validateTag, type Entity } from "@/lib/domain";

export function TagInput({
  value,
  onChange,
  allowCreate = true,
}: {
  value: Entity[];
  onChange: (tags: Entity[]) => void;
  allowCreate?: boolean;
}) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { data: suggestions = [] } = useQuery({
    queryKey: ["tag-suggestions", text],
    queryFn: () => api.suggestTags(text),
  });

  async function add(name: string) {
    const existing = suggestions.find((t) => t.name === normalizeName(name));
    if (!existing && !allowCreate) return setError("Pick an existing tag.");
    const err = validateTag(name);
    if (err) return setError(err);
    try {
      const t = existing ?? (await api.createEntity("tags", name));
      if (!value.some((v) => v.id === t.id)) onChange([...value, t]);
      setText("");
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const shown = suggestions.filter((s) => !value.some((v) => v.id === s.id)).slice(0, 6);

  return (
    <div className="space-y-2">
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {value.map((t) => (
            <span key={t.id} className="inline-flex items-center gap-1 rounded-full bg-secondary px-2.5 py-0.5 text-xs">
              {t.name}
              <button type="button" aria-label={`Remove ${t.name}`} onClick={() => onChange(value.filter((v) => v.id !== t.id))}>
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <Input
          value={text}
          placeholder="Add a tag"
          onChange={(e) => {
            setText(e.target.value);
            setError(null);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              if (text.trim()) add(text);
            }
          }}
        />
        <Button type="button" variant="outline" onClick={() => text.trim() && add(text)}>
          Add
        </Button>
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
      {shown.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {shown.map((s) => (
            <button key={s.id} type="button" onClick={() => add(s.name)} className="rounded-full border px-2.5 py-0.5 text-xs text-muted-foreground">
              + {s.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
