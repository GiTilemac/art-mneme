import { httpServices } from "./http";
import type { Services } from "./types";

export type * from "./types";

/** The implementation the app uses: the real backend. The mock stays for the tests. */
export const api: Services = httpServices;
