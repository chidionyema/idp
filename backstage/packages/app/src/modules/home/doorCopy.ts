// One line per door on the home page. The menu already owns the titles and the routes;
// this file only says what the person gets when they click. Keys are the menu titles in
// nav/EstateNav.tsx, so doorCopy.test.ts fails the moment a door is renamed without its line.
export const DOOR_WHY: Record<string, string> = {
  Home: 'What needs you, right now.',
  Estate: 'The whole estate on one page, live.',
  Catalogue: 'Every service we hold.',
  Health: 'Reds, and who owns them.',
  Showcase: 'The buyer demo, end to end.',
  Docs: 'The manuals.',
  You: 'Your settings.',
  Reports: 'What the estate wrote down.',
  Investigate: 'Trace a red to its root.',
  Pair: 'Work an issue with an agent.',
  Create: 'Start something new.',
  Map: 'How it all connects.',
  Kubernetes: 'What the cluster is running.',
  Tools: 'Every page you sign in through.',
  Find: 'Search the estate.',
};
