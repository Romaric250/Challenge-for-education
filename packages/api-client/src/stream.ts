export type TutorStreamEvent = {
  event: string;
  data: Record<string, unknown>;
};

export async function* streamTutorEvents(
  url: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<TutorStreamEvent> {
  const response = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: {
      "content-type": "application/json",
      "x-requested-with": "tutor",
    },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok || response.body === null) {
    throw new Error(`The tutor request failed (${response.status}).`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const step = await reader.read();
    if (step.done) {
      break;
    }
    buffer += decoder.decode(step.value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const parsed = parseFrame(frame);
      if (parsed !== null) {
        yield parsed;
      }
    }
  }
}

function parseFrame(frame: string): TutorStreamEvent | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }
  if (dataLines.length === 0) {
    return null;
  }
  const parsed: unknown = JSON.parse(dataLines.join("\n"));
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { event, data: {} };
  }
  return { event, data: parsed as Record<string, unknown> };
}
