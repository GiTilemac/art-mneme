/**
 * MOCK BACKEND. Implements the services layer so the whole app runs without a real backend.
 * Data lives in localStorage (records) and IndexedDB (photos) in this browser only.
 * Each function follows the matching endpoint in openapi.yaml.
 */
import {
  collapse,
  normalizeName,
  PAGE_SIZE,
  TAG_SUGGESTION_MIN_USES,
  formatDate,
  validateDate,
  validateNewArtwork,
  validatePassword,
  validateTag,
  yearSpan,
  type Artwork,
  type ArtworkInput,
  type ArtworkState,
  type Entity,
  type EntityKind,
} from "@/lib/domain";
import type { ExploreParams, ListParams, Page, RelatedArtworks, Services, User } from "./types";

/** An artwork as the mock stores it: entries by id, plus the owner and photo ids. */
interface StoredArtwork extends ArtworkInput {
  id: string;
  ownerId: string;
  state: ArtworkState;
  photoId: string | null;
  createdAt: string;
}

interface Db {
  users: { id: string; email: string; password: string }[];
  artists: Entity[];
  movements: Entity[];
  subjects: Entity[];
  tags: Entity[];
  artworks: StoredArtwork[];
}

/** Stands in for the session cookie. */
interface Session {
  userId: string;
  email: string;
  expiresAt: number;
}

const DB_KEY = "artmneme-db-v2";
const SESSION_KEY = "artmneme-session";
const SESSION_MS = 30 * 24 * 60 * 60 * 1000;
const uid = () => crypto.randomUUID();
const wait = <T>(v: T, ms = 120) => new Promise<T>((r) => setTimeout(() => r(v), ms));

// ---------- storage ----------
function load(): Db {
  const raw = localStorage.getItem(DB_KEY);
  if (raw) {
    const db = JSON.parse(raw) as Db;
    // Records saved before state was stored derived it from the photo.
    db.artworks.forEach((a) => (a.state ??= a.photoId ? "COLLECTION" : "WATCHLIST"));
    return db;
  }
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
const readPhoto = async (id: string) =>
  (await photoTx<Blob | undefined>("readonly", (s) => s.get(id))) ?? null;
const removePhoto = (id: string) => photoTx("readwrite", (s) => void s.delete(id));

// ---------- auth ----------
function currentSession(): Session | null {
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
  const s = currentSession();
  if (!s) throw new Error("Please sign in again.");
  return s.userId;
}
function startSession(u: { id: string; email: string }): User {
  const s: Session = { userId: u.id, email: u.email, expiresAt: Date.now() + SESSION_MS };
  localStorage.setItem(SESSION_KEY, JSON.stringify(s));
  return { id: u.id, email: u.email };
}

async function register(email: string, password: string) {
  const e = email.trim().toLowerCase();
  if (!/^\S+@\S+\.\S+$/.test(e)) throw new Error("Enter a valid email address.");
  const pwErr = validatePassword(password);
  if (pwErr) throw new Error(pwErr);
  const db = load();
  if (db.users.some((u) => u.email === e))
    throw new Error("An account with this email already exists.");
  const u = { id: uid(), email: e, password };
  db.users.push(u);
  save(db);
  return wait(startSession(u));
}

async function login(email: string, password: string) {
  const u = load().users.find(
    (x) => x.email === email.trim().toLowerCase() && x.password === password,
  );
  if (!u) throw new Error("Email or password is incorrect.");
  return wait(startSession(u));
}

async function logout() {
  me();
  localStorage.removeItem(SESSION_KEY);
  return wait(undefined);
}

async function getMe() {
  const s = currentSession();
  return wait(s ? { id: s.userId, email: s.email } : null, 0);
}

// ---------- shared entries ----------
async function searchEntities(
  kind: Exclude<EntityKind, "tags">,
  query: string,
  page = 1,
): Promise<Page<Entity>> {
  me();
  const q = normalizeName(query);
  const items = load()
    [kind].filter((e) => !q || e.name.toLowerCase().includes(q))
    .sort((a, b) => a.name.localeCompare(b.name));
  return wait(paginate(items, page), 60);
}

async function createEntity(kind: EntityKind, name: string) {
  me();
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
async function suggestTags(query: string) {
  me();
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
function paginate<T>(items: T[], requested?: number): Page<T> {
  const page = Math.max(1, requested ?? 1);
  return {
    items: items.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    total: items.length,
    page,
    pageSize: PAGE_SIZE,
  };
}

const find = (l: Entity[], id: string | null) => (id ? (l.find((e) => e.id === id) ?? null) : null);

function resolved(db: Db, a: StoredArtwork) {
  return {
    title: a.title,
    artist: find(db.artists, a.artistId),
    date: a.date && { ...a.date, display: formatDate(a.date) },
    subject: find(db.subjects, a.subjectId),
    movement: find(db.movements, a.movementId),
    museum: a.museum,
    tags: a.tagIds.map((t) => find(db.tags, t)).filter((t): t is Entity => !!t),
  };
}

function view(db: Db, a: StoredArtwork): Artwork {
  return {
    ...resolved(db, a),
    id: a.id,
    notes: a.notes,
    state: a.state,
    hasPhoto: !!a.photoId,
    photoVersion: a.photoId ?? "",
    createdAt: a.createdAt,
  };
}

function own(db: Db, id: string): StoredArtwork {
  const a = db.artworks.find((x) => x.id === id && x.ownerId === me());
  if (!a) throw new Error("Artwork not found.");
  return a;
}

async function listArtworks(p: ListParams) {
  const userId = me();
  const db = load();
  const name = (l: Entity[], id: string | null) => find(l, id)?.name ?? "";
  const q = p.q ? normalizeName(p.q) : "";
  let items = db.artworks.filter((a) => a.ownerId === userId && a.state === p.state);
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
  if (p.museum)
    items = items.filter((a) => normalizeName(a.museum) === normalizeName(p.museum!));
  if (p.tagIds?.length) items = items.filter((a) => p.tagIds!.every((t) => a.tagIds.includes(t)));
  if (p.fromYear != null || p.toYear != null) {
    const lo = p.fromYear == null ? -Infinity : p.fromBc ? -p.fromYear : p.fromYear;
    const hi = p.toYear == null ? Infinity : p.toBc ? -p.toYear : p.toYear;
    if (hi < lo) throw new Error("The end year cannot be before the start year.");
    items = items.filter((a) => {
      if (!a.date) return false;
      const [s, e] = yearSpan(a.date);
      return e >= lo && s <= hi;
    });
  }
  items.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const page = paginate(items, p.page);
  return wait({ ...page, items: page.items.map((a) => view(db, a)) });
}

async function getArtwork(id: string) {
  const db = load();
  return wait(view(db, own(db, id)));
}

async function createArtwork(input: ArtworkInput, state: ArtworkState, photo?: Blob | null) {
  const userId = me();
  const invalid = validateNewArtwork(state, !!photo) ?? validateDate(input.date);
  if (invalid) throw new Error(invalid);
  const photoId = photo ? await putPhoto(photo) : null;
  const db = load();
  const a: StoredArtwork = {
    ...input,
    title: collapse(input.title),
    museum: collapse(input.museum),
    id: uid(),
    ownerId: userId,
    state,
    photoId,
    createdAt: new Date().toISOString(),
  };
  db.artworks.push(a);
  save(db);
  return wait(view(db, a));
}

async function updateArtwork(id: string, patch: Partial<ArtworkInput>) {
  const db = load();
  const a = own(db, id);
  const next = { ...a, ...patch };
  const invalid = validateDate(next.date);
  if (invalid) throw new Error(invalid);
  Object.assign(a, next, { title: collapse(next.title), museum: collapse(next.museum) });
  save(db);
  return wait(view(db, a));
}

async function deleteArtwork(id: string) {
  const db = load();
  const a = own(db, id);
  db.artworks = db.artworks.filter((x) => x.id !== id);
  save(db);
  if (a.photoId) await removePhoto(a.photoId);
}

// ---------- photos ----------
/** Uploading the main photo moves a watchlist artwork into the collection. Any old photo is deleted. */
async function setArtworkPhoto(id: string, photo: Blob) {
  own(load(), id);
  const photoId = await putPhoto(photo);
  const db = load();
  const a = own(db, id);
  const old = a.photoId;
  a.state = "COLLECTION";
  a.photoId = photoId;
  save(db);
  if (old) await removePhoto(old);
  return view(db, a);
}

/** For the tests: the stored photo of an artwork. The app loads photos from the photo address. */
export async function readArtworkPhoto(id: string) {
  const a = own(load(), id);
  return a.photoId ? readPhoto(a.photoId) : null;
}

// ---------- relationship exploration ----------
async function explore(id: string, p: ExploreParams): Promise<RelatedArtworks> {
  const userId = me();
  const db = load();
  const src = own(db, id);
  const match = (a: StoredArtwork) => {
    switch (p.by) {
      case "artist":
        return !!src.artistId && a.artistId === src.artistId;
      case "subject":
        return !!src.subjectId && a.subjectId === src.subjectId;
      case "movement":
        return !!src.movementId && a.movementId === src.movementId;
      case "museum":
        return !!src.museum && normalizeName(a.museum) === normalizeName(src.museum);
    }
  };
  const mine = db.artworks
    .filter((a) => a.id !== src.id && a.ownerId === userId && match(a))
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  return wait({
    collection: p.includeCollection
      ? mine.filter((a) => a.state === "COLLECTION").map((a) => view(db, a))
      : [],
    watchlist: p.includeWatchlist
      ? mine.filter((a) => a.state === "WATCHLIST").map((a) => view(db, a))
      : [],
  });
}

export const mockServices: Services = {
  register,
  login,
  logout,
  me: getMe,
  searchEntities,
  createEntity,
  suggestTags,
  listArtworks,
  createArtwork,
  getArtwork,
  updateArtwork,
  deleteArtwork,
  setArtworkPhoto,
  photoUrl: (a) => (a.hasPhoto ? `/api/artworks/${a.id}/photo?v=${a.photoVersion}` : null),
  explore,
};

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
  const subjects = ent([
    "Cat",
    "Landscape",
    "Ship",
    "David and Goliath",
    "Judgement of Paris",
    "Judith",
    "Battle",
    "Militia",
  ]);
  const tags = ent(["battle", "horse", "armor", "chiaroscuro", "sword"]);
  return {
    users: [],
    artists,
    movements,
    subjects,
    tags,
    artworks: [],
  };
}
