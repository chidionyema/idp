# Adding a tool to the Tools page

A tool is one entry in `backstage/founder/catalog-info.yaml` with `spec.type: founder-surface`. The page reads the catalogue; nothing on the page itself changes when a tool is added.

## Steps

1. Copy an existing entry in `backstage/founder/catalog-info.yaml`. Give it a plain title, one sentence of description a person can act on, and the link that opens it. Write the host as `https://<name>.${ESTATE_ZONE}`; the zone is substituted when the file is rendered.
2. Set `estate/group` to one of the seven headings: See what is running, Fix something, AI and models, Our products, Money, Build and ship, Under the hood. An entry with no group lands under the heading Other, which is a defect the page makes visible.
3. If the tool is one a person uses most days, add `estate/tier: "daily"`. It then sits first in its group with the word Everyday.
4. If the tool asks for its own credential after the estate login, say so in the description in those words. The gate refuses an entry that hides a second login.
5. Run the gates before pushing:

       python3 -m pytest -o addopts= tests/test_incident_crew684_the_tools_page_is_every_door_on_one_page.py tests/test_incident_crew718_the_second_login_is_named_not_silently_passed.py -q

6. Push. After merge, Flux renders the file into the portal; open **More**, then **Tools**, and find the tile under its heading.

Do not add a tile by editing the page. The page has no list of its own; the catalogue is the list.
