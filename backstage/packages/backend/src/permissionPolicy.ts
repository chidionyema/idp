// Real RBAC for the scaffolder: templates tagged `founder-action` (crew#180) are for
// group:default/platform only; every other template -- including ordinary, customer-facing
// ones such as templates/customer-onboarding/template.yaml, which share the *same*
// `owner: group:default/platform` as the founder-action ones -- stays open to anyone the
// front door already signed in. Ownership does not discriminate here (verified: every
// template.yaml under templates/ carries that owner), so this gates on the `founder-action`
// tag instead, confirmed to appear only on templates/founder-actions/**/template.yaml plus
// templates/agent-foundry-space/template.yaml.
//
// Why this is a catalog-entity policy, not a scaffolder-template one:
// `@backstage/plugin-scaffolder-common`'s templateParameterReadPermission and
// templateStepReadPermission are resourced with resourceType `scaffolder-template`
// (plugins/scaffolder-common/src/permissions.ts), but scaffolder-backend's own enforcement
// (plugins/scaffolder-backend/src/service/router.ts:1199-1248, authorizeTemplate) asks the
// policy for a decision *before* it knows which template is being read (no entityRef is
// passed into permissions.authorizeConditional there), then applies the decision itself,
// per parameter/step, using ONLY the built-in HAS_TAG rule
// (plugins/scaffolder-backend/src/service/rules.ts:42-53) -- which reads an inline
// `backstage:permissions.tags` annotation on the *step*, not `metadata.tags` on the
// Template entity. There is no per-template hook here at all: gating those two permissions
// cannot see which template is in play, so they cannot express "block this whole template by
// its own tag" without hand-editing every step of all ~44 founder-action templates (out of
// scope for this change, and a much larger blast radius). taskCreatePermission
// (plugins/scaffolder-common/src/permissions.ts:118-123) has no resourceType at all and is
// checked with zero entity context (router.ts:557-563) -- same dead end.
//
// Scaffolder templates ARE catalog entities (kind: Template) fetched by entityRef, so the
// permission that genuinely carries the template being read is catalogEntityReadPermission
// (resourceType `catalog-entity`, @backstage/plugin-catalog-common/alpha). Denying that for a
// founder-action Template makes findTemplate() 404 it and the scaffolder picker never lists
// it -- which is what actually keeps a non-platform user off the create button. The
// conditional decision uses catalog-backend's own built-in rule set
// (plugins/catalog-backend/src/permissions/rules -- hasAnnotation, hasLabel, hasMetadata,
// hasSpec, isEntityKind, isEntityOwner; there is no dedicated hasTag rule, but hasMetadata
// with key: 'tags' matches an array entry via the same entity-search index hasLabel/hasTag
// would use). The rule is scoped to `isEntityKind(['Template'])` so it never touches any
// other catalog entity (Component, API, System, Group, User, ...), and every non-catalog
// permission (search, techdocs, notifications, kubernetes, the rest of the catalog) is left
// on the default ALLOW below, untouched.
import { createBackendModule } from '@backstage/backend-plugin-api';
import { policyExtensionPoint } from '@backstage/plugin-permission-node/alpha';
import type {
  PermissionPolicy,
  PolicyQuery,
  PolicyQueryUser,
} from '@backstage/plugin-permission-node';
import {
  AuthorizeResult,
  isResourcePermission,
  type PolicyDecision,
} from '@backstage/plugin-permission-common';
import {
  RESOURCE_TYPE_CATALOG_ENTITY,
} from '@backstage/plugin-catalog-common/alpha';
import {
  catalogConditions,
  createCatalogConditionalDecision,
} from '@backstage/plugin-catalog-backend/alpha';

export const FOUNDER_ACTION_TAG = 'founder-action';
export const PLATFORM_GROUP_REF = 'group:default/platform';

// Exported so the test can exercise the decision logic directly, without standing up the
// whole permission-backend HTTP surface.
export class ScaffolderTemplateAccessPolicy implements PermissionPolicy {
  async handle(
    request: PolicyQuery,
    user?: PolicyQueryUser,
  ): Promise<PolicyDecision> {
    if (!isResourcePermission(request.permission, RESOURCE_TYPE_CATALOG_ENTITY)) {
      return { result: AuthorizeResult.ALLOW };
    }

    // group:default/platform members bypass the tag gate entirely -- no conditional
    // round-trip needed, and this also covers every catalog entity that isn't a template.
    if (user?.info.ownershipEntityRefs.includes(PLATFORM_GROUP_REF)) {
      return { result: AuthorizeResult.ALLOW };
    }

    // Everyone else: ALLOW unless the entity is a Template carrying the founder-action tag.
    return createCatalogConditionalDecision(request.permission, {
      not: {
        allOf: [
          catalogConditions.isEntityKind({ kinds: ['Template'] }),
          catalogConditions.hasMetadata({
            key: 'tags',
            value: FOUNDER_ACTION_TAG,
          }),
        ],
      },
    });
  }
}

export default createBackendModule({
  pluginId: 'permission',
  moduleId: 'scaffolder-template-access-policy',
  register(reg) {
    reg.registerInit({
      deps: { policy: policyExtensionPoint },
      async init({ policy }) {
        policy.setPolicy(new ScaffolderTemplateAccessPolicy());
      },
    });
  },
});
