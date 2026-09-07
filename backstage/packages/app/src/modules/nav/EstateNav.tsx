// Buyer first (founder 2026-09-02: catalogue, health, docs, login first; the content pane
// scrolls, the nav stays). Backstage's own Sidebar is the chrome (LAW 43). Each door is a
// SidebarItem, not a SidebarGroup of one and not a submenu: a group made hover expand into a
// second click (founder 2026-09-03: "outdated interactions"). The buyer's five doors sit
// above a divider, the operator's five below it, and every door is one click. Find is
// Backstage's own search modal (Cmd/Ctrl+K). Every page the nav does not list is still
// published at its path and still graded by bin/idp-login-drill.
//
// On a phone (founder, 2026-09-01: "I am the one using it and I don't like it") the menu
// slides in from the left behind a menu button in the top-left corner. Backstage's Sidebar
// folds itself into a bottom bar under 600px, ten tabs wide, and the founder read that as
// "there is no menu". The phone menu is Material UI's own Drawer, temporary variant: it is
// the component every phone menu on the web is built from, it closes on tap, on Escape and
// on the backdrop, and it is the same ten doors in the same order.
//
// Icons are Remix, the icon set Backstage's own IconElement prefers (Material icons are
// deprecated there); remixIcon.tsx wraps them into the shape SidebarItem wants.
//
// crew#612 item 3: /#screens and /#kubernetes were hash-jumps that looked like pages;
// removed. Screens section is visible on Today (/). Kubernetes is in the catalog.
// crew#612 item 1: /create added; scaffolderPlugin registered in App.tsx.
// crew#612 item 3: DnsIcon for Kubernetes so Ops keeps the single gear icon.
import { Fragment, useEffect, useState } from 'react';
import {
  Link,
  Sidebar,
  SidebarDivider,
  SidebarItem,
  SidebarSpace,
} from '@backstage/core-components';
import { NavContentBlueprint } from '@backstage/plugin-app-react';
import {
  SearchModal,
  SearchModalProvider,
  SidebarSearchModal,
  useSearchModal,
} from '@backstage/plugin-search';
import Drawer from '@material-ui/core/Drawer';
import IconButton from '@material-ui/core/IconButton';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemIcon from '@material-ui/core/ListItemIcon';
import ListItemText from '@material-ui/core/ListItemText';
import Typography from '@material-ui/core/Typography';
import { makeStyles, useTheme } from '@material-ui/core/styles';
import useMediaQuery from '@material-ui/core/useMediaQuery';
import {
  RiAddCircleLine,
  RiBookOpenLine,
  RiCalendarLine,
  RiCloseLine,
  RiMenuLine,
  RiNodeTree,
  RiPulseLine,
  RiSearchLine,
  RiServerLine,
  RiStackLine,
  RiToolsLine,
  RiUserLine,
} from '@remixicon/react';
import { remix } from './remixIcon';
import { SidebarLogo } from './SidebarLogo';
import { LogoIcon } from './LogoIcon';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';

const MenuIcon = remix(RiMenuLine);
const CloseIcon = remix(RiCloseLine);
const TodayIcon = remix(RiCalendarLine);
const DnsIcon = remix(RiServerLine);
const LayersIcon = remix(RiStackLine);
const AddCircleOutlineIcon = remix(RiAddCircleLine);
const AccountTreeIcon = remix(RiNodeTree);
const BuildIcon = remix(RiToolsLine);
const TimelineIcon = remix(RiPulseLine);
const SearchIcon = remix(RiSearchLine);
const MenuBookIcon = remix(RiBookOpenLine);
const AccountCircleIcon = remix(RiUserLine);

export const NAV = [
  { title: 'Home', to: '/', icon: TodayIcon },
  { title: 'Catalogue', to: '/catalog', icon: LayersIcon },
  { title: 'Health', to: '/ops', icon: TimelineIcon },
  { title: 'Docs', to: '/docs', icon: MenuBookIcon },
  { title: 'You', to: '/settings', icon: AccountCircleIcon },
  { title: 'Create', to: '/create', icon: AddCircleOutlineIcon },
  { title: 'Map', to: '/catalog-graph', icon: AccountTreeIcon },
  { title: 'Kubernetes', to: '/catalog?filters%5Bkind%5D=Component', icon: DnsIcon },
  { title: 'Tools', to: '/tools', icon: BuildIcon },
  { title: 'Find', to: '/search', icon: SearchIcon },
] as const;

/** The first doors a visitor sees; the rest sit below the divider. */
export const BUYER_COUNT = 5;

// The words a person reads on the phone menu. bin/idp-login-drill grades the phone view on
// these words, never on a selector (R53).
export const PHONE_MENU_LABEL = 'Menu';

const usePhoneStyles = makeStyles(theme => ({
  // A fixed strip at the top of every page: the menu button and the wordmark. 56px is
  // Material's own phone toolbar height, so page content starts under it, not behind it.
  bar: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    height: 56,
    zIndex: theme.zIndex.appBar,
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1),
    paddingLeft: theme.spacing(1),
    paddingRight: theme.spacing(1),
    background: theme.palette.background.paper,
    borderBottom: `1px solid ${theme.palette.divider}`,
  },
  grow: { flex: 1, minWidth: 0 },
  spacer: { height: 56 },
  brand: { display: 'flex', alignItems: 'center', gap: theme.spacing(1) },
  word: { fontWeight: 600, color: theme.palette.text.primary },
  drawer: { width: 280, maxWidth: '85vw' },
  head: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: theme.spacing(1, 1, 1, 2),
    borderBottom: `1px solid ${theme.palette.divider}`,
  },
  item: { minHeight: 48 },
  section: {
    padding: theme.spacing(2, 2, 0.5, 2),
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    color: theme.palette.text.secondary,
  },
}));

// Cmd/Ctrl+K opens Backstage's own search modal from any page.
const FindShortcut = () => {
  const { toggleModal } = useSearchModal();
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== 'k') {
        return;
      }
      event.preventDefault();
      toggleModal();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [toggleModal]);
  return null;
};

// The phone nav: a menu button, and the ten doors in a drawer that slides in from the left.
const PhoneNav = () => {
  const classes = usePhoneStyles();
  const [open, setOpen] = useState(false);
  // The Find button top right only toggles state; something has to draw the modal. On the
  // desktop that is SidebarSearchModal, which is part of the sidebar and so is not rendered
  // on a phone -- so the button toggled a modal nobody drew and searching did nothing
  // (founder 2026-09-04, "top right search not working"). The phone draws its own.
  const { state: searchState, toggleModal } = useSearchModal();
  // The wordmark in the bar is the estate's name from app.title (LAW 46), in the page's own
  // ink: LogoFull is drawn for the navy sidebar and would vanish on the phone bar.
  const title = useApi(configApiRef).getOptionalString('app.title') ?? 'Estate';
  return (
    <div data-testid="estate-nav-phone">
      <div className={classes.bar}>
        <IconButton
          aria-label={`Open ${PHONE_MENU_LABEL.toLowerCase()}`}
          onClick={() => setOpen(true)}
          edge="start"
        >
          <MenuIcon />
        </IconButton>
        <Link to="/" underline="none" aria-label="Home" className={classes.brand}>
          <LogoIcon />
          <Typography variant="subtitle1" className={classes.word}>
            {title}
          </Typography>
        </Link>
        <span className={classes.grow} />
        <IconButton aria-label="Find" onClick={() => toggleModal()}>
          <SearchIcon />
        </IconButton>
      </div>
      <SearchModal {...searchState} toggleModal={toggleModal} />
      <div className={classes.spacer} />
      <Drawer
        anchor="left"
        open={open}
        onClose={() => setOpen(false)}
        classes={{ paper: classes.drawer }}
      >
        <div className={classes.head}>
          <Typography variant="h6">{PHONE_MENU_LABEL}</Typography>
          <IconButton aria-label="Close menu" onClick={() => setOpen(false)}>
            <CloseIcon />
          </IconButton>
        </div>
        <List component="nav" aria-label={PHONE_MENU_LABEL}>
          {NAV.map(({ title: label, to, icon: Glyph }, i) => (
            <Fragment key={to}>
              {i === 0 && (
                <Typography className={classes.section}>Start here</Typography>
              )}
              {i === BUYER_COUNT && (
                <Typography className={classes.section}>More</Typography>
              )}
              <ListItem
                button
                component={Link}
                to={to}
                className={classes.item}
                onClick={() => setOpen(false)}
              >
                <ListItemIcon>
                  <Glyph />
                </ListItemIcon>
                <ListItemText primary={label} />
              </ListItem>
            </Fragment>
          ))}
        </List>
      </Drawer>
    </div>
  );
};

// The desktop nav: Backstage's own Sidebar. One click per door; buyer doors above the line.
const DesktopNav = () => (
  <div data-testid="estate-nav">
    <Sidebar>
      <SidebarLogo />
      <SidebarSearchModal />
      <SidebarDivider />
      {NAV.slice(0, BUYER_COUNT).map(({ title, to, icon: Icon }) => (
        <SidebarItem key={to} icon={Icon} to={to} text={title} />
      ))}
      <SidebarDivider />
      {NAV.slice(BUYER_COUNT).map(({ title, to, icon: Icon }) => (
        <SidebarItem key={to} icon={Icon} to={to} text={title} />
      ))}
      <SidebarSpace />
    </Sidebar>
  </div>
);

export const EstateNav = NavContentBlueprint.make({
  params: {
    // A named, capitalised function: the hooks below are legal only inside a component, and
    // the lint rule recognises a component by its name, not by the slot it is handed to.
    component: function EstateNavContent({ navItems }) {
      // Every plugin's nav item is taken so nothing renders twice; the ten above are the nav.
      navItems.withComponent(() => null);
      const theme = useTheme();
      // Backstage's own breakpoint for its bottom bar is 'xs' (under 600px); the phone menu
      // takes over at exactly the width the bottom bar would have appeared.
      const phone = useMediaQuery(theme.breakpoints.down('xs'));
      return (
        <SearchModalProvider>
          <FindShortcut />
          {phone ? <PhoneNav /> : <DesktopNav />}
        </SearchModalProvider>
      );
    },
  },
});
