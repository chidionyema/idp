import { render, screen, within } from '@testing-library/react';
import Timeline from '@material-ui/icons/Timeline';
import VpnKey from '@material-ui/icons/VpnKey';
import Extension from '@material-ui/icons/Extension';
import {
  StateDonut,
  SystemBars,
  systemIcon,
  SYSTEM_ICON_KEYWORDS,
} from './visuals';
import { State, STATE_ORDER } from '../theme/tokens';

const counts = (over: Partial<Record<State, number>>): Record<State, number> => ({
  red: 0,
  needs: 0,
  stale: 0,
  blind: 0,
  running: 0,
  good: 0,
  ...over,
});

describe('StateDonut', () => {
  it('says the whole verdict in one sentence for a mixed count', () => {
    render(<StateDonut counts={counts({ red: 6, needs: 2, good: 23 })} total={31} />);
    expect(screen.getByRole('img')).toHaveAttribute(
      'aria-label',
      '31 services: 6 failing, 2 need you, 23 working',
    );
  });

  it('says "0 services" and draws an empty ring when nothing is known', () => {
    render(<StateDonut counts={counts({})} total={0} />);
    expect(screen.getByRole('img')).toHaveAttribute('aria-label', '0 services');
    expect(document.querySelectorAll('[data-arc]')).toHaveLength(0);
    expect(screen.getByTestId('state-donut')).toHaveTextContent('0');
    expect(screen.getByTestId('state-donut')).toHaveTextContent('services');
  });

  it('shows a legend row only for the states that have a number', () => {
    render(<StateDonut counts={counts({ red: 6, needs: 2, good: 23 })} total={31} />);
    const donut = screen.getByTestId('state-donut');
    expect(donut.querySelectorAll('[data-legend]')).toHaveLength(3);
    expect(donut.querySelector('[data-legend="red"]')).not.toBeNull();
    expect(donut.querySelector('[data-legend="stale"]')).toBeNull();
    expect(donut.querySelector('[data-legend="red"]')).toHaveTextContent('Red');
    expect(donut.querySelector('[data-legend="needs"]')).toHaveTextContent('Needs you');
    expect(donut.querySelector('[data-legend="good"]')).toHaveTextContent('23');
  });

  it('keeps every number in a hidden table, one row per state', () => {
    render(<StateDonut counts={counts({ red: 6, needs: 2, good: 23 })} total={31} />);
    const table = screen.getByRole('table');
    const bodyRows = within(table).getAllByRole('row').slice(1);
    expect(bodyRows).toHaveLength(STATE_ORDER.length);
    expect(bodyRows[0]).toHaveTextContent('Red');
    expect(bodyRows[0]).toHaveTextContent('6');
    expect(bodyRows[2]).toHaveTextContent('Stale');
    expect(bodyRows[2]).toHaveTextContent('0');
  });
});

describe('SystemBars', () => {
  const rows = [
    { id: 'observability', title: 'Observability', counts: counts({ red: 1, good: 3 }) },
    { id: 'delivery', title: 'Delivery', counts: counts({ needs: 2 }) },
  ];

  it('draws one row per system with a sentence and titled segments', () => {
    render(<SystemBars rows={rows} />);
    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveAttribute(
      'aria-label',
      'Observability: 4 services, 1 failing, 3 working',
    );
    expect(items[1]).toHaveAttribute('aria-label', 'Delivery: 2 services, 2 need you');

    const first = screen.getByTestId('bar-observability');
    const segments = Array.from(first.querySelectorAll('[data-segment]'));
    expect(segments.map(s => s.getAttribute('title'))).toEqual(['1 Red', '3 Good']);
    expect(first).toHaveTextContent('Observability');
    expect(first).toHaveTextContent('4');

    const second = screen.getByTestId('bar-delivery');
    expect(
      Array.from(second.querySelectorAll('[data-segment]')).map(s =>
        s.getAttribute('title'),
      ),
    ).toEqual(['2 Needs you']);
  });

  it('renders nothing when there are no systems', () => {
    const { container } = render(<SystemBars rows={[]} />);
    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByTestId('system-bars')).toBeNull();
  });
});

describe('systemIcon', () => {
  it('reads the keyword table and falls back for an unknown name', () => {
    expect(systemIcon('observability')).toBe(Timeline);
    expect(systemIcon('secret-store')).toBe(VpnKey);
    expect(systemIcon('unknown-thing')).toBe(Extension);
    expect(systemIcon('')).toBe(Extension);
  });

  it('exports the table it reads, first match wins', () => {
    expect(SYSTEM_ICON_KEYWORDS[0].keywords).toContain('observ');
    expect(SYSTEM_ICON_KEYWORDS[0].icon).toBe(Timeline);
    expect(SYSTEM_ICON_KEYWORDS.map(r => r.keywords.length).every(n => n > 0)).toBe(true);
  });
});
