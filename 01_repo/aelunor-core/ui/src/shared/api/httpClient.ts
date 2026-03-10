import { readSessionBootstrap } from "../../app/bootstrap/sessionStorage";

export class HttpClientError extends Error {
  public readonly status: number;
  public readonly detail: unknown;

  public constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.name = "HttpClientError";
    this.status = status;
    this.detail = detail;
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") ?? "";
  const isJsonResponse = contentType.includes("application/json");

  const payload: unknown = isJsonResponse
    ? await response.json().catch(() => null)
    : await response.text().catch(() => "");

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    if (typeof payload === "object" && payload && "detail" in payload) {
      const detailValue = (payload as { detail: unknown }).detail;
      if (typeof detailValue === "string" && detailValue.trim().length > 0) {
        message = detailValue;
      }
    }
    throw new HttpClientError(message, response.status, payload);
  }

  return payload as T;
}

export async function httpClient<T>(input: string, init: RequestInit = {}): Promise<T> {
  const session = readSessionBootstrap();
  const headers = new Headers(init.headers ?? {});
  headers.set("Accept", headers.get("Accept") ?? "application/json");

  if (session.player_id) {
    headers.set("X-Player-Id", session.player_id);
  }
  if (session.player_token) {
    headers.set("X-Player-Token", session.player_token);
  }
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(input, {
    ...init,
    headers,
  });
  return parseResponse<T>(response);
}

export function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  return httpClient<T>(path, { ...(init ?? {}), method: "GET" });
}

export function postJson<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
  const nextInit: RequestInit = {
    ...(init ?? {}),
    method: "POST",
  };
  if (body !== undefined) {
    nextInit.body = JSON.stringify(body);
  }
  return httpClient<T>(path, nextInit);
}
