import "fake-indexeddb/auto";
import { IDBFactory } from "fake-indexeddb";
import { Blob as NodeBlob } from "node:buffer";
import { beforeEach, describe, expect, it } from "vitest";
import type { ArtworkDate, ArtworkInput } from "@/lib/domain";
import { mockServices as api, readArtworkPhoto } from "./mock";

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
const year = (fromYear: number, o: Partial<ArtworkDate> = {}): ArtworkDate => ({
  fromYear,
  toYear: null,
  circa: false,
  fromBc: false,
  toBc: false,
  ...o,
});
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
    const [rare, common] = [await tagId("rare"), await tagId("common")];
    await api.createArtwork(input({ tagIds: [rare, common] }), "WATCHLIST");
    await api.createArtwork(input({ tagIds: [common] }), "WATCHLIST");
    const names = (await api.suggestTags("")).map((t) => t.name);
    expect(names).toEqual(["common"]);
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
    expect(await (await readArtworkPhoto(a.id))!.text()).toBe("new");
  });

  it("replacing the photo of a collection artwork keeps it in the collection", async () => {
    const a = await api.createArtwork(input(), "COLLECTION", photo("first"));
    expect((await api.setArtworkPhoto(a.id, photo("second"))).state).toBe("COLLECTION");
    expect(await (await readArtworkPhoto(a.id))!.text()).toBe("second");
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
    await expect(readArtworkPhoto(a.id)).rejects.toThrow("not found");
  });

  it("a deleted artwork is gone", async () => {
    const a = await api.createArtwork(input(), "COLLECTION", photo());
    await api.deleteArtwork(a.id);
    await expect(api.getArtwork(a.id)).rejects.toThrow("not found");
  });

});

describe("dates", () => {
  beforeEach(() => signUp());

  it("an artwork shows its date as the backend writes it", async () => {
    const date = year(30, { toYear: 14, fromBc: true, circa: true });
    expect((await api.createArtwork(input({ date }), "WATCHLIST")).date?.display).toBe("c. 30 BC – 14 AD");
  });

  it("a range that ends before it starts is refused, also across eras", async () => {
    const date = year(14, { toYear: 30, toBc: true });
    await expect(api.createArtwork(input({ date }), "WATCHLIST")).rejects.toThrow("end year cannot be before");
  });

  it("the date filter uses a BC box for each year", async () => {
    await api.createArtwork(input({ title: "Old", date: year(450, { fromBc: true }) }), "WATCHLIST");
    await api.createArtwork(input({ title: "New", date: year(1642) }), "WATCHLIST");
    const titles = async (p: object) =>
      (await api.listArtworks({ state: "WATCHLIST", ...p })).items.map((a) => a.title);
    expect(await titles({ fromYear: 500, fromBc: true, toYear: 400, toBc: true })).toEqual(["Old"]);
    expect(await titles({ fromYear: 1600 })).toEqual(["New"]);
  });
});

describe("exploration", () => {
  beforeEach(() => signUp());

  const sources = { includeCollection: true, includeWatchlist: false };

  it("watchlist results are left out unless asked for", async () => {
    const artist = await api.createEntity("artists", "Caravaggio");
    const a = await api.createArtwork(input({ artistId: artist.id }), "COLLECTION", photo());
    await api.createArtwork(input({ artistId: artist.id }), "WATCHLIST");
    const off = await api.explore(a.id, { by: "artist", ...sources });
    const on = await api.explore(a.id, { by: "artist", ...sources, includeWatchlist: true });
    expect([off.watchlist.length, on.watchlist.length]).toEqual([0, 1]);
  });
});
