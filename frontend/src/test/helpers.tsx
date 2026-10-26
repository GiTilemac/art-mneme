import "fake-indexeddb/auto";
import { IDBFactory } from "fake-indexeddb";
import { QueryClient } from "@tanstack/react-query";
import { createMemoryHistory, createRouter, RouterProvider } from "@tanstack/react-router";
import { fireEvent, render, screen } from "@testing-library/react";
import { Blob as NodeBlob } from "node:buffer";
import { routeTree } from "@/routeTree.gen";
import { Route as rootRoute } from "@/routes/__root";

// jsdom never loads the stylesheets the root route waits on and cannot render its <html> shell.
// Tests drop the shell and head links of the root route; every page is the real one.
rootRoute.update({ shellComponent: undefined, head: () => ({}) } as never);

/** Fresh simulated backend: empty browser storage and photo database. */
export function resetBackend() {
  localStorage.clear();
  globalThis.indexedDB = new IDBFactory();
}

// jsdom's Blob does not survive the simulated photo storage; Node's does.
export const photoFile = () => new NodeBlob(["photo"], { type: "image/jpeg" }) as unknown as File;

/** Renders the real app at the given URL, in memory. */
export function renderApp(url: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: [url] }),
    context: { queryClient },
    defaultPreloadStaleTime: 0,
  });
  return { router, ...render(<RouterProvider router={router} />) };
}

/** Picks a photo in the (hidden) file input of the n-th photo button on the page. */
export function choosePhoto(n = 0) {
  const input = document.querySelectorAll<HTMLInputElement>('input[type="file"]')[n]!;
  fireEvent.change(input, { target: { files: [photoFile()] } });
}

export const typeInto = (el: HTMLElement, value: string) => fireEvent.change(el, { target: { value } });
export const click = (name: string | RegExp) => fireEvent.click(screen.getByRole("button", { name }));
