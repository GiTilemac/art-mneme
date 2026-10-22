import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import * as api from "@/lib/api";
import type { Entity } from "@/lib/domain";

export const entitiesKey = ["entities"] as const;

export function useEntities() {
  const q = useQuery({ queryKey: entitiesKey, queryFn: api.getEntities });
  const d = q.data ?? { artists: [], movements: [], subjects: [], tags: [] };
  const name = (list: Entity[], id: string | null | undefined) =>
    id ? (list.find((e) => e.id === id)?.name ?? "") : "";
  return {
    ...d,
    artistName: (id?: string | null) => name(d.artists, id),
    movementName: (id?: string | null) => name(d.movements, id),
    subjectName: (id?: string | null) => name(d.subjects, id),
    tagName: (id?: string | null) => name(d.tags, id),
  };
}

export function usePhotoUrl(photoId: string | null | undefined) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!photoId) return setUrl(null);
    let objectUrl: string | null = null;
    let live = true;
    api.getPhoto(photoId).then((b) => {
      if (!live || !b) return;
      objectUrl = URL.createObjectURL(b);
      setUrl(objectUrl);
    });
    return () => {
      live = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [photoId]);
  return url;
}
