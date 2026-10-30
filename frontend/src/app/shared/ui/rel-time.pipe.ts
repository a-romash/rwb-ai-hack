import {Pipe, PipeTransform} from '@angular/core';
import {relativeTime} from '../../core/util/time';

/** `{{ date | relTime: clock.now() }}` — пересчитывается, когда тикают общие часы. */
@Pipe({name: 'relTime'})
export class RelTimePipe implements PipeTransform {
  transform(value: string | number | Date | null | undefined, now: number): string {
    return value == null ? '' : relativeTime(value, now);
  }
}
