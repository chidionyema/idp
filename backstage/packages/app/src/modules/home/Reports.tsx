// The Reports page (crew#684, founder 2026-09-01: "can we automate all reports, need report tab in
// Backstage"). One tile per report the estate writes on a clock, each dated against its schedule
// and red when late; the chosen report's markdown below. Nothing is computed here: the writers are
// bin/idp-reports-render in estate-state.yml and estate-inventory.yml, the store is the state
// branch, the door is the /estate-state proxy (backstage/app-config.yaml).
//
// crew#843: the page top, the tiles and the grid come from modules/shell now. The whole tile used
// to be one button, which meant a screen reader announced the state, the title, the schedule and
// the summary as the label of a single control; the title is the control now and the rest is text.
import { useEffect, useState } from 'react';
import { Link, MarkdownContent } from '@backstage/core-components';
import { Text } from '@backstage/ui';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Pill } from './EstateHome';
import { ago } from './estate';
import {
  EstatePage,
  Name,
  Section,
  Summary,
  Tile,
  Tiles,
  Unread,
  Waiting,
} from '../shell';
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

const ReportTile = ({
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
  const when = ago(report.generatedAt, now);
  const why = report.blind
    ? 'Blind: the source could not be read'
    : `${FRESHNESS_WORD[freshness(report, now)]}${
        when ? `, produced ${when}` : ''
      }`;
  return (
    <Tile
      title={report.title}
      onChoose={onChoose}
      chosen={chosen}
      testId={`report-${report.id}`}
      state={freshnessState(report, now)}
      badge={<Pill state={freshnessState(report, now)} why={why} />}
    >
      <Text variant="body-small" color="secondary">
        {why}. Written {everySentence(report.scheduleMinutes)}.
      </Text>
      {report.summary && (
        <Text variant="body-small" color="secondary">
          {report.summary}
        </Text>
      )}
    </Tile>
  );
};

export const Reports = () => {
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
    <EstatePage title={TITLE} lead={LEAD}>
      {loaded.state === 'loading' && (
        <Waiting testId="reports-loading">Reading the report index.</Waiting>
      )}
      {loaded.state === 'error' && (
        <Unread testId="reports-error" detail={loaded.error}>
          The report index could not be read, so no report is known.
        </Unread>
      )}
      {loaded.state === 'ready' && (
        <Summary testId="reports-sentence">
          {reportsSentence(reports, now)}
        </Summary>
      )}
      <Tiles>
        {reports.map(r => (
          <ReportTile
            key={r.id}
            report={r}
            now={now}
            chosen={r.id === chosen?.id}
            onChoose={() => setChosenId(r.id)}
          />
        ))}
      </Tiles>
      {chosen && (
        <Section title={chosen.title}>
          <div className="estate-panel" data-testid="report-body">
            <div className="estate-panel-top">
              <Text variant="body-small" color="secondary">
                {chosen.source ? `Source: ${chosen.source}.` : ''}
              </Text>
              <Link to={`${base}/api/proxy${REPORTS_BASE}${chosen.file}`}>
                The file itself
              </Link>
            </div>
            {body.state === 'loading' && (
              <Waiting>Reading {chosen.title}.</Waiting>
            )}
            {body.state === 'error' && (
              <p
                className="estate-state-line estate-unread"
                role="alert"
                data-testid="report-body-error"
              >
                This report could not be read. <Name>{body.error}</Name>
              </p>
            )}
            {body.state === 'ready' && <MarkdownContent content={body.text} />}
          </div>
        </Section>
      )}
    </EstatePage>
  );
};
