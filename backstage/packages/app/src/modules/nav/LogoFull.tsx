// The open-sidebar wordmark. It is the estate's name from `app.title`, not a
// vendor SVG: the portal an investor opens must name the thing it shows
// (crew#459), and the name lives in config so this file names nothing (LAW 46).
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import { makeStyles } from '@material-ui/core';
import { LogoIcon } from './LogoIcon';
import { inkOnNavy } from '../theme/tokens';

const useStyles = makeStyles({
  root: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    whiteSpace: 'nowrap',
  },
  word: {
    color: inkOnNavy,
    fontSize: 17,
    fontWeight: 600,
    letterSpacing: '0.02em',
    lineHeight: 1,
  },
});

export const LogoFull = () => {
  const classes = useStyles();
  const title = useApi(configApiRef).getOptionalString('app.title') ?? 'Estate';
  return (
    <span className={classes.root} data-testid="estate-wordmark">
      <LogoIcon />
      <span className={classes.word}>{title}</span>
    </span>
  );
};
