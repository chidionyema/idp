// The collapsed-sidebar mark: the first letter of `app.title` on a rounded
// tile in the estate accent. No vendor artwork (crew#459).
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import { makeStyles } from '@material-ui/core';
import { accent, accentSoft, inkOnAccent } from '../theme/tokens';

const useStyles = makeStyles({
  tile: {
    width: 28,
    height: 28,
    borderRadius: 7,
    background: `linear-gradient(135deg, ${accentSoft} 0%, ${accent} 100%)`,
    color: inkOnAccent,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 15,
    fontWeight: 700,
    flex: '0 0 auto',
  },
});

export const LogoIcon = () => {
  const classes = useStyles();
  const title = useApi(configApiRef).getOptionalString('app.title') ?? 'Estate';
  return (
    <span className={classes.tile} aria-hidden="true">
      {title.trim().charAt(0).toUpperCase()}
    </span>
  );
};
