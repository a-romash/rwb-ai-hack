import {Component} from '@angular/core';
import {RouterLink, RouterOutlet} from '@angular/router';
import {TuiRoot} from '@taiga-ui/core';

@Component({
  selector: 'app-root',
  imports: [RouterLink, RouterOutlet, TuiRoot],
  template: `
    <tui-root>
      <header class="topbar">
        <a class="brand" routerLink="/projects" aria-label="Поток — к проектам">
          <span class="brand-mark" aria-hidden="true">↗</span> поток<span class="brand-sub">/ AI pipeline</span>
        </a>
        <span class="workspace-label"><span class="status-dot"></span> Рабочее пространство</span>
      </header>
      <div class="shell">
        <aside class="sidebar">
          <p class="nav-caption">РАЗРАБОТКА</p>
          <a routerLink="/projects" class="nav-link"><span aria-hidden="true">▦</span> Проекты</a>
          <div class="sidebar-note"><span class="status-dot"></span> Локальное окружение<br><small>От идеи к работающему продукту</small></div>
        </aside>
        <main id="main-content"><router-outlet /></main>
      </div>
    </tui-root>
  `,
})
export class App {}
