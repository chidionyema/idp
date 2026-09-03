# The Tools page

The Tools page is the one place that lists every door in the estate: the portal's own pages, the dashboards, the model router, the traces, the products, the stores and the platform plumbing. Each opens on the estate login, so a person signs in once and every tile works. It sits under **More** in the portal menu.

The founder said the earlier version was a maze: one wall of tiles with no order and no words that said what anything was. The page now reads top to bottom like a page written for a person.

## What you see

- **One sentence at the top** says how many tools there are, how many are everyday tools, and how many are plumbing folded out of the way.
- **Seven groups, in the order a person arrives with a question:** See what is running, Fix something, AI and models, Our products, Money, Build and ship, Under the hood.
- **Everyday tools first** inside each group, marked with the word Everyday.
- **Under the hood is folded closed.** It holds the platform plumbing; open it when you need it.
- **Every tile** has a title, one plain sentence saying what the tool is for, and one Open button. If a tool asks for a second credential after the estate login, its sentence says so.

## See it work

Open the portal, choose **More**, then **Tools**. Read the first sentence, then the group headings. Press **Open** on any tile in "See what is running"; it opens on your estate login with no second sign-in.

Read the same list without the portal:

    curl -s https://catalogue.<your estate zone>/api/catalog/entities/by-query?filter=spec.type=founder-surface

## Where the pieces live

- The list, the groups and the sentences: `backstage/founder/catalog-info.yaml`. Every entry carries `estate/group` (which heading) and, for the everyday ones, `estate/tier: daily`.
- The grouping and ordering rules: `backstage/packages/app/src/modules/home/toolGroups.ts`.
- The page: `backstage/packages/app/src/modules/home/Tools.tsx`, route `/tools`.
- The gates: `tests/test_incident_crew684_the_tools_page_is_every_door_on_one_page.py` (every door is on the page, none hard-coded) and `tests/test_incident_crew718_the_second_login_is_named_not_silently_passed.py` (a second credential is named, never hidden).
