import { createApp } from '@backstage/frontend-defaults';
import catalogPlugin from '@backstage/plugin-catalog/alpha';
import { navModule } from './modules/nav';
import { homeModule } from './modules/home';
import { signInModule } from './modules/signin';
import { themeModule } from './modules/theme';

export default createApp({
  features: [catalogPlugin, navModule, homeModule, signInModule, themeModule],
});
