import { fireEvent, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ArtworkInput, ArtworkState } from "@/lib/domain";
import { mockServices } from "@/services/mock";
import { choosePhoto, click, renderApp, resetBackend, typeInto } from "./helpers";

vi.mock("@/services", () => ({ api: mockServices }));
vi.mock("@/lib/image", async () => {
  const { Blob } = await import("node:buffer");
  return { prepareJpeg: async () => new Blob(["photo"], { type: "image/jpeg" }) };
});

const photo = () => new Blob(["photo"], { type: "image/jpeg" });
const add = async (title: string, state: ArtworkState, o: Partial<ArtworkInput> = {}) => {
  const input: ArtworkInput = { title, artistId: null, date: null, subjectId: null, movementId: null, museum: "", tagIds: [], notes: "", ...o };
  return mockServices.createArtwork(input, state, state === "COLLECTION" ? photo() : null);
};

beforeEach(async () => {
  resetBackend();
  await mockServices.register("ana@example.com", "password1");
});

describe("artwork page", () => {
  it("adding a photo to a watchlist artwork moves it to the collection", async () => {
    const a = await add("Water Lilies", "WATCHLIST");
    renderApp(`/artworks/${a.id}`);
    await screen.findByText("Watchlist", { selector: "p" });
    choosePhoto();
    await screen.findByText("Collection", { selector: "p" });
    expect(screen.getByRole("button", { name: "Replace photo" })).toBeInTheDocument();
  });

  it("a watchlist artwork offers to add my photo", async () => {
    const a = await add("Water Lilies", "WATCHLIST");
    renderApp(`/artworks/${a.id}`);
    expect(await screen.findByRole("button", { name: "I've seen it — add my photo" })).toBeInTheDocument();
  });

  it("edited notes are shown after Save", async () => {
    const a = await add("Sunflowers", "COLLECTION");
    renderApp(`/artworks/${a.id}`);
    await screen.findByText("No notes yet.");
    click("Edit notes");
    typeInto(screen.getByRole("textbox"), "Seen on a rainy day");
    click("Save");
    await screen.findByText("Seen on a rainy day");
  });

  it("deleting an artwork returns to the list without it", async () => {
    const a = await add("Sunflowers", "COLLECTION");
    await add("Poppies", "COLLECTION");
    renderApp(`/artworks/${a.id}`);
    await screen.findByRole("heading", { name: "Sunflowers" });
    click("Delete artwork");
    const dialog = await screen.findByRole("alertdialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete" }));
    await screen.findByText("Poppies");
    expect(screen.queryByText("Sunflowers")).not.toBeInTheDocument();
  });

  it("an edited title is shown after Save", async () => {
    const a = await add("Sunflowers", "COLLECTION");
    renderApp(`/artworks/${a.id}`);
    await screen.findByRole("heading", { name: "Sunflowers" });
    click("Edit details");
    typeInto(await screen.findByPlaceholderText("The Night Watch"), "Irises");
    click("Save");
    expect(await screen.findByRole("heading", { name: "Irises" })).toBeInTheDocument();
  });
});

describe("explore relationships", () => {
  it("a relationship the artwork has no value for is disabled", async () => {
    const a = await add("Sunflowers", "COLLECTION");
    renderApp(`/artworks/${a.id}/explore`);
    expect(await screen.findByRole("button", { name: "Same artist" })).toBeDisabled();
  });

  it("before a choice it asks to choose a relationship", async () => {
    const a = await add("Sunflowers", "COLLECTION");
    renderApp(`/artworks/${a.id}/explore`);
    await screen.findByText("Choose a relationship to explore.");
  });

  it("results are grouped by collection and watchlist", async () => {
    const artist = await mockServices.createEntity("artists", "Van Gogh");
    const a = await add("Sunflowers", "COLLECTION", { artistId: artist.id });
    await add("Irises", "COLLECTION", { artistId: artist.id });
    await add("Starry Night", "WATCHLIST", { artistId: artist.id });
    renderApp(`/artworks/${a.id}/explore`);
    fireEvent.click(await screen.findByRole("button", { name: "Same artist" }));
    fireEvent.click(await screen.findByRole("switch", { name: "Watchlist" }));
    await screen.findByText("From my collection");
    await screen.findByText("From my watchlist");
    expect(screen.getByText("Irises")).toBeInTheDocument();
    expect(screen.getByText("Starry Night")).toBeInTheDocument();
  });

  it("no hits suggests turning on the watchlist", async () => {
    const artist = await mockServices.createEntity("artists", "Van Gogh");
    const a = await add("Sunflowers", "COLLECTION", { artistId: artist.id });
    renderApp(`/artworks/${a.id}/explore`);
    fireEvent.click(await screen.findByRole("button", { name: "Same artist" }));
    await screen.findByText("No related artworks — try turning on Watchlist.");
  });
});
