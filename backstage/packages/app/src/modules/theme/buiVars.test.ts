import { buiVars } from './buiVars';
import { dark, stateDark } from './tokens';

describe('buiVars', () => {
  it('paints Backstage UI from the estate palette, not a second set of colours', () => {
    const vars = buiVars(dark, stateDark) as Record<string, string>;
    expect(vars['--bui-bg-app']).toBe(dark.canvas);
    expect(vars['--bui-bg-neutral-1']).toBe(dark.surface1);
    expect(vars['--bui-accent-bg']).toBe(dark.accent);
    expect(vars['--bui-accent-fg']).toBe(dark.inkOnAccent);
    expect(vars['--bui-negative-fg-subdued']).toBe(stateDark.red.ink);
    expect(vars['--bui-bg-solid']).toBe(dark.accent);
    expect(vars['--bui-fg-primary']).toBe(dark.textPrimary);
    expect(vars['--bui-fg-solid']).toBe(dark.inkOnAccent);
    expect(vars['--bui-fg-danger']).toBe(stateDark.red.ink);
    expect(vars['--bui-border-1']).toBe(dark.borderSubtle);
    expect(vars['--bui-font-regular']).toContain('BlinkMacSystemFont');
  });
});
