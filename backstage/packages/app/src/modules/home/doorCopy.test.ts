import { NAV } from '../nav/EstateNav';
import { DOOR_WHY } from './doorCopy';

describe('DOOR_WHY', () => {
  it('has one line for every menu door, so a card is never blank', () => {
    expect(NAV.map(d => d.title).sort()).toEqual(Object.keys(DOOR_WHY).sort());
    for (const title of Object.keys(DOOR_WHY)) {
      expect(DOOR_WHY[title].length).toBeGreaterThan(8);
    }
  });
});
