import {ChangeDetectionStrategy, Component, computed, input} from '@angular/core';

@Component({
  selector: 'app-map-view',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="map" role="img" [attr.aria-label]="'Map ' + lat() + ', ' + lng()">
      <span class="marker" [style.left]="marker().left" [style.top]="marker().top"></span>
    </div>
    <p class="coords">{{ lat() }}, {{ lng() }}</p>
  `,
  styles: `
    :host { display: block; }
    .map {
      position: relative;
      height: 220px;
      border: 1px solid #c4c7c5;
      border-radius: 8px;
      background-color: #e7f1ff;
      background-image:
        linear-gradient(to right, rgba(0, 0, 0, 0.08) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(0, 0, 0, 0.08) 1px, transparent 1px);
      background-size: 24px 24px;
    }
    .marker {
      position: absolute;
      width: 12px;
      height: 12px;
      margin: -6px 0 0 -6px;
      border-radius: 50%;
      background: #005cbb;
      box-shadow: 0 0 0 4px rgba(0, 92, 187, 0.25);
    }
    .coords { margin: 8px 0 0; font-size: 12px; }
  `,
})
export class AppMapView {
  readonly lat = input(0);
  readonly lng = input(0);
  readonly marker = computed(() => {
    const left = ((this.lng() + 180) / 360) * 100;
    const top = ((90 - this.lat()) / 180) * 100;
    return {left: `${clamp(left)}%`, top: `${clamp(top)}%`};
  });
}

function clamp(value: number): number {
  return Math.min(100, Math.max(0, value));
}
