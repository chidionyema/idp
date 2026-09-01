// The Reports page (crew#684, founder 2026-09-01: "can we automate all reports, need report tab in
// Backstage"). One tile per report the estate writes on a clock, each dated against its schedule
// and red when late; the chosen report's markdown below. Nothing is computed here: the writers are
// bin/idp-reports-render in estate-state.yml and estate-inventory.yml, the store is the state
// branch, the door is the /estate-state proxy (backstage/app-config.yaml).
import { useEffect, useState } from 'react';
import {
  Content,
  Link,
  MarkdownContent,
  Page,
} from '@backstage/core-components';
import { Typography, makeStyles } from '@material-ui/core';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Pill } from './EstateHome';
import { ago } from './estate';
import { monoFamily } from '../theme/tokens';
import {
  FRESHNESS_WORD,
  REPORTS_BASE,
  Report,
  everySentence,
  freshness,
  freshnessState,
  reportsSentence,
} from './reportIndex';
import { useReportBody, useReports } from './useReports';

export const TITLE = 'Reports';
export const LEAD =
  'Every report the estate writes for you, produced on a clock, dated, and red when it is late.';

const useStyles = makeStyles(theme => ({
  header: { marginBottom: theme.spacing(3) },
  lead: { fontSize: 17, margin: theme.spacing(1, 0, 0) },
  grid: {
    display: 'grid',
    gap: theme.spacing(1.5),
    gridTemplateColumns: 'repeat(auto-fill, minmax(22em, 1fr))',
  },
  tile: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'stretch',
    textAlign: 'left',
    gap: theme.spacing(1),
    padding: theme.spacing(2),
    borderRadius: 12,
    border: `1px solid ${theme.palette.divider}`,
    background: theme.palette.background.paper,
    color: theme.palette.text.primary,
    font: 'inherit',
    cursor: 'pointer',
    minWidth: 0,
    '&:focus-visible': { outline: `2px solid ${theme.palette.primary.main}` },
  },
  chosen: { borderColor: theme.palette.primary.main },
  tileTop: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1),
    flexWrap: 'wrap',
  },
  tileTitle: { fontWeight: 600, fontSize: 18, flex: '1 1 10em' },
  small: { fontSize: 13, color: theme.palette.text.secondary, margin: 0 },
  mono: { fontFamily: monoFamily, fontSize: 12, overflowWrap: 'anywhere' },
  body: {
    marginTop: theme.spacing(3),
    padding: theme.spacing(2),
    borderRadius: 12,
    border: `1px solid ${theme.palette.divider}`,
    background: theme.palette.background.paper,
    overflowX: 'auto',
    '& table': { borderCollapse: 'collapse', fontSize: 13 },
    '& th, & td': {
      textAlign: 'left',
      verticalAlign: 'top',
      padding: theme.spacing(0.5, 1),
      borderBottom: `1px solid ${theme.palette.divider}`,
    },
  },
  bodyTop: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: theme.spacing(1),
    flexWrap: 'wrap',
    marginBottom: theme.spacing(1),
  },
}));

const Tile = ({
  report,
  now,
  chosen,
  onChoose,
}: {
  report: Report;
  now: number;
  chosen: boolean;
  onChoose: () => void;
}) => {
  const classes = useStyles();
  const when = ago(report.generatedAt, now);
  const why = report.blind
    ? 'Blind: the source could not be read'
    : `${FRESHNESS_WORD[freshness(report, now)]}${
        when ? `, produced ${when}` : ''
      }`;
  return (
    <button
      type="button"
      className={`${classes.tile} ${chosen ? classes.chosen : ''}`}
      onClick={onChoose}
      aria-pressed={chosen}
      data-testid={`report-${report.id}`}
    >
      <div className={classes.tileTop}>
        <span className={classes.tileTitle}>{report.title}</span>
        <Pill state={freshnessState(report, now)} why={why} />
      </div>
      <p className={classes.small}>
        {why}. Written {everySentence(report.scheduleMinutes)}.
      </p>
      {report.summary && <p className={classes.small}>{report.summary}</p>}
    </button>
  );
};

export const Reports = () => {
  const classes = useStyles();
  const config = useApi(configApiRef);
  const base = config.getOptionalString('backend.baseUrl') ?? '';
  const loaded = useReports();
  const [chosenId, setChosenId] = useState<string | undefined>(undefined);
  const now = Date.now();
  const reports = loaded.state === 'ready' ? loaded.reports : [];
  const chosen = reports.find(r => r.id === chosenId) ?? reports[0];
  useEffect(() => {
    if (chosen && chosen.id !== chosenId) setChosenId(chosen.id);
  }, [chosen, chosenId]);
  const body = useReportBody(chosen?.file, chosen?.generatedAt ?? '');
  return (
    <Page themeId="home">
      <Content>
        <header className={classes.header}>
          <Typography variant="h1" component="h1">
            {TITLE}
          </Typography>
          <p className={classes.lead}>{LEAD}</p>
          {loaded.state === 'loading' && (
            <p className={classes.lead} data-testid="reports-loading">
              Reading the report index.
            </p>
          )}
          {loaded.state === 'error' && (
            <p className={classes.lead} data-testid="reports-error">
              The report index could not be read, so no report is known.{' '}
              <span className={classes.mono}>{loaded.error}</span>
            </p>
          )}
          {loaded.state === 'ready' && (
            <p className={classes.lead} data-testid="reports-sentence">
              {reportsSentence(reports, now)}
            </p>
          )}
        </header>
        <div className={classes.grid}>
          {reports.map(r => (
            <Tile
              key={r.id}
              report={r}
              now={now}
              chosen={r.id === chosen?.id}
              onChoose={() => setChosenId(r.id)}
            />
          ))}
        </div>
        {chosen && (
          <section className={classes.body} data-testid="report-body">
            <div className={classes.bodyTop}>
              <span className={classes.small}>
                {chosen.source ? `Source: ${chosen.source}.` : ''}
              </span>
              <Link to={`${base}/api/proxy${REPORTS_BASE}${chosen.file}`}>
                The file itself
              </Link>
            </div>
            {body.state === 'loading' && (
              <p className={classes.small}>Reading {chosen.title}.</p>
            )}
            {body.state === 'error' && (
              <p className={classes.small} data-testid="report-body-error">
                This report could not be read.{' '}
                <span className={classes.mono}>{body.error}</span>
              </p>
            )}
            {body.state === 'ready' && <MarkdownContent content={body.text} />}
          </section>
        )}
      </Content>
    </Page>
  );
};
