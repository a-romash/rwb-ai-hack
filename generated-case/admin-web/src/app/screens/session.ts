import {Injectable, signal} from '@angular/core';
import {apiUrl} from '../api/sse';

const ROLE_KEY = 'role';

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

/** Demo sign-in by role (POST /api/auth/login): the stand has no identity provider. */
@Injectable({providedIn: 'root'})
export class Session {
  readonly role = signal<string | null>(readRole());
  private token: Promise<string> | null = null;

  use(role: string): void {
    try {
      localStorage.setItem(ROLE_KEY, role);
    } catch {
      // Storage may be blocked; the role still lives for this page.
    }
    this.token = null;
    this.role.set(role);
  }

  async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const response = await fetch(apiUrl(path), {
      method,
      headers: {'Content-Type': 'application/json', Authorization: `Bearer ${await this.signIn()}`},
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) {
      const problem = await response.json().catch(() => null);
      throw new ApiError(response.status, problem?.title ?? response.statusText);
    }
    return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
  }

  /** Authorization header value for streams that cannot go through request(). */
  async authorization(): Promise<string> {
    return `Bearer ${await this.signIn()}`;
  }

  private signIn(): Promise<string> {
    const role = this.role();
    if (!role) {
      return Promise.reject(new ApiError(401, 'Роль не выбрана'));
    }
    this.token ??= fetch(apiUrl('/auth/login'), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({role}),
    }).then(async (response) => {
      if (!response.ok) {
        this.token = null;
        throw new ApiError(response.status, 'Вход не выполнен');
      }
      return (await response.json()).token as string;
    });
    return this.token;
  }
}

function readRole(): string | null {
  // ?role=engineer wins so a link (or an E2E walk) can open the app as a given role.
  const fromUrl = new URLSearchParams(location.search).get(ROLE_KEY);
  try {
    if (fromUrl) {
      localStorage.setItem(ROLE_KEY, fromUrl);
    }
    return fromUrl ?? localStorage.getItem(ROLE_KEY);
  } catch {
    return fromUrl;
  }
}
