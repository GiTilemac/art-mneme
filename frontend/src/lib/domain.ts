// Pure domain types and rules for ArtMneme. No I/O here.

export type ArtworkState = "WATCHLIST" | "COLLECTION";
export type EntityKind = "artists" | "movements" | "subjects" | "tags";

export interface Entity {
  id: string;
  name: string;
}

/** Years are always 1 or more; each year has its own BC flag. */
export interface ArtworkDate {
  fromYear: number;
  toYear: number | null;
  circa: boolean;
  fromBc: boolean;
  toBc: boolean;
}

/** A date as the backend answers it, with its readable form. */
export interface ShownDate extends ArtworkDate {
  display: string;
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
export interface Artwork extends Omit<ArtworkDraft, "date"> {
  id: string;
  state: ArtworkState;
  date: ShownDate | null;
  hasPhoto: boolean;
  photoVersion: string;
  createdAt: string;
}

export const PAGE_SIZE = 50;
export const MIN_PASSWORD_LENGTH = 8;
export const MAX_PHOTO_BYTES = 30 * 1024 * 1024;
export const PHOTO_MAX_EDGE = 2500;
export const TAG_SUGGESTION_MIN_USES = 2;
export const MAX_BC_YEAR = 100_000;

/** A collection artwork needs a photo; a watchlist artwork may have one or not. */
export function validateNewArtwork(state: ArtworkState, hasPhoto: boolean): string | null {
  return state === "COLLECTION" && !hasPhoto ? "Add a photo to put this artwork in your collection." : null;
}

const signedYear = (year: number, bc: boolean) => (bc ? -year : year);

/** The date as the backend shows it, e.g. `c. 450 BC`, `500–450 BC`, `30 BC – 14 AD`. */
export function formatDate(d: ArtworkDate | null): string {
  if (!d) return "";
  const start = signedYear(d.fromYear, d.fromBc);
  const end = d.toYear == null ? null : signedYear(d.toYear, d.toBc);
  let s: string;
  if (end == null || end === start) s = start < 0 ? `${-start} BC` : String(start);
  else if (start < 0 && end > 0) s = `${-start} BC – ${end} AD`;
  else if (end < 0) s = `${-start}–${-end} BC`;
  else s = `${start}–${end}`;
  return d.circa ? `c. ${s}` : s;
}

/** Signed year span (BC as negative) for range filtering. */
export function yearSpan(d: ArtworkDate): [number, number] {
  const a = signedYear(d.fromYear, d.fromBc);
  const b = d.toYear == null ? a : signedYear(d.toYear, d.toBc);
  return [a, b];
}

/** The backend's date rules; null when the date is fine. */
export function validateDate(d: ArtworkDate | null, thisYear = new Date().getFullYear()): string | null {
  if (!d) return null;
  for (const [year, bc] of [[d.fromYear, d.fromBc], [d.toYear, d.toBc && d.toYear != null]] as const) {
    if (year == null) continue;
    if (year < 1) return "A year must be 1 or more; use the BC box for years before 1 AD.";
    if (bc && year > MAX_BC_YEAR) return "A BC year cannot be above 100,000.";
    if (!bc && year > thisYear) return "A year cannot be in the future.";
  }
  const [start, end] = yearSpan(d);
  return d.toYear != null && end < start ? "The end year cannot be before the start year." : null;
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
