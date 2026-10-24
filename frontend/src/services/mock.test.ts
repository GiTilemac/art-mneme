import "fake-indexeddb/auto";
import { IDBFactory } from "fake-indexeddb";
import { Blob as NodeBlob } from "node:buffer";
import { beforeEach, describe, expect, it } from "vitest";
import type { ArtworkInput } from "@/lib/domain";
import { mockServices as api } from "./mock";

// jsdom's Blob does not survive the simulated photo storage; Node's does.
const photo = (text = "photo") => new NodeBlob([text], { type: "image/jpeg" }) as unknown as Blob;
const input = (o: Partial<ArtworkInput> = {}): ArtworkInput => ({
  title: "",
  artistId: null,
  date: null,
  subjectId: null,
  movementId: null,
  museum: "",
  tagIds: [],
  notes: "",
  ...o,
});
const year = (fromYear: number) => ({ fromYear, toYear: null, circa: false, bc: false });
const signUp = (email = "ana@example.com") => api.register(email, "password1");
const tagId = async (name: string) => (await api.createEntity("tags", name)).id;

beforeEach(() => {
  localStorage.clear();
  globalThis.indexedDB = new IDBFactory();
});

describe("auth", () => {
  it("registering logs the new user in", async () => {
    const user = await signUp();
    expect(await api.me()).toEqual(user);
  });

  it("registering with an email that is already taken is refused", async () => {
    await signUp();
    await expect(signUp("ANA@example.com")).rejects.toThrow("already exists");
  });

  it("registering with a password shorter than 8 characters is refused", async () => {
    await expect(api.register("ana@example.com", "1234567")).rejects.toThrow("at least 8");
  });

  it("logging in with a wrong password is refused", async () => {
    await signUp();
    await api.logout();
    await expect(api.login("ana@example.com", "wrong-password")).rejects.toThrow("incorrect");
  });

  it("logging out ends the session", async () => {
    await signUp();
    await api.logout();
    expect(await api.me()).toBeNull();
  });

  it("actions that need a login are refused when logged out", async () => {
    await expect(api.listArtworks({ state: "COLLECTION" })).rejects.toThrow("sign in");
  });
});

describe("shared entries", () => {
  beforeEach(() => signUp());

  it("creating an artist that already exists returns the existing one, ignoring capital letters", async () => {
    const existing = (await api.searchEntities("artists", "caravaggio")).items[0]!;
    expect(await api.createEntity("artists", "CARAVAGGIO")).toEqual(existing);
  });

  it("searching artists finds part of a name", async () => {
    const page = await api.searchEntities("artists", "rem");
    expect(page.items.map((a) => a.name)).toEqual(["Rembrandt van Rijn"]);
    expect(page.pageSize).toBe(50);
  });

  it("tags are stored in lowercase", async () => {
    expect((await api.createEntity("tags", "Night Sky")).name).toBe("night sky");
  });

  it("a tag with punctuation is refused", async () => {
    await expect(api.createEntity("tags", "cat!")).rejects.toThrow("letters, numbers");
  });

  it("tag suggestions put the most used first and leave out tags used on fewer than 2 artworks", async () => {
    const rare = await tagId("rare");
    await api.createArtwork(input({ tagIds: [rare] }), "WATCHLIST");
    const names = (await api.suggestTags("")).map((t) => t.name);
    expect(names[0]).toBe("chiaroscuro");
    expect(names).not.toContain("rare");
  });
});

describe("artworks", () => {
  beforeEach(() => signUp());

  it("a collection artwork without a photo is refused", async () => {
    await expect(api.createArtwork(input(), "COLLECTION")).rejects.toThrow("Add a photo");
  });

  it("a watchlist artwork can be created with or without a photo", async () => {
    expect((await api.createArtwork(input(), "WATCHLIST")).hasPhoto).toBe(false);
    const withPhoto = await api.createArtwork(input(), "WATCHLIST", photo());
    expect(withPhoto).toMatchObject({ state: "WATCHLIST", hasPhoto: true });
  });

  it("adding a photo to a watchlist artwork moves it to the collection and replaces the old photo", async () => {
    const a = await api.createArtwork(input(), "WATCHLIST", photo("old"));
    expect((await api.setArtworkPhoto(a.id, photo("new"))).state).toBe("COLLECTION");
    expect(await (await api.getArtworkPhoto(a.id))!.text()).toBe("new");
  });

  it("replacing the photo of a collection artwork keeps it in the collection", async () => {
    const a = await api.createArtwork(input(), "COLLECTION", photo("first"));
    expect((await api.setArtworkPhoto(a.id, photo("second"))).state).toBe("COLLECTION");
    expect(await (await api.getArtworkPhoto(a.id))!.text()).toBe("second");
  });

  it("the list shows only artworks in the chosen state, newest first", async () => {
    await api.createArtwork(input({ title: "Older" }), "COLLECTION", photo());
    await api.createArtwork(input({ title: "Newer" }), "COLLECTION", photo());
    await api.createArtwork(input({ title: "Wanted" }), "WATCHLIST");
    const page = await api.listArtworks({ state: "COLLECTION" });
    expect(page.items.map((a) => a.title)).toEqual(["Newer", "Older"]);
  });

  it("search never looks at notes", async () => {
    await api.createArtwork(input({ title: "Sunflowers", notes: "secret word" }), "WATCHLIST");
    expect((await api.listArtworks({ state: "WATCHLIST", q: "secret" })).total).toBe(0);
    expect((await api.listArtworks({ state: "WATCHLIST", q: "sunflow" })).total).toBe(1);
  });

  it("an artwork shows the names of its artist and tags", async () => {
    const artist = await api.createEntity("artists", "Caravaggio");
    const a = await api.createArtwork(
      input({ artistId: artist.id, tagIds: [await tagId("sword")] }),
      "WATCHLIST",
    );
    expect(a.artist).toEqual(artist);
    expect(a.tags.map((t) => t.name)).toEqual(["sword"]);
  });

  it("another user's artwork behaves as if it does not exist", async () => {
    const a = await api.createArtwork(input(), "COLLECTION", photo());
    await api.logout();
    await signUp("ben@example.com");
    await expect(api.getArtwork(a.id)).rejects.toThrow("not found");
    await expect(api.getArtworkPhoto(a.id)).rejects.toThrow("not found");
  });

  it("possible duplicates are found ignoring capital letters and extra spaces", async () => {
    const artist = await api.createEntity("artists", "Rembrandt van Rijn");
    await api.createArtwork(
      input({ title: "The Night Watch", artistId: artist.id, date: year(1642) }),
      "WATCHLIST",
    );
    const dups = await api.findDuplicates({
      title: " the  night watch",
      artistId: artist.id,
      date: year(1642),
    });
    expect(dups).toHaveLength(1);
  });

  it("no duplicate is reported while the date is missing", async () => {
    const artist = await api.createEntity("artists", "Rembrandt van Rijn");
    await api.createArtwork(input({ title: "The Night Watch", artistId: artist.id }), "WATCHLIST");
    expect(
      await api.findDuplicates({ title: "The Night Watch", artistId: artist.id, date: null }),
    ).toEqual([]);
  });

  it("a deleted artwork is gone", async () => {
    const a = await api.createArtwork(input(), "COLLECTION", photo());
    await api.deleteArtwork(a.id);
    await expect(api.getArtwork(a.id)).rejects.toThrow("not found");
  });

  it("detail photos can be added, viewed and deleted", async () => {
    const a = await api.createArtwork(input(), "COLLECTION", photo());
    const [detail] = (await api.addDetailPhoto(a.id, photo("brushstroke"))).detailPhotoIds;
    expect(await (await api.getDetailPhoto(a.id, detail!))!.text()).toBe("brushstroke");
    expect((await api.deleteDetailPhoto(a.id, detail!)).detailPhotoIds).toEqual([]);
  });
});

describe("discoverability", () => {
  beforeEach(() => signUp());

  it("making an artwork discoverable is refused while the date is missing", async () => {
    const artist = await api.createEntity("artists", "Caravaggio");
    const a = await api.createArtwork(input({ title: "Medusa", artistId: artist.id }), "WATCHLIST");
    await expect(api.setDiscoverable(a.id, true)).rejects.toThrow("title, artist and date");
  });

  it("an artwork with title, artist and date can be made discoverable without a photo", async () => {
    const artist = await api.createEntity("artists", "Caravaggio");
    const a = await api.createArtwork(
      input({ title: "Medusa", artistId: artist.id, date: year(1597) }),
      "WATCHLIST",
    );
    expect((await api.setDiscoverable(a.id, true)).discoverable).toBe(true);
  });

  it("notes discoverability is switched separately", async () => {
    const a = await api.createArtwork(input(), "WATCHLIST");
    expect(await api.setNotesDiscoverable(a.id, true)).toMatchObject({
      discoverable: false,
      notesDiscoverable: true,
    });
  });
});

describe("exploration", () => {
  beforeEach(() => signUp());

  const sources = { includeCollection: true, includeWatchlist: false, includeCommunity: true };

  it("community results come from discoverable artworks and show notes only when shared", async () => {
    const artist = await api.createEntity("artists", "Caravaggio");
    const a = await api.createArtwork(input({ artistId: artist.id }), "WATCHLIST");
    const { community } = await api.explore(a.id, { by: "artist", tagIds: [], ...sources });
    expect(community.map((c) => [c.title, c.notes])).toEqual([
      ["David with the Head of Goliath", "Goliath is a self-portrait."],
      ["Judith Beheading Holofernes", null],
    ]);
    expect(community[0]).not.toHaveProperty("hasPhoto");
  });

  it("community results are left out unless asked for", async () => {
    const artist = await api.createEntity("artists", "Caravaggio");
    const a = await api.createArtwork(input({ artistId: artist.id }), "WATCHLIST");
    const result = await api.explore(a.id, {
      by: "artist",
      tagIds: [],
      ...sources,
      includeCommunity: false,
    });
    expect(result.community).toEqual([]);
  });

  it("watchlist results are left out unless asked for", async () => {
    const artist = await api.createEntity("artists", "Caravaggio");
    const a = await api.createArtwork(input({ artistId: artist.id }), "COLLECTION", photo());
    await api.createArtwork(input({ artistId: artist.id }), "WATCHLIST");
    const off = await api.explore(a.id, { by: "artist", tagIds: [], ...sources });
    const on = await api.explore(a.id, {
      by: "artist",
      tagIds: [],
      ...sources,
      includeWatchlist: true,
    });
    expect([off.watchlist.length, on.watchlist.length]).toEqual([0, 1]);
  });

  it("shared tags results carry every chosen tag", async () => {
    const tags = [await tagId("battle"), await tagId("horse"), await tagId("armor")];
    const a = await api.createArtwork(input({ tagIds: tags }), "WATCHLIST");
    const { community } = await api.explore(a.id, { by: "tags", tagIds: tags, ...sources });
    expect(community.map((c) => c.title).sort()).toEqual([
      "The Battle of San Romano",
      "The Battle of the Amazons",
    ]);
  });
});
