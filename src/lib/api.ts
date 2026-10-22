/**
 * MOCK BACKEND. Every function here is async and shaped like a future HTTP call.
 * Data lives in localStorage (records) and IndexedDB (photos) in this browser only.
 * Replace the bodies with real fetch() calls when the real backend exists;
 * keep the signatures so the UI does not change.
 */
import {
  artworkState,
  canBeDiscoverable,
  collapse,
  isDuplicate,
  normalizeName,
  PAGE_SIZE,
  TAG_SUGGESTION_MIN_USES,
  validatePassword,
  validateTag,
  yearSpan,
  type Artwork,
  type ArtworkInput,
  type ArtworkState,
  type CommunityArtwork,
  type Entity,
  type EntityKind,
} from "./domain";

export type UsageEventType =
  | "sign_in"
  | "artwork_created"
  | "artwork_creation_failed"
  | "exploration"
  | "discoverable_enabled"
  | "watchlist_converted";

interface Db {
  users: { id: string; email: string; password: string }[];
  artists: Entity[];
  movements: Entity[];
  subjects: Entity[];
  tags: Entity[];
  artworks: Artwork[];
  events: { type: UsageEventType; userId: string; at: string }[];
}

export interface Session {
  userId: string;
  email: string;
  expiresAt: number;
}

const DB_KEY = "artmneme-db-v1";
const SESSION_KEY = "artmneme-session";
const SESSION_MS = 30 * 24 * 60 * 60 * 1000;
const uid = () => crypto.randomUUID();
const wait = <T>(v: T, ms = 120) => new Promise<T>((r) => setTimeout(() => r(v), ms));

// ---------- storage ----------
function load(): Db {
  const raw = localStorage.getItem(DB_KEY);
  if (raw) return JSON.parse(raw) as Db;
  const db = seed();
  save(db);
  return db;
}
const save = (db: Db) => localStorage.setItem(DB_KEY, JSON.stringify(db));

function idb(): Promise<IDBDatabase> {
  return new Promise((res, rej) => {
    const r = indexedDB.open("artmneme-photos", 1);
    r.onupgradeneeded = () => r.result.createObjectStore("photos");
    r.onsuccess = () => res(r.result);
    r.onerror = () => rej(r.error);
  });
}
async function photoTx<T>(mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest | void) {
  const db = await idb();
  return new Promise<T>((res, rej) => {
    const tx = db.transaction("photos", mode);
    const req = fn(tx.objectStore("photos"));
    tx.oncomplete = () => res((req ? req.result : undefined) as T);
    tx.onerror = () => rej(tx.error);
  });
}
const putPhoto = async (blob: Blob) => {
  const id = uid();
  await photoTx("readwrite", (s) => void s.put(blob, id));
  return id;
};
const removePhoto = (id: string) => photoTx("readwrite", (s) => void s.delete(id));

// ---------- auth ----------
export function getSessionSync(): Session | null {
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  const s = JSON.parse(raw) as Session;
  if (s.expiresAt < Date.now()) {
    localStorage.removeItem(SESSION_KEY);
    return null;
  }
  // Rolling 30 days: every use restarts the clock.
  s.expiresAt = Date.now() + SESSION_MS;
  localStorage.setItem(SESSION_KEY, JSON.stringify(s));
  return s;
}
function me(): string {
  const s = getSessionSync();
  if (!s) throw new Error("Please sign in again.");
  return s.userId;
}
function startSession(u: { id: string; email: string }) {
  const s: Session = { userId: u.id, email: u.email, expiresAt: Date.now() + SESSION_MS };
  localStorage.setItem(SESSION_KEY, JSON.stringify(s));
  return s;
}
function track(db: Db, type: UsageEventType, userId: string) {
  db.events.push({ type, userId, at: new Date().toISOString() });
}

export async function signUp(email: string, password: string) {
  const e = email.trim().toLowerCase();
  if (!/^\S+@\S+\.\S+$/.test(e)) throw new Error("Enter a valid email address.");
  const pwErr = validatePassword(password);
  if (pwErr) throw new Error(pwErr);
  const db = load();
  if (db.users.some((u) => u.email === e)) throw new Error("An account with this email already exists.");
  const u = { id: uid(), email: e, password };
  db.users.push(u);
  track(db, "sign_in", u.id);
  save(db);
  return wait(startSession(u));
}

export async function signIn(email: string, password: string) {
  const db = load();
  const u = db.users.find((x) => x.email === email.trim().toLowerCase() && x.password === password);
  if (!u) throw new Error("Email or password is incorrect.");
  track(db, "sign_in", u.id);
  save(db);
  return wait(startSession(u));
}

export async function signOut() {
  localStorage.removeItem(SESSION_KEY);
  return wait(undefined);
}

// ---------- shared entities ----------
export interface Entities {
  artists: Entity[];
  movements: Entity[];
  subjects: Entity[];
  tags: Entity[];
}
export async function getEntities(): Promise<Entities> {
  const { artists, movements, subjects, tags } = load();
  const sort = (l: Entity[]) => [...l].sort((a, b) => a.name.localeCompare(b.name));
  return wait({ artists: sort(artists), movements: sort(movements), subjects: sort(subjects), tags });
}

/** Select-or-create. Matching an existing name (case-insensitive) returns it. */
export async function createEntity(kind: EntityKind, name: string): Promise<Entity> {
  const clean = collapse(name);
  if (!clean) throw new Error("Name cannot be empty.");
  if (kind === "tags") {
    const err = validateTag(clean);
    if (err) throw new Error(err);
  }
  const db = load();
  const existing = db[kind].find((e) => normalizeName(e.name) === normalizeName(clean));
  if (existing) return wait(existing);
  const e = { id: uid(), name: kind === "tags" ? clean.toLowerCase() : clean };
  db[kind].push(e);
  save(db);
  return wait(e);
}

/** Popular tags first; tags on fewer than 2 artworks are hidden. */
export async function suggestTags(query: string): Promise<Entity[]> {
  const db = load();
  const q = normalizeName(query);
  const counts = new Map<string, number>();
  db.artworks.forEach((a) => a.tagIds.forEach((t) => counts.set(t, (counts.get(t) ?? 0) + 1)));
  return wait(
    db.tags
      .filter((t) => (counts.get(t.id) ?? 0) >= TAG_SUGGESTION_MIN_USES)
      .filter((t) => !q || t.name.includes(q))
      .sort((a, b) => (counts.get(b.id) ?? 0) - (counts.get(a.id) ?? 0))
      .slice(0, 10),
    60,
  );
}

// ---------- artworks ----------
export interface ListParams {
  state: ArtworkState;
  q?: string | undefined;
  artistId?: string | undefined;
  movementId?: string | undefined;
  museum?: string | undefined;
  tagIds?: string[] | undefined;
  fromYear?: number | undefined;
  toYear?: number | undefined;
  page?: number | undefined;
}
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export async function listArtworks(p: ListParams): Promise<Page<Artwork>> {
  const userId = me();
  const db = load();
  const name = (l: Entity[], id: string | null) => (id ? (l.find((e) => e.id === id)?.name ?? "") : "");
  const q = p.q ? normalizeName(p.q) : "";
  let items = db.artworks.filter((a) => a.ownerId === userId && artworkState(a) === p.state);
  if (q)
    items = items.filter((a) =>
      [
        a.title,
        name(db.artists, a.artistId),
        name(db.subjects, a.subjectId),
        a.museum,
        ...a.tagIds.map((t) => name(db.tags, t)),
      ].some((f) => f.toLowerCase().includes(q)),
    );
  if (p.artistId) items = items.filter((a) => a.artistId === p.artistId);
  if (p.movementId) items = items.filter((a) => a.movementId === p.movementId);
  if (p.museum) items = items.filter((a) => a.museum.toLowerCase().includes(normalizeName(p.museum!)));
  if (p.tagIds?.length) items = items.filter((a) => p.tagIds!.every((t) => a.tagIds.includes(t)));
  if (p.fromYear != null || p.toYear != null) {
    const lo = p.fromYear ?? -Infinity;
    const hi = p.toYear ?? Infinity;
    items = items.filter((a) => {
      if (!a.date) return false;
      const [s, e] = yearSpan(a.date);
      return e >= lo && s <= hi;
    });
  }
  items.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const page = Math.max(1, p.page ?? 1);
  return wait({
    items: items.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    total: items.length,
    page,
    pageSize: PAGE_SIZE,
  });
}

function own(db: Db, id: string): Artwork {
  const a = db.artworks.find((x) => x.id === id && x.ownerId === me());
  if (!a) throw new Error("Artwork not found.");
  return a;
}

export async function getArtwork(id: string): Promise<Artwork> {
  return wait(own(load(), id));
}

export async function findDuplicates(input: ArtworkInput, excludeId?: string): Promise<Artwork[]> {
  const userId = me();
  return wait(
    load().artworks.filter((a) => a.ownerId === userId && a.id !== excludeId && isDuplicate(a, input)),
    40,
  );
}

export async function createArtwork(input: ArtworkInput, photo?: Blob | null): Promise<Artwork> {
  const userId = me();
  try {
    const photoId = photo ? await putPhoto(photo) : null;
    const db = load();
    const a: Artwork = {
      ...input,
      title: collapse(input.title),
      museum: collapse(input.museum),
      id: uid(),
      ownerId: userId,
      photoId,
      detailPhotoIds: [],
      discoverable: false,
      notesDiscoverable: false,
      createdAt: new Date().toISOString(),
    };
    db.artworks.push(a);
    track(db, "artwork_created", userId);
    save(db);
    return wait(a);
  } catch (e) {
    const db = load();
    track(db, "artwork_creation_failed", userId);
    save(db);
    throw e;
  }
}

export type ArtworkPatch = Partial<ArtworkInput & Pick<Artwork, "discoverable" | "notesDiscoverable">>;

export async function updateArtwork(id: string, patch: ArtworkPatch): Promise<Artwork> {
  const db = load();
  const a = own(db, id);
  const next = { ...a, ...patch };
  if (next.discoverable && !canBeDiscoverable(next))
    throw new Error("Set a title, artist and date before making this artwork discoverable.");
  if (next.discoverable && !a.discoverable) track(db, "discoverable_enabled", a.ownerId);
  Object.assign(a, next, { title: collapse(next.title), museum: collapse(next.museum) });
  save(db);
  return wait(a);
}

export async function deleteArtwork(id: string) {
  const db = load();
  const a = own(db, id);
  db.artworks = db.artworks.filter((x) => x.id !== id);
  save(db);
  await Promise.all([a.photoId, ...a.detailPhotoIds].filter(Boolean).map((p) => removePhoto(p!)));
}

/** Uploading the main photo moves a watchlist artwork into the collection. */
export async function setArtworkPhoto(id: string, photo: Blob): Promise<Artwork> {
  const photoId = await putPhoto(photo);
  const db = load();
  const a = own(db, id);
  const old = a.photoId;
  if (!old) track(db, "watchlist_converted", a.ownerId);
  a.photoId = photoId;
  save(db);
  if (old) await removePhoto(old);
  return a;
}

export async function addDetailPhoto(id: string, photo: Blob): Promise<Artwork> {
  const photoId = await putPhoto(photo);
  const db = load();
  const a = own(db, id);
  a.detailPhotoIds.push(photoId);
  save(db);
  return a;
}

export async function deleteDetailPhoto(id: string, photoId: string): Promise<Artwork> {
  const db = load();
  const a = own(db, id);
  a.detailPhotoIds = a.detailPhotoIds.filter((p) => p !== photoId);
  save(db);
  await removePhoto(photoId);
  return a;
}

/** Photos are private: only the owner's browser can read them. */
export async function getPhoto(photoId: string): Promise<Blob | null> {
  return (await photoTx<Blob | undefined>("readonly", (s) => s.get(photoId))) ?? null;
}

// ---------- relationship exploration ----------
export type Dimension = "artist" | "subject" | "movement" | "museum" | "tags";
export interface ExploreParams {
  artworkId: string;
  dimension: Dimension;
  tagIds: string[];
  includeCollection: boolean;
  includeWatchlist: boolean;
  includeCommunity: boolean;
}
export interface ExploreResult {
  collection: Artwork[];
  watchlist: Artwork[];
  community: CommunityArtwork[];
}

export async function explore(p: ExploreParams): Promise<ExploreResult> {
  const userId = me();
  const db = load();
  const src = own(db, p.artworkId);
  const match = (a: Pick<Artwork, "artistId" | "subjectId" | "movementId" | "museum" | "tagIds">) => {
    switch (p.dimension) {
      case "artist":
        return !!src.artistId && a.artistId === src.artistId;
      case "subject":
        return !!src.subjectId && a.subjectId === src.subjectId;
      case "movement":
        return !!src.movementId && a.movementId === src.movementId;
      case "museum":
        return !!src.museum && normalizeName(a.museum) === normalizeName(src.museum);
      case "tags":
        return p.tagIds.length > 0 && p.tagIds.every((t) => a.tagIds.includes(t));
    }
  };
  const candidates = db.artworks.filter((a) => a.id !== src.id && match(a));
  const mine = candidates.filter((a) => a.ownerId === userId);
  track(db, "exploration", userId);
  save(db);
  return wait({
    collection: p.includeCollection ? mine.filter((a) => artworkState(a) === "COLLECTION") : [],
    watchlist: p.includeWatchlist ? mine.filter((a) => artworkState(a) === "WATCHLIST") : [],
    community: p.includeCommunity
      ? candidates
          .filter((a) => a.ownerId !== userId && a.discoverable)
          .map((a) => ({
            id: a.id,
            title: a.title,
            artistId: a.artistId,
            date: a.date,
            subjectId: a.subjectId,
            movementId: a.movementId,
            museum: a.museum,
            tagIds: a.tagIds,
            notes: a.notesDiscoverable ? a.notes : null,
          }))
      : [],
  });
}

// ---------- seed ----------
function seed(): Db {
  const ent = (names: string[]) => names.map((name) => ({ id: uid(), name }));
  const artists = ent([
    "Caravaggio",
    "Rembrandt van Rijn",
    "Peter Paul Rubens",
    "Artemisia Gentileschi",
    "Paolo Uccello",
    "Johannes Vermeer",
  ]);
  const movements = ent([
    "Baroque",
    "Renaissance",
    "Early Renaissance",
    "Mannerism",
    "Rococo",
    "Neoclassicism",
    "Romanticism",
    "Realism",
    "Impressionism",
    "Post-Impressionism",
    "Expressionism",
    "Cubism",
    "Surrealism",
  ]);
  const subjects = ent(["Cat", "Landscape", "Ship", "David and Goliath", "Judgement of Paris", "Judith", "Battle", "Militia"]);
  const tags = ent(["battle", "horse", "armor", "chiaroscuro", "sword"]);
  const id = (l: Entity[], n: string) => l.find((e) => e.name === n)!.id;
  const T = (...n: string[]) => n.map((x) => id(tags, x));
  const yr = (fromYear: number, circa = false) => ({ fromYear, toYear: null, circa, bc: false });
  const community = (
    title: string,
    artist: string,
    date: ReturnType<typeof yr>,
    subject: string | null,
    museum: string,
    tagIds: string[],
    notes = "",
  ): Artwork => ({
    id: uid(),
    ownerId: "community",
    title,
    artistId: id(artists, artist),
    date,
    subjectId: subject ? id(subjects, subject) : null,
    movementId: id(movements, artist === "Paolo Uccello" ? "Early Renaissance" : "Baroque"),
    museum,
    tagIds,
    notes,
    photoId: null,
    detailPhotoIds: [],
    discoverable: true,
    notesDiscoverable: !!notes,
    createdAt: new Date(2026, 0, 1).toISOString(),
  });
  return {
    users: [],
    artists,
    movements,
    subjects,
    tags,
    events: [],
    artworks: [
      community("David with the Head of Goliath", "Caravaggio", yr(1610, true), "David and Goliath", "Galleria Borghese", T("chiaroscuro", "sword"), "Goliath is a self-portrait."),
      community("Judith Beheading Holofernes", "Caravaggio", yr(1599, true), "Judith", "Palazzo Barberini", T("chiaroscuro", "sword")),
      community("Judith Slaying Holofernes", "Artemisia Gentileschi", yr(1620, true), "Judith", "Uffizi", T("chiaroscuro", "sword")),
      community("The Judgement of Paris", "Peter Paul Rubens", yr(1636), "Judgement of Paris", "Prado", []),
      community("The Battle of the Amazons", "Peter Paul Rubens", yr(1618), "Battle", "Alte Pinakothek", T("battle", "horse", "armor")),
      community("The Battle of San Romano", "Paolo Uccello", yr(1438, true), "Battle", "National Gallery", T("battle", "horse", "armor"), "Look at the broken lances on the ground."),
      community("The Night Watch", "Rembrandt van Rijn", yr(1642), "Militia", "Rijksmuseum", T("armor", "chiaroscuro")),
    ],
  };
}
