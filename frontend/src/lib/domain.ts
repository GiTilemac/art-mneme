// Pure domain types and rules for ArtMneme. No I/O here.

export type ArtworkState = "WATCHLIST" | "COLLECTION";
export type EntityKind = "artists" | "movements" | "subjects" | "tags";

export interface Entity {
  id: string;
  name: string;
}

export interface ArtworkDate {
  fromYear: number;
  toYear: number | null;
  circa: boolean;
  bc: boolean;
}

export interface ArtworkInput {
  title: string;
  artistId: string | null;
  date: ArtworkDate | null;
  subjectId: string | null;
  movementId: string | null;
  museum: string;
  tagIds: string[];
  notes: string;
}

/** The editable fields with their entries resolved, as the artwork form shows them. */
export interface ArtworkDraft {
  title: string;
  artist: Entity | null;
  date: ArtworkDate | null;
  subject: Entity | null;
  movement: Entity | null;
  museum: string;
  tags: Entity[];
  notes: string;
}

/** One of the user's own artworks. */
export interface Artwork extends ArtworkDraft {
  id: string;
  state: ArtworkState;
  hasPhoto: boolean;
  detailPhotoIds: string[];
  discoverable: boolean;
  notesDiscoverable: boolean;
  createdAt: string;
}

/** What other users may see. Never contains photos; notes only when shared. */
export interface CommunityArtwork extends Omit<ArtworkDraft, "notes"> {
  id: string;
  notes: string | null;
}

export const PAGE_SIZE = 50;
export const MIN_PASSWORD_LENGTH = 8;
export const MAX_PHOTO_BYTES = 30 * 1024 * 1024;
export const PHOTO_MAX_EDGE = 2500;
export const TAG_SUGGESTION_MIN_USES = 2;

/** A collection artwork needs a photo; a watchlist artwork may have one or not. */
export function validateNewArtwork(state: ArtworkState, hasPhoto: boolean): string | null {
  return state === "COLLECTION" && !hasPhoto ? "Add a photo to put this artwork in your collection." : null;
}

export function formatDate(d: ArtworkDate | null): string {
  if (!d) return "";
  let s = String(d.fromYear);
  if (d.toYear != null && d.toYear !== d.fromYear) s += `–${d.toYear}`;
  if (d.circa) s = `c. ${s}`;
  if (d.bc) s += " BC";
  return s;
}

/** Signed year span (BC as negative) for range filtering. */
export function yearSpan(d: ArtworkDate): [number, number] {
  const sign = d.bc ? -1 : 1;
  const a = d.fromYear * sign;
  const b = (d.toYear ?? d.fromYear) * sign;
  return [Math.min(a, b), Math.max(a, b)];
}

export const collapse = (s: string) => s.trim().replace(/\s+/g, " ");
export const normalizeName = (s: string) => collapse(s).toLowerCase();

const TAG_RE = /^[\p{L}\p{N} -]+$/u;
export function validateTag(raw: string): string | null {
  const t = collapse(raw);
  if (t.length < 2 || t.length > 50) return "Tags must be 2–50 characters.";
  if (!TAG_RE.test(t)) return "Tags may only contain letters, numbers, spaces and hyphens.";
  return null;
}

export function validatePassword(pw: string): string | null {
  return pw.length >= MIN_PASSWORD_LENGTH
    ? null
    : `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
}

const hasIdentity = (a: Pick<ArtworkInput, "title" | "artistId" | "date">) =>
  collapse(a.title).length > 0 && !!a.artistId && !!a.date;

export const canBeDiscoverable = hasIdentity;

export function isDuplicate(
  a: Pick<ArtworkInput, "title" | "artistId" | "date">,
  b: Pick<ArtworkInput, "title" | "artistId" | "date">,
): boolean {
  if (!hasIdentity(a) || !hasIdentity(b)) return false;
  const da = a.date!;
  const db = b.date!;
  return (
    normalizeName(a.title) === normalizeName(b.title) &&
    a.artistId === b.artistId &&
    da.fromYear === db.fromYear &&
    (da.toYear ?? null) === (db.toYear ?? null) &&
    da.circa === db.circa &&
    da.bc === db.bc
  );
}

export const emptyDraft = (): ArtworkDraft => ({
  title: "",
  artist: null,
  date: null,
  subject: null,
  movement: null,
  museum: "",
  tags: [],
  notes: "",
});

export const toInput = (d: ArtworkDraft): ArtworkInput => ({
  title: d.title,
  artistId: d.artist?.id ?? null,
  date: d.date,
  subjectId: d.subject?.id ?? null,
  movementId: d.movement?.id ?? null,
  museum: d.museum,
  tagIds: d.tags.map((t) => t.id),
  notes: d.notes,
});
