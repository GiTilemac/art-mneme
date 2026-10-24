import { describe, expect, it } from "vitest";
import { canBeDiscoverable, formatDate, isDuplicate, validateNewArtwork, validatePassword, validateTag } from "./domain";

const d = (fromYear: number, o: Partial<{ toYear: number; circa: boolean; bc: boolean }> = {}) => ({
  fromYear,
  toYear: o.toYear ?? null,
  circa: !!o.circa,
  bc: !!o.bc,
});

describe("formatDate", () => {
  it("single year", () => expect(formatDate(d(1642))).toBe("1642"));
  it("range", () => expect(formatDate(d(1600, { toYear: 1605 }))).toBe("1600–1605"));
  it("circa", () => expect(formatDate(d(1600, { circa: true }))).toBe("c. 1600"));
  it("circa BC", () => expect(formatDate(d(450, { circa: true, bc: true }))).toBe("c. 450 BC"));
});

describe("validateTag", () => {
  it("rejects 1 char", () => expect(validateTag("a")).not.toBeNull());
  it("rejects 51 chars", () => expect(validateTag("a".repeat(51))).not.toBeNull());
  it("accepts letters numbers spaces hyphens", () => expect(validateTag("Battle-scene 2")).toBeNull());
  it("rejects punctuation", () => expect(validateTag("cat!")).not.toBeNull());
});

describe("password", () => {
  it("rejects 7", () => expect(validatePassword("1234567")).not.toBeNull());
  it("accepts 8 without composition rules", () => expect(validatePassword("aaaaaaaa")).toBeNull());
});

describe("duplicates", () => {
  const base = { title: "The Night  Watch", artistId: "a1", date: d(1642) };
  it("matches ignoring case and extra spaces", () =>
    expect(isDuplicate(base, { ...base, title: " the night watch" })).toBe(true));
  it("differs on circa", () =>
    expect(isDuplicate(base, { ...base, date: d(1642, { circa: true }) })).toBe(false));
  it("differs on artist", () => expect(isDuplicate(base, { ...base, artistId: "a2" })).toBe(false));
  it("skipped when date missing", () =>
    expect(isDuplicate({ ...base, date: null }, { ...base, date: null })).toBe(false));
});

describe("discoverability", () => {
  it("requires title, artist and date", () => {
    expect(canBeDiscoverable({ title: "X", artistId: "a", date: d(1) })).toBe(true);
    expect(canBeDiscoverable({ title: "", artistId: "a", date: d(1) })).toBe(false);
    expect(canBeDiscoverable({ title: "X", artistId: null, date: d(1) })).toBe(false);
    expect(canBeDiscoverable({ title: "X", artistId: "a", date: null })).toBe(false);
  });
});

describe("new artwork state", () => {
  it("refuses a collection artwork without a photo", () => expect(validateNewArtwork("COLLECTION", false)).not.toBeNull());
  it("accepts a collection artwork with a photo", () => expect(validateNewArtwork("COLLECTION", true)).toBeNull());
  it("accepts a watchlist artwork without a photo", () => expect(validateNewArtwork("WATCHLIST", false)).toBeNull());
  it("accepts a watchlist artwork with a photo", () => expect(validateNewArtwork("WATCHLIST", true)).toBeNull());
});
