# Why the catalogue still looks old, and the one look that is allowed

Research note, 2026-09-03. Every claim has a first-party source. This is the answer to
"is it looking good, can it look spectacularly better."

## Verdict

It is not looking good. The last change (`b1b56e09`, one-click nav and a fixed home) made
the **clicks** current. The **look** is still Material UI v4 around a 2020 catalog: filled
Google icons, `makeStyles`, hairline cards. Backstage already shipped the design system
that looks current. This estate imports its CSS and never uses a single component from it.

Spectacular is not a second portal and not more hover tweaks. It is Backstage UI (BUI)
for anything we draw, and the existing Unified Theme only for plugins that are still MUI.

## Findings

1. **Backstage runs two UI systems at once.** The old one is Material UI, themed in
   JavaScript with `UnifiedThemeProvider`. The new one is Backstage UI: CSS variables
   and tokens, documented at ui.backstage.io. Both are supported; most plugins are
   still MUI; new work is BUI. Spotify's own instruction: if the class name starts
   with `bui`, style it with BUI CSS, not MUI.
   https://backstage.io/docs/conf/user-interface/

2. **You keep both themes during the transition.** Custom themes override the defaults.
   You still export light and dark. MUI stays on `UnifiedThemeProvider`. BUI does not
   use a React provider; you add a CSS file and import it next to the app. The `body`
   gets `data-theme-mode="light"` or `"dark"` from the theme variant.
   https://backstage.io/docs/conf/user-interface/

3. **BUI is the official "this looks like Backstage in 2026" surface.** It is React,
   TypeScript, and vanilla CSS, hosted in the Backstage monorepo, designed by Spotify's
   Backstage team. Layout is `Box`, `Flex`, `Grid`, and `Card`. Nested surfaces raise
   themselves on a neutral scale from 0 to 4 so hierarchy is automatic. Adaptive
   `Card` / `Button` / `Text` restyle to the surface they sit on.
   https://ui.backstage.io/

4. **The spectacular look is a short list of CSS variables, not a new brand file.**
   Official starting set: `--bui-bg-app`, `--bui-bg-neutral-1`, `--bui-bg-neutral-2`,
   `--bui-bg-solid`, `--bui-fg-solid`, `--bui-fg-primary`, `--bui-fg-secondary`,
   status foregrounds, `--bui-border-1`, `--bui-border-2`, `--bui-font-regular`.
   Light and dark are `[data-theme-mode='light']` and `[data-theme-mode='dark']`.
   https://backstage.io/docs/conf/user-interface/ · https://ui.backstage.io/tokens

5. **Spacing and radius are one knob each.** `--bui-space` defaults to `0.25rem` and
   drives every gap. Radius runs `--bui-radius-1` (0.125rem) through `--bui-radius-6`
   (1.25rem) plus `--bui-radius-full`. A current look is a larger radius and a
   slightly looser space, set once.
   https://ui.backstage.io/tokens

6. **Icons are Remix, not Material.** BUI removed its own `Icon` because it broke
   tree-shaking. The documented replacement is `@remixicon/react` (keep the package
   below 4.9.0; 4.9.0 changed licence). This estate still imports `@material-ui/icons`
   in `EstateNav.tsx`. That is why the rail looks like 2018 Google.
   https://backstage.io/docs/releases/v1.44.0/ · https://ui.backstage.io/changelog

7. **There is an official bridge from our MUI theme to BUI CSS.**
   `@backstage/plugin-mui-to-bui` adds `/mui-to-bui`: it reads the installed themes,
   emits BUI variables, live-previews, copy or download. New frontend system: install
   the plugin, no extra route. We do not have this package.
   https://backstage.io/api/stable/modules/_backstage_plugin_mui-to-bui.html ·
   https://backstage.io/docs/releases/v1.44.0/

8. **v1.44 made BUI CSS mandatory.** `UnifiedThemeProvider` no longer injects
   CssBaseline. An app that forgets `@backstage/ui/css/styles.css` looks broken.
   This estate already imports that file in `packages/app/src/index.tsx`. The CSS
   is loaded. Zero files import a component from `@backstage/ui` (`rg` over
   `packages/app/src`, 2026-09-03).
   https://backstage.io/docs/releases/v1.44.0/ ·
   `backstage/packages/app/src/index.tsx` · `@backstage/ui` 0.17.1 in
   `packages/app/package.json`

9. **What we actually paint today.** `modules/theme` is `createUnifiedTheme` plus
   MUI `styleOverrides` (the theme change of 2026-08-29): near-black canvas `#0b0c0e`,
   hairline borders, system fonts, no webfont. Home is `Page` / `Header` /
   `Content` from `@backstage/core-components` wrapping plugin widgets
   (`homeLayout.tsx` on `feat/portal-modern-home`). Nav is `@material-ui/core`
   Drawer + `@material-ui/icons`. That is the old system, tightened. It cannot
   look like BUI no matter how many card hovers we add.
   `backstage/packages/app/src/modules/theme/tokens.ts` ·
   `backstage/packages/app/src/modules/home/homeLayout.tsx` ·
   `backstage/packages/app/src/modules/nav/EstateNav.tsx`

10. **Custom components, if any, must sit on BUI tokens or BUI primitives.**
    Spotify: prefer BUI components; if you must draw your own, use
    `var(--bui-bg-solid)` / `var(--bui-fg-solid)` and React Aria for behaviour.
    Do not invent a third card.
    https://ui.backstage.io/

11. **A second CSS framework is the stitch.** Tailwind, Chakra, shadcn, or a
    hand-drawn "spectacular" marketing shell would be a second design system
    next to MUI and BUI. The docs already call two systems a problem they are
    retiring. A third is the thing this estate deletes.
    https://backstage.io/docs/conf/user-interface/

## The one path

1. Add `packages/app/src/styles.css` that sets `[data-theme-mode='dark']` and
   `light` `--bui-*` to the same numbers as `modules/theme/tokens.ts` (canvas
   `#0b0c0e`, accent `#4c8dff`, surfaces `#121316` / `#17191d`). Import it from
   `index.tsx` after `@backstage/ui/css/styles.css`.
2. Rebuild **Today** (`homeLayout.tsx`) with BUI `Box`, `Flex`, `Grid`, `Card`,
   `Text`, `Button` / `ButtonLink`. Leave catalog tables and the vendor sidebar
   on Unified Theme until those plugins ship `bui` classes.
3. Swap nav icons to `@remixicon/react` below 4.9.0. Keep the ten doors and
   the phone Drawer.
4. Install `@backstage/plugin-mui-to-bui` and open `/mui-to-bui` once, so the
   CSS file is generated from the live MUI theme instead of typed by hand.
   Pin the result; do not leave the themer as a public nav item.

Risk: catalog and TechDocs stay MUI until those plugins move. The first screen
and the chrome we own will look like 2026 Backstage. Everything else will catch
up as plugins adopt `bui` classes.

## What we will not do

- Another homepage grid or another custom "god view" drawn in `makeStyles`.
- A webfont download. System faces stay; `--bui-font-regular` can name the same
  stack already in `tokens.ts`.
- Tailwind, Chakra, or a marketing landing in front of the catalog.

## What is on the shelf (read 2026-09-03)

Source of truth for **this estate**: the export list of `@backstage/ui` **0.17.1** in
`backstage/node_modules/@backstage/ui/dist/index.d.ts`. Docs for each page:
`https://ui.backstage.io/components/<name>`.

### Layout (the bones)

`Box`, `Flex`, `Grid`, `Container`, `Card` + `CardHeader` / `CardBody` / `CardFooter`,
`FullPage`. Nested `Box`/`Card` step the neutral scale so a card on a card is darker
without picking colours. https://ui.backstage.io/

### Type and chrome

`Text`, `Header` (title, tags, description, metadata, tabs, `customActions`; can stick),
`HeaderPage`, `PluginHeader`, `HeaderMetadataStatus`, `HeaderMetadataUsers`,
`Link`, `Button`, `ButtonLink`, `ButtonIcon`.
https://ui.backstage.io/components/header · https://ui.backstage.io/components/button

### Find and type-in

`SearchField` (collapsible, icon, sizes), `SearchAutocomplete`, `TextField`,
`TextAreaField`, `PasswordField`, `NumberField`, `Combobox`, `Select`, `DatePicker`,
`DateRangePicker`, `Slider`. Search is its own component, not a TextField with
`type="search"`. https://ui.backstage.io/components/search-field ·
https://ui.backstage.io/components/text-field

### Choose and switch

`Checkbox`, `CheckboxGroup`, `Radio`, `RadioGroup`, `Switch`, `ToggleButton`,
`ToggleButtonGroup`, `Menu` / `MenuTrigger` / `MenuItem` / `MenuSection` /
`MenuAutocomplete`, `Tabs` / `Tab` / `TabList` / `TabPanel`.
https://ui.backstage.io/components/menu · https://ui.backstage.io/components/checkbox

### Lists and tables

`List` / `ListRow`, `Table` + `useTable` (sort, page, select, stale, empty state),
`TableRoot` if you must compose, `Cell` / `CellText` / `CellProfile`, `Tag` / `TagGroup`.
https://ui.backstage.io/components/table

### Feedback

`Alert`, `Badge`, `Avatar`, `Skeleton`, `Tooltip` / `TooltipTrigger`, `Dialog` /
`DialogTrigger` / `DialogHeader` / `DialogBody` / `DialogFooter`, `Popover`,
`Accordion` / `AccordionGroup`.
https://ui.backstage.io/components/dialog · https://ui.backstage.io/components/avatar

### What Today should actually import

Not the whole list. For the first screen:

| Job | Component | Why |
| --- | --- | --- |
| Page shell | `Header` + `customActions` | Official page title, Find/Create as actions. Replaces MUI `Header`. |
| Search | `SearchField` | Official search, not a text box. |
| Door tiles | `Card` + `CardHeader` + `href` | Clickable card with overlay; nested buttons still work. |
| Words | `Text` | Adaptive type on whatever surface it sits on. |
| Layout | `Flex` + `Grid` | Tokens for gap. Replaces `makeStyles` grids. |
| Status | `HeaderMetadataStatus` / `Badge` | Live / failing without a home-grown pill. |
| Menu on a card | `MenuTrigger` + `ButtonIcon` | The header docs show this exact pattern. |

Icons on those buttons: `@remixicon/react` (below 4.9.0), as BUI removed its own Icon.
https://ui.backstage.io/changelog · https://backstage.io/docs/releases/v1.44.0/

New frontend already wraps `BUIProvider`. Link, ButtonLink, Tabs, Menu, TagGroup and
Table need that provider or they do a full page load.
https://ui.backstage.io/get-started/installation ·
https://ui.backstage.io/components/table

## Libraries (read 2026-09-03)

The internet has many kits. Backstage names three. This estate already has two of them.

### Already in `packages/app`

| Package | Job | Use it? |
| --- | --- | --- |
| `@backstage/ui` 0.17.1 | The 2026 design system (BUI). CSS is imported. No component is. | Yes. Today and any new screen. |
| `@backstage/core-components` | Old page chrome on Material UI. Catalog, sidebar, TechDocs still emit this. | Keep until those plugins ship `bui` classes. Do not write new screens in it. |
| `@backstage/theme` | Unified Theme that paints MUI v4 and BUI from one token set. | Yes. Map our colours here, not in a third theme. |
| `@material-ui/core` + `@material-ui/icons` | Material UI v4. What Today actually imports. | Leave for plugin pages. Do not add more `makeStyles`. |
| `@backstage/plugin-home` | Home widgets (starred, recently visited). | Keep the data. Stop using its drag grid. |

https://ui.backstage.io/get-started/installation ·
`backstage/packages/app/package.json`

### Official, not yet installed

| Package | Job | Pin |
| --- | --- | --- |
| `@remixicon/react` | Official icons. BUI dropped its own Icon. `IconElement` prefers Remix. Material icons are deprecated. | **Below 4.9.0.** Licence changes at 4.9.0. https://ui.backstage.io/changelog · https://backstage.io/docs/releases/v1.51.0/ · https://backstage.io/api/stable/types/_backstage_frontend-plugin-api.index.IconElement.html |
| `react-aria-components` | Headless behaviour BUI is built on. Official for a custom control that BUI does not have. Types are also re-exported from `@backstage/ui` so you often need no extra dep. | Whatever BUI already resolved. https://ui.backstage.io/ |
| `@backstage/plugin-mui-to-bui` | Turns the live MUI theme into `--bui-*` CSS. A converter, not a look. | Optional, at `/mui-to-bui` only. Do not put it in the nav. |

Codemods (`backstage/codemods`) rewrite MUI to BUI. They are a one-shot tool, not a library we ship.

### Out there, and not for this portal

These exist. Teams stitch them. A buyer’s engineer would see two (or three) design systems on one page.

- **Tailwind / shadcn / Radix** — utility CSS plus a second kit. BUI is already vanilla CSS and tokens.
- **Chakra, Ant Design, Mantine, Fluent, Carbon** — full kits with their own tokens, resets, and providers. Clash with MUI v4 and BUI on the same tree.
- **`@mui/material` v5** — even Material’s next major is a third look next to v4 and BUI. Core Backstage is still on v4 until the migration tracker hits zero. https://github.com/backstage/backstage/issues/31467
- **A house design system** (Cdiscount / PeakSYS path: restyle by forking Catalog). Upgrade tax forever. https://medium.com/peaksys-engineering/two-years-of-backstage-behind-the-scenes-of-our-developer-portal-a45ddf6f0e73

Spotify’s own words on custom work: use BUI components first; if you must invent a control, use React Aria plus `--bui-*` variables. Do not bring another kit. https://ui.backstage.io/

### One add

`yarn add '@remixicon/react@<4.9.0'` in `packages/app`. That is the only new library.

## Sources, in the order they were read

- https://backstage.io/docs/conf/user-interface/
- https://ui.backstage.io/
- https://ui.backstage.io/tokens
- https://ui.backstage.io/get-started/installation
- https://ui.backstage.io/changelog
- https://backstage.io/docs/releases/v1.44.0/
- https://backstage.io/api/stable/modules/_backstage_plugin_mui-to-bui.html
- `backstage/packages/app/package.json` (`@backstage/ui` ^0.17.1)
- `backstage/packages/app/src/index.tsx`
- `backstage/packages/app/src/modules/theme/tokens.ts`
- `backstage/packages/app/src/modules/home/homeLayout.tsx` (branch `feat/portal-modern-home`)
- `backstage/node_modules/@backstage/ui/dist/index.d.ts` (0.17.1 export list, this machine)
- https://ui.backstage.io/components/header
- https://ui.backstage.io/components/button
- https://ui.backstage.io/components/card
- https://ui.backstage.io/components/search-field
- https://ui.backstage.io/components/text-field
- https://ui.backstage.io/components/menu
- https://ui.backstage.io/components/table
- https://ui.backstage.io/components/dialog
- https://ui.backstage.io/components/accordion
- https://ui.backstage.io/components/avatar
- https://ui.backstage.io/components/checkbox
- https://backstage.io/docs/releases/v1.51.0/
- https://backstage.io/api/stable/types/_backstage_frontend-plugin-api.index.IconElement.html
- https://github.com/backstage/backstage/issues/31467
- https://github.com/backstage/codemods
- https://medium.com/peaksys-engineering/two-years-of-backstage-behind-the-scenes-of-our-developer-portal-a45ddf6f0e73
