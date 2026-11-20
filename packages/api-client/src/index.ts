import createClient, { type Client } from "openapi-fetch";

import type { paths } from "./schema";

export { streamTutorEvents, type TutorStreamEvent } from "./stream";

export type TutorClient = Client<paths>;
export type TutorPaths = paths;

export function createTutorClient(baseUrl = ""): TutorClient {
  return createClient<paths>({
    baseUrl,
    credentials: "include",
    headers: { "X-Requested-With": "tutor" },
  });
}
