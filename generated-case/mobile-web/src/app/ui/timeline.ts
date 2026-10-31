import {ChangeDetectionStrategy, Component, input} from '@angular/core';

export interface TimelineEvent {
  at: string;
  title: string;
  detail: string;
}

@Component({
  selector: 'app-timeline',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (events().length === 0) {
      <p>No events</p>
    } @else {
      <ol>
        @for (event of events(); track event.at + event.title) {
          <li>
            <time [attr.datetime]="event.at">{{ event.at }}</time>
            <strong>{{ event.title }}</strong>
            <p>{{ event.detail }}</p>
          </li>
        }
      </ol>
    }
  `,
  styles: `
    ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }
    li { border-left: 3px solid #005cbb; padding: 4px 0 4px 12px; }
    time { display: block; font-size: 12px; opacity: 0.7; }
    p { margin: 4px 0 0; }
  `,
})
export class AppTimeline {
  readonly events = input<readonly TimelineEvent[]>([]);
}
