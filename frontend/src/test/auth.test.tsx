import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MIN_PASSWORD_LENGTH } from "@/lib/domain";
import { mockServices } from "@/services/mock";
import { click, renderApp, resetBackend, typeInto } from "./helpers";

vi.mock("@/services", () => ({ api: mockServices }));

beforeEach(async () => {
  resetBackend();
  await mockServices.register("ana@example.com", "password1");
});

async function signIn(password: string) {
  typeInto(await screen.findByLabelText("Email"), "ana@example.com");
  typeInto(screen.getByLabelText("Password"), password);
  click("Sign in");
}

describe("sign in", () => {
  beforeEach(() => mockServices.logout());

  it("a correct login opens the collection page", async () => {
    const { router } = renderApp("/auth");
    await signIn("password1");
    await screen.findByText("Your collection is empty.");
    expect(router.state.location.pathname).toBe("/collection");
  });

  it("a wrong password shows the error text", async () => {
    renderApp("/auth");
    await signIn("wrong-password");
    await screen.findByText(/incorrect/i);
  });

  it("the sign-up page tells the minimum password length", async () => {
    renderApp("/auth?mode=signup");
    await screen.findByText(`At least ${MIN_PASSWORD_LENGTH} characters.`);
  });

  it("without a session the collection page goes to the sign-in page", async () => {
    const { router } = renderApp("/collection");
    await screen.findByText("Welcome back");
    expect(router.state.location.pathname).toBe("/auth");
  });
});

describe("signed-in area", () => {
  it("Sign out returns to the sign-in page", async () => {
    renderApp("/collection");
    await screen.findByText("Your collection is empty.");
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    await screen.findByText("Welcome back");
  });
});
