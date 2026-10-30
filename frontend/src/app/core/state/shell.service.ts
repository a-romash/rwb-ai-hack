import {Injectable, signal} from '@angular/core';

export interface Crumb {
  label: string;
  link?: string;
}

/** Хлебные крошки верхней панели задаёт экран, который сейчас открыт. */
@Injectable({providedIn: 'root'})
export class ShellService {
  readonly crumbs = signal<Crumb[]>([]);
  /** Проект, открытый в рабочей области: командная палитра предлагает его разделы. */
  readonly projectId = signal<string | null>(null);
}
