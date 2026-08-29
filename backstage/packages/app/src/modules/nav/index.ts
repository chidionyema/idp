import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { EstateNav } from './EstateNav';

export const navModule = createFrontendModule({
  pluginId: 'app',
  extensions: [EstateNav],
});
