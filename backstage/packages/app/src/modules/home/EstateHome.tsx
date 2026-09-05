// The founder god view (crew#401) as the portal's front page (crew#459).
//
// Every card is a `founder-surface` entity read from the catalogue at render
// time. Nothing here names a hostname or a surface: the list is the catalogue,
// so the gate that refuses an unregistered surface (crew#401 CP3) keeps this
// page complete, and the catalogue-drift row (crew#401 CP4) keeps it honest.
import { useEffect, useState } from 'react';
import { Entity } from '@backstage/catalog-model';
import {
  Content,
  ContentHeader,
  Header,
  HeaderLabel,
  InfoCard,
  ItemCardGrid,
  Link,
  LinkButton,
  Page,
  Progress,
  ResponseErrorPanel,
} from '@backstage/core-components';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import { catalogApiRef } from '@backstage/plugin-catalog-react';
import { Grid, Typography, makeStyles } from '@material-ui/core';

export const FOUNDER_SURFACE_TYPE = 'founder-surface';

const useStyles = makeStyles(theme => ({
  card: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
  },
  description: {
    flex: 1,
    marginBottom: theme.spacing(2),
    display: '-webkit-box',
    WebkitLineClamp: 4,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
  links: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: theme.spacing(1),
  },
  count: {
    fontSize: 40,
    fontWeight: 700,
    lineHeight: 1,
  },
}));

type Loaded =
  | { state: 'loading' }
  | { state: 'error'; error: Error }
  | { state: 'ready'; surfaces: Entity[]; totals: Record<string, number> };

/** One card per founder surface: title, what it is, and its doors. */
export const SurfaceCard = ({ entity }: { entity: Entity }) => {
  const classes = useStyles();
  const title = entity.metadata.title ?? entity.metadata.name;
  const links = entity.metadata.links ?? [];
  const entityPath = `/catalog/${entity.metadata.namespace ?? 'default'}/${entity.kind.toLowerCase()}/${entity.metadata.name}`;
  return (
    <InfoCard
      title={title}
      className={classes.card}
      deepLink={{ title: 'Catalogue entry', link: entityPath }}
      data-testid={`surface-${entity.metadata.name}`}
    >
      <Typography variant="body2" className={classes.description}>
        {entity.metadata.description}
      </Typography>
      <div className={classes.links}>
        {links.map(link => (
          <LinkButton
            key={link.url}
            to={link.url}
            color="primary"
            variant={link === links[0] ? 'contained' : 'outlined'}
            size="small"
          >
            {link.title ?? link.url}
          </LinkButton>
        ))}
      </div>
    </InfoCard>
  );
};

const Total = ({ label, value, to }: { label: string; value: number; to: string }) => {
  const classes = useStyles();
  return (
    <Grid item xs={6} sm={3}>
      <InfoCard>
        <Link to={to} underline="none" color="inherit">
          <Typography className={classes.count}>{value}</Typography>
          <Typography variant="overline">{label}</Typography>
        </Link>
      </InfoCard>
    </Grid>
  );
};

export const EstateHome = () => {
  const catalogApi = useApi(catalogApiRef);
  const config = useApi(configApiRef);
  const title = config.getOptionalString('app.title') ?? 'Estate';
  const [loaded, setLoaded] = useState<Loaded>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [surfaces, all] = await Promise.all([
          catalogApi.getEntities({
            filter: { 'spec.type': FOUNDER_SURFACE_TYPE },
            fields: ['kind', 'metadata', 'spec.type'],
          }),
          catalogApi.getEntities({ fields: ['kind', 'metadata.name'] }),
        ]);
        const totals: Record<string, number> = {};
        for (const e of all.items) {
          totals[e.kind] = (totals[e.kind] ?? 0) + 1;
        }
        if (!cancelled) {
          setLoaded({
            state: 'ready',
            surfaces: [...surfaces.items].sort((a, b) =>
              (a.metadata.title ?? a.metadata.name).localeCompare(
                b.metadata.title ?? b.metadata.name,
              ),
            ),
            totals,
          });
        }
      } catch (error) {
        if (!cancelled) setLoaded({ state: 'error', error: error as Error });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [catalogApi]);

  return (
    <Page themeId="home">
      <Header title={title} subtitle="Every door into the estate, read from the catalogue">
        {loaded.state === 'ready' && (
          <HeaderLabel label="Surfaces" value={String(loaded.surfaces.length)} />
        )}
      </Header>
      <Content>
        {loaded.state === 'loading' && <Progress />}
        {loaded.state === 'error' && <ResponseErrorPanel error={loaded.error} />}
        {loaded.state === 'ready' && (
          <>
            <Grid container spacing={2} style={{ marginBottom: 16 }}>
              <Total label="Components" value={loaded.totals.Component ?? 0} to="/catalog?filters[kind]=component" />
              <Total label="Systems" value={loaded.totals.System ?? 0} to="/catalog?filters[kind]=system" />
              <Total label="Resources" value={loaded.totals.Resource ?? 0} to="/catalog?filters[kind]=resource" />
              <Total label="APIs" value={loaded.totals.API ?? 0} to="/api-docs" />
            </Grid>
            <ContentHeader title="Founder surfaces" />
            {loaded.surfaces.length === 0 ? (
              <Typography data-testid="no-surfaces">
                The catalogue holds no {FOUNDER_SURFACE_TYPE} entity yet.
              </Typography>
            ) : (
              <ItemCardGrid>
                {loaded.surfaces.map(entity => (
                  <SurfaceCard key={entity.metadata.name} entity={entity} />
                ))}
              </ItemCardGrid>
            )}
          </>
        )}
      </Content>
    </Page>
  );
};
