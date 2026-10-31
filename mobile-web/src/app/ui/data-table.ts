import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatTableModule} from '@angular/material/table';

@Component({
  selector: 'app-data-table',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatTableModule],
  template: `
    @if (columns().length === 0) {
      <p>No columns</p>
    } @else {
      <div class="wrap">
        <table mat-table [dataSource]="rows()">
          @for (column of columns(); track column) {
            <ng-container [matColumnDef]="column">
              <th mat-header-cell *matHeaderCellDef>{{ column }}</th>
              <td mat-cell *matCellDef="let row">{{ text(row, column) }}</td>
            </ng-container>
          }
          <tr mat-header-row *matHeaderRowDef="columns()"></tr>
          <tr mat-row *matRowDef="let row; columns: columns()"></tr>
        </table>
      </div>
    }
  `,
  styles: `
    .wrap { overflow: auto; border: 1px solid #d0d7de; border-radius: 8px; background: #fff; }
    table { width: 100%; }
  `,
})
export class AppDataTable {
  readonly columns = input<string[]>([]);
  readonly rows = input<Record<string, string>[]>([]);

  text(row: Record<string, string>, column: string): string {
    return row[column] ?? '';
  }
}
