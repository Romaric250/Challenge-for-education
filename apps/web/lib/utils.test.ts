import { describe, expect, it } from "vitest";

import { citationLabel } from "./utils";

describe("citationLabel", () => {
  it("names the document and page range", () => {
    expect(
      citationLabel({
        marker: "S1",
        document: "Sample mathematics booklet",
        page_start: 8,
        page_end: 8,
      }),
    ).toBe("S1 Sample mathematics booklet p. 8");
  });
});
