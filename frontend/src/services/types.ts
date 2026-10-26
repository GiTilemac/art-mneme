/**
 * The services layer: every backend call the app makes, shaped after openapi.yaml.
 * Screens call these through `api` from "@/services" and never reach storage or HTTP directly.
 */
import type {
  Artwork,
  ArtworkInput,
  ArtworkState,
  Entity,
  EntityKind,
} from "@/lib/domain";

export interface User {
  id: string;
  email: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ListParams {
  state: ArtworkState;
  q?: string | undefined;
  artistId?: string | undefined;
  movementId?: string | undefined;
  museum?: string | undefined;
  tagIds?: string[] | undefined;
  fromYear?: number | undefined;
  fromBc?: boolean | undefined;
  toYear?: number | undefined;
  toBc?: boolean | undefined;
  page?: number | undefined;
}

export type Dimension = "artist" | "subject" | "movement" | "museum";

export interface ExploreParams {
  by: Dimension;
  includeCollection: boolean;
  includeWatchlist: boolean;
}

export interface RelatedArtworks {
  collection: Artwork[];
  watchlist: Artwork[];
}

export interface Services {
  // /auth
  register(email: string, password: string): Promise<User>;
  login(email: string, password: string): Promise<User>;
  logout(): Promise<void>;
  /** The logged-in user, or null when logged out. */
  me(): Promise<User | null>;

  // /artists, /movements, /subjects, /tags
  searchEntities(
    kind: Exclude<EntityKind, "tags">,
    q: string,
    page?: number,
  ): Promise<Page<Entity>>;
  /** Returns the existing entry when the name already exists, ignoring capital letters. */
  createEntity(kind: EntityKind, name: string): Promise<Entity>;
  suggestTags(q: string): Promise<Entity[]>;

  // /artworks
  listArtworks(p: ListParams): Promise<Page<Artwork>>;
  createArtwork(input: ArtworkInput, state: ArtworkState, photo?: Blob | null): Promise<Artwork>;
  getArtwork(id: string): Promise<Artwork>;
  updateArtwork(id: string, patch: Partial<ArtworkInput>): Promise<Artwork>;
  deleteArtwork(id: string): Promise<void>;

  // photos
  /** Moves a watchlist artwork into the collection; replaces the photo of a collection one. */
  setArtworkPhoto(id: string, photo: Blob): Promise<Artwork>;
  /** Where the browser loads the photo from, or null when the artwork has none. */
  photoUrl(a: Artwork): string | null;

  // exploration
  explore(id: string, p: ExploreParams): Promise<RelatedArtworks>;
}
