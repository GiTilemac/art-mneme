/**
 * The services layer: every backend call the app makes, shaped after openapi.yaml.
 * Screens call these through `api` from "@/services" and never reach storage or HTTP directly.
 */
import type {
  Artwork,
  ArtworkInput,
  ArtworkState,
  CommunityArtwork,
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
  /** BC years are negative. */
  fromYear?: number | undefined;
  toYear?: number | undefined;
  page?: number | undefined;
}

export type Dimension = "artist" | "subject" | "movement" | "museum" | "tags";

export interface ExploreParams {
  by: Dimension;
  tagIds: string[];
  includeCollection: boolean;
  includeWatchlist: boolean;
  includeCommunity: boolean;
}

export interface RelatedArtworks {
  collection: Artwork[];
  watchlist: Artwork[];
  community: CommunityArtwork[];
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
  findDuplicates(
    input: Pick<ArtworkInput, "title" | "artistId" | "date">,
    excludeId?: string,
  ): Promise<Artwork[]>;
  createArtwork(input: ArtworkInput, state: ArtworkState, photo?: Blob | null): Promise<Artwork>;
  getArtwork(id: string): Promise<Artwork>;
  updateArtwork(id: string, patch: Partial<ArtworkInput>): Promise<Artwork>;
  deleteArtwork(id: string): Promise<void>;

  // photos
  setArtworkPhoto(id: string, photo: Blob): Promise<Artwork>;
  getArtworkPhoto(id: string): Promise<Blob | null>;
  addDetailPhoto(id: string, photo: Blob): Promise<Artwork>;
  getDetailPhoto(id: string, photoId: string): Promise<Blob | null>;
  deleteDetailPhoto(id: string, photoId: string): Promise<Artwork>;

  // discoverability
  setDiscoverable(id: string, value: boolean): Promise<Artwork>;
  setNotesDiscoverable(id: string, value: boolean): Promise<Artwork>;

  // exploration
  explore(id: string, p: ExploreParams): Promise<RelatedArtworks>;
}
