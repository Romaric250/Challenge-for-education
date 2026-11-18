import createClient, { type Client } from "openapi-fetch";

import type { paths } from "./schema";

export type TutorClient = Client<paths>;
export type TutorPaths = paths;

export function createTutorClient(baseUrl: string): TutorClient {
  return createClient<paths>({ baseUrl });
}
