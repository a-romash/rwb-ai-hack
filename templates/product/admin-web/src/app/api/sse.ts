import {InjectionToken} from '@angular/core';
import {environment} from '../../environments/environment';

export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL', {
  factory: () => environment.apiBaseUrl,
});

export interface SseConnectOptions {
  authorization?: string;
  signal?: AbortSignal;
}

export function apiUrl(path: string): string {
  const suffix = path.startsWith('/') ? path : `/${path}`;
  return `${environment.apiBaseUrl}${suffix}`;
}

export async function connectSse(
  url: string,
  options: SseConnectOptions = {},
): Promise<ReadableStream<Uint8Array>> {
  const headers = new Headers({Accept: 'text/event-stream'});
  if (options.authorization) {
    headers.set('Authorization', options.authorization);
  }
  const response = await fetch(url, {headers, signal: options.signal});
  if (!response.ok || !response.body) {
    throw new Error(`SSE failed (${response.status})`);
  }
  return response.body;
}

export async function* readSseEvents(stream: ReadableStream<Uint8Array>): AsyncGenerator<string> {
  const reader = stream.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  try {
    for (;;) {
      const {value, done} = await reader.read();
      if (done) {
        return;
      }
      buffer += value;
      const parts = buffer.split('\n\n');
      buffer = parts.pop() ?? '';
      for (const part of parts) {
        const data = part
          .split('\n')
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trimStart())
          .join('\n');
        if (data) {
          yield data;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
