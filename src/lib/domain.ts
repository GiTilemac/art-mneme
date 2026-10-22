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

export interface Artwork extends ArtworkInput {
  id: string;
  ownerId: string;
  photoId: string | null;
  detailPhotoIds: string[];
  discoverable: boolean;
  notesDiscoverable: boolean;
  createdAt: string;
}

/** What other users may see. Never contains photos; notes only when shared. */
export interface CommunityArtwork {
  id: string;
  title: string;
  artistId: string | null;
  date: ArtworkDate | null;
  subjectId: string | null;
  movementId: string | null;
  museum: string;
  tagIds: string[];
  notes: string | null;
}

export const PAGE_SIZE = 50;
export const MIN_PASSWORD_LENGTH = 8;
export const MAX_PHOTO_BYTES = 30 * 1024 * 1024;
export const PHOTO_MAX_EDGE = 2500;
export const TAG_SUGGESTION_MIN_USES = 2;

export const artworkState = (a: Pick<Artwork, "photoId">): ArtworkState =>
  a.photoId ? "COLLECTION" : "WATCHLIST";

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

export const emptyInput = (): ArtworkInput => ({
  title: "",
  artistId: null,
  date: null,
  subjectId: null,
  movementId: null,
  museum: "",
  tagIds: [],
  notes: "",
});
