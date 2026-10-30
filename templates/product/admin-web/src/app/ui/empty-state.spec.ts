import {ComponentFixture, TestBed} from '@angular/core/testing';
import {provideNoopAnimations} from '@angular/platform-browser/animations';
import {AppEmptyState} from './empty-state';

describe('AppEmptyState', () => {
  let fixture: ComponentFixture<AppEmptyState>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppEmptyState],
      providers: [provideNoopAnimations()],
    }).compileComponents();
    fixture = TestBed.createComponent(AppEmptyState);
    fixture.componentRef.setInput('title', 'No records');
    fixture.componentRef.setInput('message', 'Nothing to show.');
    fixture.detectChanges();
  });

  it('creates the component', () => {
    expect(fixture.componentInstance).toBeInstanceOf(AppEmptyState);
    expect(fixture.nativeElement.textContent).toContain('No records');
    expect(fixture.nativeElement.textContent).toContain('Nothing to show.');
  });
});
