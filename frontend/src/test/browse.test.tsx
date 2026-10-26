import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ArtworkInput } from "@/lib/domain";
import { mockServices } from "@/services/mock";
import { choosePhoto, click, renderApp, resetBackend, typeInto } from "./helpers";

vi.mock("@/services", () => ({ api: mockServices }));
vi.mock("@/lib/image", async () => {
  const { Blob } = await import("node:buffer");
  return { prepareJpeg: async () => new Blob(["photo"], { type: "image/jpeg" }) };
});

const input = (o: Partial<ArtworkInput> = {}): ArtworkInput => ({
  title: "", artistId: null, date: null, subjectId: null, movementId: null, museum: "", tagIds: [], notes: "", ...o,
});
const photo = () => new Blob(["photo"], { type: "image/jpeg" });

beforeEach(async () => {
  resetBackend();
  await mockServices.register("ana@example.com", "password1");
});

describe("collection and watchlist", () => {
  it("an empty collection says so and offers to add an artwork", async () => {
    renderApp("/collection");
    await screen.findByText("Your collection is empty.");
    expect(screen.getByRole("link", { name: "Add an artwork" })).toBeInTheDocument();
  });

  it("saved artworks are shown", async () => {
    await mockServices.createArtwork(input({ title: "Sunflowers" }), "COLLECTION", photo());
    await mockServices.createArtwork(input({ title: "Water Lilies" }), "WATCHLIST");
    renderApp("/watchlist");
    await screen.findByText("Water Lilies");
    expect(screen.queryByText("Sunflowers")).not.toBeInTheDocument();
  });

  it("a search with no hits says nothing matches", async () => {
    await mockServices.createArtwork(input({ title: "Sunflowers" }), "COLLECTION", photo());
    renderApp("/collection");
    await screen.findByText("Sunflowers");
    typeInto(screen.getByPlaceholderText(/Search title/), "zzzz");
    await screen.findByText("Nothing matches.");
  });
});

describe("add artwork", () => {
  it("a collection artwork without a photo is refused with a message", async () => {
    renderApp("/artworks/new");
    typeInto(await screen.findByPlaceholderText("The Night Watch"), "Sunflowers");
    click("Add to collection");
    await screen.findByText("Add a photo to put this artwork in your collection.");
  });

  it("a watchlist artwork without a photo is saved and its page opens", async () => {
    renderApp("/artworks/new");
    typeInto(await screen.findByPlaceholderText("The Night Watch"), "Water Lilies");
    fireToggle("Watchlist");
    click("Add to watchlist");
    expect(await screen.findByRole("heading", { name: "Water Lilies" })).toBeInTheDocument();
    expect(screen.getByText("Watchlist", { selector: "p" })).toBeInTheDocument();
  });

  it("the submit button follows the Collection / Watchlist toggle", async () => {
    renderApp("/artworks/new");
    await screen.findByRole("button", { name: "Add to collection" });
    fireToggle("Watchlist");
    expect(screen.getByRole("button", { name: "Add to watchlist" })).toBeInTheDocument();
  });

  it("a collection artwork with a photo is saved", async () => {
    renderApp("/artworks/new");
    typeInto(await screen.findByPlaceholderText("The Night Watch"), "Sunflowers");
    choosePhoto();
    await screen.findByRole("button", { name: "Change photo" });
    click("Add to collection");
    expect(await screen.findByRole("heading", { name: "Sunflowers" })).toBeInTheDocument();
    expect(screen.getByText("Collection", { selector: "p" })).toBeInTheDocument();
  });
});

const fireToggle = (name: string) => fireEvent.click(screen.getByRole("radio", { name }));
