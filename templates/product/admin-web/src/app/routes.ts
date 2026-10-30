import {Routes} from '@angular/router';
import {routes as generated} from './generated/routes';
import {ScreenPage} from './screens/screen-page';
import {Start} from './screens/start';

// Every ui.json screen is served at /<ScreenName> by the generic renderer (E2E walks rely on it).
export const routes: Routes = [
  {path: '', component: Start},
  ...generated.map((route) => ({
    path: route.path,
    component: ScreenPage,
    data: {screen: route.screen},
    title: route.title,
  })),
  {path: '**', redirectTo: ''},
];
