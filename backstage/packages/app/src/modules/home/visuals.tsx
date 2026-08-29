// Visuals for the estate front page (crew#612, POLISH-SPEC.md). Founder, 2026-08-29:
// "I DONT SEE ICONS NOT CHART, NOTHING VISUAL".
//
// Pure SVG, no chart library, no colour literal: every tint comes from ../theme/tokens.
// Colour never carries a meaning alone — every state is drawn as icon + word + number, and
// each chart ships an aria-label sentence plus a visually hidden table of the same numbers.

import React from 'react';
import { makeStyles, useTheme } from '@material-ui/core/styles';
import type { SvgIconProps } from '@material-ui/core/SvgIcon';
import ErrorOutline from '@material-ui/icons/ErrorOutline';
import PersonOutline from '@material-ui/icons/PersonOutline';
import HistoryOutlined from '@material-ui/icons/HistoryOutlined';
import VisibilityOffOutlined from '@material-ui/icons/VisibilityOffOutlined';
import Autorenew from '@material-ui/icons/Autorenew';
import CheckCircleOutline from '@material-ui/icons/CheckCircleOutline';
import LayersOutlined from '@material-ui/icons/LayersOutlined';
import MeetingRoomOutlined from '@material-ui/icons/MeetingRoomOutlined';
import PlayCircleOutline from '@material-ui/icons/PlayCircleOutline';
import Timeline from '@material-ui/icons/Timeline';
import VpnKey from '@material-ui/icons/VpnKey';
import LocalShipping from '@material-ui/icons/LocalShipping';
import Storage from '@material-ui/icons/Storage';
import Memory from '@material-ui/icons/Memory';
import Dashboard from '@material-ui/icons/Dashboard';
import Public from '@material-ui/icons/Public';
import Schedule from '@material-ui/icons/Schedule';
import Extension from '@material-ui/icons/Extension';
import {
  State,
  STATE_ORDER,
  STATE_WORD,
  stateDark,
  stateLight,
  phone,
  ease,
  reducedMotion,
  monoFamily,
} from '../theme/tokens';

// ---------------------------------------------------------------- state icons

export type IconComponent = React.ComponentType<SvgIconProps>;

/** One icon per state. The icon is a hint; the word from STATE_WORD is always beside it. */
export const STATE_ICON: Record<State, IconComponent> = {
  red: ErrorOutline,
  needs: PersonOutline,
  stale: HistoryOutlined,
  blind: VisibilityOffOutlined,
  running: Autorenew,
  good: CheckCircleOutline,
};

/** How a state reads inside a sentence a stranger understands. */
export const STATE_PHRASE: Record<State, string> = {
  red: 'failing',
  needs: 'need you',
  stale: 'stale',
  blind: 'cannot be checked',
  running: 'starting or changing',
  good: 'working',
};

/** The tint set for the current theme mode. */
export function useTints(): Record<State, { ink: string; bg: string; edge: string }> {
  const theme = useTheme();
  return theme.palette.type === 'dark' ? stateDark : stateLight;
}

export function StateIcon(props: {
  state: State;
  fontSize?: SvgIconProps['fontSize'];
  className?: string;
}) {
  const { state, fontSize = 'small', className } = props;
  const tints = useTints();
  const Icon = STATE_ICON[state];
  return (
    <Icon
      aria-hidden
      className={className}
      fontSize={fontSize}
      htmlColor={tints[state].ink}
      data-state={state}
    />
  );
}

// -------------------------------------------------------------- section icons

export type Section = 'layers' | 'doors' | 'actions';

export const SECTION_ICON: Record<Section, IconComponent> = {
  layers: LayersOutlined,
  doors: MeetingRoomOutlined,
  actions: PlayCircleOutline,
};

export function SectionIcon(props: {
  section: Section;
  fontSize?: SvgIconProps['fontSize'];
  className?: string;
}) {
  const { section, fontSize = 'default', className } = props;
  const Icon = SECTION_ICON[section];
  return (
    <Icon
      aria-hidden
      className={className}
      fontSize={fontSize}
      color="inherit"
      data-section={section}
    />
  );
}

// --------------------------------------------------------------- system icons

/** Keyword -> icon, first match wins, read in order. Exported so a test can pin it. */
export const SYSTEM_ICON_KEYWORDS: { keywords: string[]; icon: IconComponent }[] = [
  { keywords: ['observ', 'trace', 'log', 'metric'], icon: Timeline },
  { keywords: ['secret', 'vault', 'identity', 'auth', 'login'], icon: VpnKey },
  { keywords: ['delivery', 'flux', 'deploy', 'ci'], icon: LocalShipping },
  { keywords: ['data', 'postgres', 'db', 'store'], icon: Storage },
  { keywords: ['ai', 'llm', 'model', 'router'], icon: Memory },
  { keywords: ['portal', 'backstage', 'catalog'], icon: Dashboard },
  { keywords: ['network', 'ingress', 'dns', 'edge'], icon: Public },
  { keywords: ['schedule', 'dagster', 'job'], icon: Schedule },
];

export const SYSTEM_ICON_FALLBACK: IconComponent = Extension;

/** Pick an icon for a system by name or title. Never throws; unknown names get Extension. */
export function systemIcon(idOrTitle: string): IconComponent {
  const needle = (idOrTitle || '').toLowerCase();
  for (const row of SYSTEM_ICON_KEYWORDS) {
    if (row.keywords.some(k => needle.includes(k))) return row.icon;
  }
  return SYSTEM_ICON_FALLBACK;
}

// -------------------------------------------------------------------- styles

const useStyles = makeStyles(theme => ({
  srOnly: {
    position: 'absolute',
    width: 1,
    height: 1,
    padding: 0,
    margin: -1,
    overflow: 'hidden',
    clip: 'rect(0 0 0 0)',
    whiteSpace: 'nowrap',
    border: 0,
  },
  donutWrap: {
    display: 'flex',
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing(4),
    [phone]: { flexDirection: 'column', alignItems: 'flex-start', gap: theme.spacing(2) },
  },
  donutFigure: { position: 'relative', flex: '0 0 auto' },
  centreNumber: {
    fontFamily: monoFamily,
    fontVariantNumeric: 'tabular-nums',
    fontSize: 34,
    fontWeight: 700,
    fill: theme.palette.text.primary,
  },
  centreWord: {
    fontSize: 13,
    fontWeight: 500,
    fill: theme.palette.text.secondary,
  },
  arc: {
    transition: `stroke-dasharray 300ms ${ease}`,
    [reducedMotion]: { transition: 'none' },
  },
  legend: {
    display: 'flex',
    flexDirection: 'column',
    gap: theme.spacing(1),
    margin: 0,
    padding: 0,
    listStyle: 'none',
  },
  legendRow: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1),
    fontSize: 14,
    color: theme.palette.text.primary,
  },
  legendWord: { fontWeight: 600 },
  legendNumber: {
    fontFamily: monoFamily,
    fontVariantNumeric: 'tabular-nums',
    fontWeight: 700,
    marginLeft: 'auto',
    paddingLeft: theme.spacing(2),
  },
  bars: {
    display: 'flex',
    flexDirection: 'column',
    gap: theme.spacing(1.5),
  },
  barRow: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(2),
    [phone]: { flexDirection: 'column', alignItems: 'stretch', gap: theme.spacing(0.5) },
  },
  barTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1),
    flex: '0 0 200px',
    fontSize: 15,
    fontWeight: 600,
    color: theme.palette.text.primary,
    [phone]: { flex: 'none' },
  },
  barTrack: {
    display: 'flex',
    flex: '1 1 auto',
    height: 14,
    borderRadius: 7,
    overflow: 'hidden',
    background: theme.palette.divider,
  },
  barSegment: {
    height: '100%',
    transition: `width 300ms ${ease}`,
    [reducedMotion]: { transition: 'none' },
  },
  barTotal: {
    fontFamily: monoFamily,
    fontVariantNumeric: 'tabular-nums',
    fontSize: 13,
    fontWeight: 700,
    color: theme.palette.text.secondary,
    flex: '0 0 auto',
    minWidth: 28,
    textAlign: 'right',
  },
}));

// --------------------------------------------------------------------- donut

const R = 45;
const C = 2 * Math.PI * R;

export function donutSentence(counts: Record<State, number>, total: number): string {
  const parts = STATE_ORDER.filter(s => (counts[s] || 0) > 0).map(
    s => `${counts[s]} ${STATE_PHRASE[s]}`,
  );
  const word = total === 1 ? 'service' : 'services';
  if (parts.length === 0) return `0 services`;
  return `${total} ${word}: ${parts.join(', ')}`;
}

export function StateDonut(props: {
  counts: Record<State, number>;
  total: number;
  size?: number;
}) {
  const { counts, total, size = 180 } = props;
  const classes = useStyles();
  const tints = useTints();
  const present = STATE_ORDER.filter(s => (counts[s] || 0) > 0);

  let offset = 0;
  const arcs = present.map(s => {
    const len = total > 0 ? (counts[s] / total) * C : 0;
    const arc = { state: s, len, offset };
    offset += len;
    return arc;
  });

  return (
    <div className={classes.donutWrap} data-testid="state-donut">
      <div className={classes.donutFigure}>
        <svg
          width={size}
          height={size}
          viewBox="0 0 120 120"
          role="img"
          aria-label={donutSentence(counts, total)}
        >
          <circle
            cx={60}
            cy={60}
            r={R}
            fill="none"
            strokeWidth={14}
            stroke={tints.blind.edge}
          />
          {arcs.map(a => (
            <circle
              key={a.state}
              className={classes.arc}
              cx={60}
              cy={60}
              r={R}
              fill="none"
              strokeWidth={14}
              stroke={tints[a.state].ink}
              strokeDasharray={`${a.len} ${Math.max(C - a.len, 0)}`}
              strokeDashoffset={-a.offset}
              transform="rotate(-90 60 60)"
              data-arc={a.state}
            />
          ))}
          <text
            className={classes.centreNumber}
            x={60}
            y={58}
            textAnchor="middle"
            dominantBaseline="middle"
          >
            {total}
          </text>
          <text className={classes.centreWord} x={60} y={80} textAnchor="middle">
            {total === 1 ? 'service' : 'services'}
          </text>
        </svg>
      </div>

      <ul className={classes.legend}>
        {present.map(s => (
          <li key={s} className={classes.legendRow} data-legend={s}>
            <StateIcon state={s} />
            <span className={classes.legendWord}>{STATE_WORD[s]}</span>
            <span className={classes.legendNumber}>{counts[s]}</span>
          </li>
        ))}
      </ul>

      <table className={classes.srOnly}>
        <caption>Pieces by state</caption>
        <thead>
          <tr>
            <th scope="col">State</th>
            <th scope="col">Pieces</th>
          </tr>
        </thead>
        <tbody>
          {STATE_ORDER.map(s => (
            <tr key={s}>
              <th scope="row">{STATE_WORD[s]}</th>
              <td>{counts[s] || 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------- bars

export type SystemRow = {
  id: string;
  title: string;
  counts: Record<State, number>;
};

export function rowSentence(row: SystemRow, total: number): string {
  const parts = STATE_ORDER.filter(s => (row.counts[s] || 0) > 0).map(
    s => `${row.counts[s]} ${STATE_PHRASE[s]}`,
  );
  const word = total === 1 ? 'service' : 'services';
  if (parts.length === 0) return `${row.title}: no services`;
  return `${row.title}: ${total} ${word}, ${parts.join(', ')}`;
}

export function SystemBars(props: { rows: SystemRow[] }) {
  const { rows } = props;
  const classes = useStyles();
  const tints = useTints();
  if (!rows || rows.length === 0) return null;

  return (
    <div className={classes.bars} role="list" data-testid="system-bars">
      {rows.map(row => {
        const total = STATE_ORDER.reduce((n, s) => n + (row.counts[s] || 0), 0);
        const Icon = systemIcon(row.id || row.title);
        return (
          <div
            key={row.id}
            role="listitem"
            className={classes.barRow}
            aria-label={rowSentence(row, total)}
            data-testid={`bar-${row.id}`}
          >
            <span className={classes.barTitle}>
              <Icon aria-hidden fontSize="small" color="inherit" />
              {row.title}
            </span>
            <span className={classes.barTrack} aria-hidden>
              {STATE_ORDER.filter(s => (row.counts[s] || 0) > 0).map(s => (
                <span
                  key={s}
                  className={classes.barSegment}
                  data-segment={s}
                  title={`${row.counts[s]} ${STATE_WORD[s]}`}
                  style={{
                    background: tints[s].ink,
                    width: `${total > 0 ? (row.counts[s] / total) * 100 : 0}%`,
                    minWidth: 4,
                  }}
                />
              ))}
            </span>
            <span className={classes.barTotal}>{total}</span>
          </div>
        );
      })}
    </div>
  );
}
