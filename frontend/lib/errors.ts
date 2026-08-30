/** Typed API error carrying the backend's `{"error": "..."}` contract. */

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

/** Map an unknown thrown value to a user-facing message. */
export function errorMessage(err: unknown): string {
  if (isApiError(err)) return err.message;
  if (err instanceof TypeError) return "Network error — check your connection.";
  return "Unexpected error. Please try again.";
}
