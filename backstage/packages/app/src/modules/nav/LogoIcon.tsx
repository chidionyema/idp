// The collapsed-sidebar mark: the first letter of `app.title` on a rounded
// tile in the estate accent. No vendor artwork (crew#459).
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import { makeStyles } from '@material-ui/core';

const useStyles = makeStyles({
  tile: {
    width: 28,
    height: 28,
    borderRadius: 7,
    background: 'linear-gradient(135deg, #f2b64b 0%, #e0762a 100%)',
    color: '#141a26',
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
