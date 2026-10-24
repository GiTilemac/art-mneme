import { useEffect, useState } from "react";

/** Object URL for a photo loaded through the services layer. Reloads when `key` changes. */
export function usePhotoUrl(load: (() => Promise<Blob | null>) | null, key: unknown) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!load) return setUrl(null);
    let objectUrl: string | null = null;
    let live = true;
    load().then((b) => {
      if (!live || !b) return;
      objectUrl = URL.createObjectURL(b);
      setUrl(objectUrl);
    });
    return () => {
      live = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
    // `load` is a new function on every render; `key` says when the photo changed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return url;
}
