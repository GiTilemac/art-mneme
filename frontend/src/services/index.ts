import { mockServices } from "./mock";
import type { Services } from "./types";

export type * from "./types";

/** The implementation the app uses. Swap in the real backend here once it exists. */
export const api: Services = mockServices;
