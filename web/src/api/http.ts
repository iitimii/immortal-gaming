/**
 * HTTP API Client
 * Thin wrapper around fetch
 */

// API base URL from env; empty (relative paths) if unset
const API_BASE = import.meta.env.VITE_API_TARGET || '';
const DEFAULT_TIMEOUT_MS = 30000;
const REQUEST_TIMEOUT_REASON = 'cws-request-timeout';

export interface HttpRequestOptions {
  timeoutMs?: number;
  signal?: AbortSignal;
}

export class ApiError extends Error {
  public status: number;
  public response: { data: unknown };

  constructor(status: number, message: string, responseData?: unknown) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
    this.response = { data: responseData || {} };
  }
}

export interface DownloadedFile {
  blob: Blob;
  filename: string | null;
}

/** Resolve an API path against the configured API base (relative when unset). */
export function buildApiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

/** Extract the filename from a Content-Disposition header, if present. */
export function parseContentDispositionFilename(header: string | null): string | null {
  if (!header) return null;
  const encoded = /filename\*\s*=\s*(?:UTF-8'')?([^;]+)/i.exec(header);
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1].trim().replace(/^"|"$/g, ''));
    } catch {
      // Fall through to the plain filename parameter
    }
  }
  const plain = /filename\s*=\s*("([^"]*)"|[^;]+)/i.exec(header);
  if (!plain) return null;
  const value = (plain[2] ?? plain[1]).trim();
  return value || null;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  requestOptions: HttpRequestOptions = {},
): Promise<T> {
  const response = await send(path, options, requestOptions);

  // Assume the backend always returns JSON
  const data: unknown = await response.json();
  if (
    data &&
    typeof data === 'object' &&
    'ok' in data &&
    data.ok === true &&
    'data' in data
  ) {
    return (data as { data: T }).data;
  }
  return data as T;
}

async function send(
  path: string,
  options: RequestInit = {},
  requestOptions: HttpRequestOptions = {},
): Promise<Response> {
  const url = buildApiUrl(path);
  const controller = new AbortController();
  const timeoutMs = requestOptions.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  let didTimeout = false;
  const callerSignal = requestOptions.signal ?? options.signal;
  const abortFromCaller = () => {
    controller.abort(callerSignal?.reason);
  };
  const timeout = globalThis.setTimeout(() => {
    didTimeout = true;
    controller.abort(REQUEST_TIMEOUT_REASON);
  }, timeoutMs);

  if (callerSignal) {
    if (callerSignal.aborted) {
      abortFromCaller();
    } else {
      callerSignal.addEventListener('abort', abortFromCaller, { once: true });
    }
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError' && didTimeout) {
      throw new ApiError(408, `Request timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw error;
  } finally {
    globalThis.clearTimeout(timeout);
    callerSignal?.removeEventListener('abort', abortFromCaller);
  }

  if (!response.ok) {
    // Try to parse the error response as JSON
    let errorData: unknown = null;
    let errorMessage = `Request failed: ${response.statusText}`;
    
    try {
      errorData = await response.json();
      // Use the backend's detail field as the error message if present
      if (errorData && typeof errorData === 'object' && 'detail' in errorData) {
        const detail = (errorData as { detail?: unknown }).detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (
          detail &&
          typeof detail === 'object' &&
          'message' in detail &&
          typeof (detail as { message?: unknown }).message === 'string'
        ) {
          errorMessage = (detail as { message: string }).message;
        }
      }
    } catch {
      // Fall back to the default message if parsing fails
    }
    
    throw new ApiError(response.status, errorMessage, errorData);
  }

  return response;
}

export const httpClient = {
  get<T>(path: string) {
    return request<T>(path, { method: 'GET' });
  },

  post<T>(path: string, body: unknown, options?: HttpRequestOptions) {
    return request<T>(path, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    }, options);
  },

  patch<T>(path: string, body: unknown, options?: HttpRequestOptions) {
    return request<T>(path, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    }, options);
  },

  put<T>(path: string, body: unknown, options?: HttpRequestOptions) {
    return request<T>(path, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    }, options);
  },

  delete<T>(path: string) {
    return request<T>(path, { method: 'DELETE' });
  },

  /** GET a file response (non-JSON body), keeping the server-provided filename. */
  async download(path: string, options?: HttpRequestOptions): Promise<DownloadedFile> {
    const response = await send(path, { method: 'GET' }, options);
    return {
      blob: await response.blob(),
      filename: parseContentDispositionFilename(response.headers.get('Content-Disposition')),
    };
  }
};

