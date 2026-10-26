import { describe, expect, it } from "vitest";
import { formatDate, validateDate, validateNewArtwork, validatePassword, validateTag } from "./domain";

const d = (
  fromYear: number,
  o: Partial<{ toYear: number; circa: boolean; fromBc: boolean; toBc: boolean }> = {},
) => ({
  fromYear,
  toYear: o.toYear ?? null,
  circa: !!o.circa,
  fromBc: !!o.fromBc,
  toBc: !!o.toBc,
});

describe("formatDate", () => {
  it("single year", () => expect(formatDate(d(1642))).toBe("1642"));
  it("range", () => expect(formatDate(d(1600, { toYear: 1605 }))).toBe("1600–1605"));
  it("circa", () => expect(formatDate(d(1600, { circa: true }))).toBe("c. 1600"));
  it("circa BC", () => expect(formatDate(d(450, { circa: true, fromBc: true }))).toBe("c. 450 BC"));
  it("BC range", () => expect(formatDate(d(500, { toYear: 450, fromBc: true, toBc: true }))).toBe("500–450 BC"));
  it("across eras", () => expect(formatDate(d(30, { toYear: 14, fromBc: true }))).toBe("30 BC – 14 AD"));
});

describe("validateDate", () => {
  it("accepts a range across eras", () => expect(validateDate(d(30, { toYear: 14, fromBc: true }))).toBeNull());
  it("refuses an end before the start, also across eras", () => {
    expect(validateDate(d(1605, { toYear: 1600 }))).toBe("The end year cannot be before the start year.");
    expect(validateDate(d(14, { toYear: 30, toBc: true }))).toBe("The end year cannot be before the start year.");
  });
  it("refuses an AD year in the future", () =>
    expect(validateDate(d(2030), 2026)).toBe("A year cannot be in the future."));
  it("refuses a BC year above 100,000", () =>
    expect(validateDate(d(100001, { fromBc: true }))).toBe("A BC year cannot be above 100,000."));
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

describe("new artwork state", () => {
  it("refuses a collection artwork without a photo", () => expect(validateNewArtwork("COLLECTION", false)).not.toBeNull());
  it("accepts a collection artwork with a photo", () => expect(validateNewArtwork("COLLECTION", true)).toBeNull());
  it("accepts a watchlist artwork without a photo", () => expect(validateNewArtwork("WATCHLIST", false)).toBeNull());
  it("accepts a watchlist artwork with a photo", () => expect(validateNewArtwork("WATCHLIST", true)).toBeNull());
});
