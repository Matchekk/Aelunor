import { HttpClientError } from "../api/httpClient";

const TECHNICAL_ERROR_PATTERNS = [
  /nameerror/i,
  /syntaxerror/i,
  /traceback/i,
  /is not defined/i,
  /internal server error/i,
  /request failed with status/i,
  /exception/i,
];

function looksTechnicalErrorMessage(message: string): boolean {
  const normalized = message.trim();
  if (!normalized) {
    return false;
  }
  return TECHNICAL_ERROR_PATTERNS.some((pattern) => pattern.test(normalized));
}

export function deriveUserFacingErrorMessage(
  error: unknown,
  fallback = "Ein technischer Fehler ist aufgetreten. Bitte versuche es erneut.",
): string {
  if (error instanceof HttpClientError) {
    if (error.status >= 500) {
      return fallback;
    }
    if (error.status === 404) {
      return "Die angeforderte Kampagne wurde nicht gefunden oder ist nicht mehr verfügbar.";
    }
    if (error.status === 401 || error.status === 403) {
      return "Deine Sitzung ist nicht mehr gültig. Bitte melde dich über den Hub erneut an.";
    }
    if (looksTechnicalErrorMessage(error.message)) {
      return fallback;
    }
    return error.message || fallback;
  }

  if (error instanceof Error) {
    if (looksTechnicalErrorMessage(error.message)) {
      return fallback;
    }
    return error.message || fallback;
  }

  return fallback;
}

