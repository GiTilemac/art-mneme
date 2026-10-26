/** The real backend under /api, shaped after openapi.yaml. Ids are integers there and strings in the app. */
import type { Artwork, ArtworkDate, ArtworkInput, ArtworkState, Entity, EntityKind } from "@/lib/domain";
import type { ListParams, Page, Services, User } from "./types";

type Json = Record<string, any>;

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const res = await fetch(`/api${path}`, { credentials: "include", ...init });
  if (res.ok) return res;
  const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
  if (res.status === 401 && !path.startsWith("/auth/") && typeof window !== "undefined")
    window.location.assign("/auth");
  throw new Error(typeof body?.detail === "string" ? body.detail : "Something went wrong. Please try again.");
}

const send = (path: string, method: string, body: unknown) =>
  request(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

const query = (params: [string, string | number | boolean | undefined][]) => {
  const q = new URLSearchParams();
  for (const [k, v] of params) if (v !== undefined && v !== "") q.append(k, String(v));
  const s = q.toString();
  return s ? `?${s}` : "";
};

const toEntity = (e: Json): Entity => ({ id: String(e["id"]), name: e["name"] });
const toEntityOrNull = (e: Json | null) => (e ? toEntity(e) : null);
const toUser = (u: Json): User => ({ id: String(u["id"]), email: u["email"] });
const id = (s: string) => Number(s);

function toArtwork(a: Json): Artwork {
  const d = a["date"] as Json | null;
  return {
    id: String(a["id"]),
    state: a["state"],
    title: a["title"],
    artist: toEntityOrNull(a["artist"]),
    date: d && {
      fromYear: d["from_year"],
      toYear: d["to_year"],
      circa: d["circa"],
      fromBc: d["from_bc"],
      toBc: d["to_bc"],
      display: d["display"],
    },
    subject: toEntityOrNull(a["subject"]),
    movement: toEntityOrNull(a["movement"]),
    museum: a["museum"],
    tags: (a["tags"] as Json[]).map(toEntity),
    notes: a["notes"],
    hasPhoto: a["has_photo"],
    photoVersion: String(a["photo_version"]),
    createdAt: a["created_at"],
  };
}

const dateBody = (d: ArtworkDate | null) =>
  d && { from_year: d.fromYear, to_year: d.toYear, circa: d.circa, from_bc: d.fromBc, to_bc: d.toBc };

/** Only the fields present are sent, with the backend's names. */
function artworkBody(p: Partial<ArtworkInput>): Json {
  const out: Json = {};
  if (p.title !== undefined) out["title"] = p.title;
  if (p.artistId !== undefined) out["artist_id"] = p.artistId && id(p.artistId);
  if (p.date !== undefined) out["date"] = dateBody(p.date);
  if (p.subjectId !== undefined) out["subject_id"] = p.subjectId && id(p.subjectId);
  if (p.movementId !== undefined) out["movement_id"] = p.movementId && id(p.movementId);
  if (p.museum !== undefined) out["museum"] = p.museum;
  if (p.tagIds !== undefined) out["tag_ids"] = p.tagIds.map(id);
  if (p.notes !== undefined) out["notes"] = p.notes;
  return out;
}

const toPage = <T>(p: Json, map: (x: Json) => T): Page<T> => ({
  items: (p["items"] as Json[]).map(map),
  total: p["total"],
  page: p["page"],
  pageSize: p["page_size"],
});

const photoForm = (photo: Blob) => {
  const form = new FormData();
  form.append("photo", photo, "photo.jpg");
  return form;
};

export const httpServices: Services = {
  async register(email, password) {
    return toUser(await (await send("/auth/register", "POST", { email, password })).json());
  },
  async login(email, password) {
    return toUser(await (await send("/auth/login", "POST", { email, password })).json());
  },
  async logout() {
    await request("/auth/logout", { method: "POST" });
  },
  async me() {
    try {
      return toUser(await (await request("/auth/me")).json());
    } catch (e) {
      // Not logged in is an answer here, not an error.
      return (e as Error).message === "Please sign in again." ? null : Promise.reject(e);
    }
  },

  async searchEntities(kind, q, page = 1) {
    return toPage(await (await request(`/${kind}${query([["q", q], ["page", page]])}`)).json(), toEntity);
  },
  async createEntity(kind: EntityKind, name) {
    return toEntity(await (await send(`/${kind}`, "POST", { name })).json());
  },
  async suggestTags(q) {
    return ((await (await request(`/tags/suggestions${query([["q", q]])}`)).json()) as Json[]).map(toEntity);
  },

  async listArtworks(p: ListParams) {
    const params = query([
      ["state", p.state],
      ["q", p.q],
      ["artist_id", p.artistId],
      ["movement_id", p.movementId],
      ["museum", p.museum],
      ...(p.tagIds ?? []).map((t): [string, string] => ["tag_ids", t]),
      ["from_year", p.fromYear],
      ["from_bc", p.fromYear === undefined ? undefined : !!p.fromBc],
      ["to_year", p.toYear],
      ["to_bc", p.toYear === undefined ? undefined : !!p.toBc],
      ["page", p.page],
    ]);
    return toPage(await (await request(`/artworks${params}`)).json(), toArtwork);
  },
  async createArtwork(input: ArtworkInput, state: ArtworkState, photo) {
    const form = new FormData();
    form.append("artwork", JSON.stringify(artworkBody(input)));
    form.append("state", state);
    if (photo) form.append("photo", photo, "photo.jpg");
    return toArtwork(await (await request("/artworks", { method: "POST", body: form })).json());
  },
  async getArtwork(artworkId) {
    return toArtwork(await (await request(`/artworks/${artworkId}`)).json());
  },
  async updateArtwork(artworkId, patch) {
    return toArtwork(await (await send(`/artworks/${artworkId}`, "PATCH", artworkBody(patch))).json());
  },
  async deleteArtwork(artworkId) {
    await request(`/artworks/${artworkId}`, { method: "DELETE" });
  },

  async setArtworkPhoto(artworkId, photo) {
    return toArtwork(
      await (await request(`/artworks/${artworkId}/photo`, { method: "PUT", body: photoForm(photo) })).json(),
    );
  },
  photoUrl: (a) => (a.hasPhoto ? `/api/artworks/${a.id}/photo?v=${encodeURIComponent(a.photoVersion)}` : null),

  async explore(artworkId, p) {
    const params = query([
      ["by", p.by],
      ["include_collection", p.includeCollection],
      ["include_watchlist", p.includeWatchlist],
    ]);
    const r = (await (await request(`/artworks/${artworkId}/related${params}`)).json()) as Json;
    return { collection: r["collection"].map(toArtwork), watchlist: r["watchlist"].map(toArtwork) };
  },
};
