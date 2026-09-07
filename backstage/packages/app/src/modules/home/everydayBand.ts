// Which tools the front page puts in front of the founder, with no React in it.
//
// Founder, 2026-09-07: "why should i be looking for essential tools at all", and, on hunting
// for the estate Mac's screen: "the fact i'm looking for it at all is a problem ... the portal
// is shit". He was right. Reaching his own machine was a tile on a second page, inside a group
// called "Fix something", among fifty-two others. The front page listed the portal's own pages
// and nothing he actually opens.
//
// So the front page now carries the everyday band: every founder surface the catalogue marks
// `estate/tier: daily`, in one row, each with its Open button. Nothing here names a tool — the
// catalogue is the list (LAW 46), the same source the Tools page reads. A tool joins the band by
// gaining the annotation in backstage/founder/catalog-info.yaml and nothing else.
import { Entity } from '@backstage/catalog-model';
import { byTitle } from './estate';
import { isDaily, openLink } from './toolGroups';

/** The band's heading and the one line under it. */
export const EVERYDAY_TITLE = 'Your everyday tools';
export const EVERYDAY_BLURB =
  'The doors you open most days, on your estate login. Everything else is on Tools.';
/** Shown while the catalogue has not answered yet, so the band never flashes empty. */
export const EVERYDAY_LOADING = 'Reading the catalogue.';
/** Shown when the catalogue answered but marks nothing as everyday. */
export const EVERYDAY_NONE =
  'No tool is marked as an everyday one yet; every tool is on the Tools page.';

/**
 * The band's tools: every daily surface that has a link to open, in title order.
 *
 * A daily tool with no published link is left out deliberately. On the Tools page a linkless
 * tile still says something useful ("No link is published for this tool yet"); on the front
 * page it would be a button that does nothing, which is the defect this band exists to end.
 */
export const everydayTools = (doors: Entity[]): Entity[] =>
  doors
    .filter(e => isDaily(e) && openLink(e) !== undefined)
    .sort(byTitle);
