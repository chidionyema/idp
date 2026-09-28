import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { catalogWords, reactWords, scaffolderWords, docsWords } from './words';

export const wordsModule = createFrontendModule({
  pluginId: 'app',
  extensions: [catalogWords, reactWords, scaffolderWords, docsWords],
});
