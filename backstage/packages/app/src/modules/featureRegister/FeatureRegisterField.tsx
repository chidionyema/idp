// crew#857: scaffolder custom field extension that reads the feature register
// (platform/features/features.yaml) at render time and renders the rows and
// their tiers as the choices. As the selection changes, it shows the price
// and fit from the pre-computed plan (plan.json).
//
// Reads from /api/feature-register/register (features.yaml) and
// /api/feature-register/plan (plan.json), both served by the backend plugin.
// Returns { feature: string, tier: string } — the template steps reference
// ${{ parameters.featureTier.feature }} and ${{ parameters.featureTier.tier }}.
import React, { useEffect, useState } from 'react';
import FormControl from '@material-ui/core/FormControl';
import FormHelperText from '@material-ui/core/FormHelperText';
import InputLabel from '@material-ui/core/InputLabel';
import MenuItem from '@material-ui/core/MenuItem';
import Select from '@material-ui/core/Select';
import Typography from '@material-ui/core/Typography';
import { makeStyles } from '@material-ui/core/styles';
import { useApi, fetchApiRef, configApiRef } from '@backstage/core-plugin-api';

const useStyles = makeStyles(theme => ({
  root: { margin: theme.spacing(2, 0) },
  fieldRow: { display: 'flex', gap: theme.spacing(2) },
  select: { minWidth: 240 },
  priceCard: {
    marginTop: theme.spacing(2),
    padding: theme.spacing(1.5),
    backgroundColor: theme.palette.background.paper,
    border: `1px solid ${theme.palette.divider}`,
    borderRadius: theme.shape.borderRadius,
  },
  priceLabel: { fontWeight: 600 },
  fitYes: { color: theme.palette.success.main },
  fitNo: { color: theme.palette.error.main },
  tierChip: {
    cursor: 'pointer',
    padding: theme.spacing(0.5, 1.5),
    marginRight: theme.spacing(1),
    borderRadius: theme.shape.borderRadius,
    border: `1px solid ${theme.palette.divider}`,
    display: 'inline-block',
    '&:hover': { borderColor: theme.palette.primary.main },
  },
  tierSelected: {
    backgroundColor: theme.palette.primary.main,
    color: theme.palette.primary.contrastText,
    borderColor: theme.palette.primary.main,
  },
}));

export interface FeatureRegisterFieldProps {
  onChange: (value: { feature: string; tier: string }) => void;
  rawErrors?: string[];
  required?: boolean;
  formData?: { feature?: string; tier?: string };
}

interface FeatureEntry {
  name: string;
  title: string;
  tiers: Array<{ name: string; what?: string; default?: boolean }>;
  default?: string;
}

interface PlanEntry {
  name: string;
  tier: string;
  cpu: number;
  memory_gb: number;
  storage_gb: number;
  note?: string;
}

interface PlanData {
  features: PlanEntry[];
  total: { cpu: number; memory_gb: number; storage_gb: number };
  node_today: {
    name: string; ocpus: number; memory_gb: number; usd_month: number; fits: boolean;
  };
  node_smallest?: {
    name: string; ocpus: number; memory_gb: number; usd_month: number;
  } | null;
}

interface RegisterData {
  features: FeatureEntry[];
  [key: string]: unknown;
}

export const FeatureRegisterField = ({
  onChange,
  rawErrors,
  required,
  formData,
}: FeatureRegisterFieldProps) => {
  const classes = useStyles();
  const fetchApi = useApi(fetchApiRef);
  const configApi = useApi(configApiRef);
  const [register, setRegister] = useState<RegisterData | null>(null);
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const baseUrl = configApi.getOptionalString('app.baseUrl') || '';

  useEffect(() => {
    async function load() {
      try {
        const [regRes, planRes] = await Promise.all([
          fetchApi.fetch(`${baseUrl}/api/feature-register/register`),
          fetchApi.fetch(`${baseUrl}/api/feature-register/plan`),
        ]);
        if (!regRes.ok) {
          setError(`Register not available (${regRes.status})`);
          setLoading(false);
          return;
        }
        const regText = await regRes.text();
        const yaml = await import('js-yaml');
        const regData = yaml.load(regText) as RegisterData;
        setRegister(regData);

        if (planRes.ok) {
          const planData = (await planRes.json()) as PlanData;
          setPlan(planData);
        }
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        setLoading(false);
      }
    }
    load();
  }, [baseUrl, fetchApi]);

  if (loading) {
    return <FormHelperText>Loading available features…</FormHelperText>;
  }

  if (error || !register) {
    return (
      <FormHelperText error>
        {error || 'Feature register not available'}
      </FormHelperText>
    );
  }

  const features = register.features || [];
  const selectedFeature = formData?.feature || '';
  const selectedTier = formData?.tier || '';

  const currentFeature = features.find(f => f.name === selectedFeature);
  const tiers = currentFeature?.tiers || [];
  const defaultTier = currentFeature?.default || (tiers.length > 0 ? String(tiers[0].name) : '');

  const handleFeatureChange = (event: React.ChangeEvent<{ value: unknown }>) => {
    const newFeature = event.target.value as string;
    const feature = features.find(f => f.name === newFeature);
    const newTier = feature?.default || (feature?.tiers?.[0] ? String(feature.tiers[0].name) : '');
    onChange({ feature: newFeature, tier: newTier });
  };

  const handleTierClick = (tierName: string) => {
    onChange({ feature: selectedFeature, tier: tierName });
  };

  const planEntry = plan?.features?.find(
    f => f.name === selectedFeature && f.tier === selectedTier,
  );
  const defaultPlanEntry = plan?.features?.find(
    f => f.name === selectedFeature && f.tier === defaultTier,
  );

  const displayEntry = planEntry || defaultPlanEntry;
  const nodeToday = plan?.node_today;
  const nodeSmallest = plan?.node_smallest;

  return (
    <div className={classes.root}>
      <div className={classes.fieldRow}>
        <FormControl
          required={required}
          error={!!(rawErrors?.length)}
          className={classes.select}
        >
          <InputLabel>Feature</InputLabel>
          <Select
            value={selectedFeature}
            onChange={handleFeatureChange}
            label="Feature"
          >
            {features.map(f => (
              <MenuItem key={f.name} value={f.name}>
                {f.title || f.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </div>

      {selectedFeature && tiers.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <FormHelperText style={{ marginBottom: 4 }}>Tier</FormHelperText>
          <div>
            {tiers.map(t => {
              const tName = String(t.name);
              const isSelected = tName === selectedTier || (!selectedTier && tName === defaultTier);
              return (
                <span
                  key={tName}
                  className={`${classes.tierChip} ${isSelected ? classes.tierSelected : ''}`}
                  onClick={() => handleTierClick(tName)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') handleTierClick(tName); }}
                >
                  {t.what || tName}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {displayEntry && nodeToday && (
        <div className={classes.priceCard}>
          <Typography variant="body2" className={classes.priceLabel}>
            Plan: {selectedFeature}/{selectedTier || defaultTier}
          </Typography>
          <Typography variant="body2">
            Resources: {displayEntry.cpu} CPU, {displayEntry.memory_gb} GB RAM, {displayEntry.storage_gb} GB storage
          </Typography>
          <Typography variant="body2">
            Total (all enabled features): {plan?.total.cpu} CPU, {plan?.total.memory_gb} GB RAM, {plan?.total.storage_gb} GB storage
          </Typography>
          {nodeToday.fits ? (
            <Typography variant="body2" className={classes.fitYes}>
              ✓ Fits current node ({nodeToday.name}) — USD {nodeToday.usd_month}/mo
            </Typography>
          ) : (
            <>
              <Typography variant="body2" className={classes.fitNo}>
                ✗ Does not fit current node ({nodeToday.name} — USD {nodeToday.usd_month}/mo)
              </Typography>
              {nodeSmallest ? (
                <Typography variant="body2" className={classes.fitYes}>
                  Smallest node that fits: {nodeSmallest.name} — USD {nodeSmallest.usd_month}/mo
                </Typography>
              ) : (
                <Typography variant="body2" className={classes.fitNo}>
                  No node size in the register holds this combination.
                </Typography>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};
