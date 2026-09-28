// Real RBAC for the scaffolder, proved by exercising the policy's handle() directly against
// the three fixtures crew#180 calls out: a founder-action template denied to a non-platform
// caller, allowed to a platform member, and an ordinary customer-facing template (which
// shares the exact same `owner: group:default/platform` as every founder-action template --
// ownership alone cannot be the gate) left open to anyone. See src/permissionPolicy.ts for why
// this is a catalog-entity conditional decision rather than a scaffolder-template one.
import {
  AuthorizeResult,
  type ConditionalPolicyDecision,
  type PolicyDecision,
} from '@backstage/plugin-permission-common';
import { catalogEntityReadPermission } from '@backstage/plugin-catalog-common/alpha';

import {
  FOUNDER_ACTION_TAG,
  PLATFORM_GROUP_REF,
  ScaffolderTemplateAccessPolicy,
} from './permissionPolicy';

// Minimal stand-in for the entities the catalog-backend rule evaluator would apply the
// resulting conditional decision to; the shape only needs what isEntityKind/hasMetadata read.
function templateEntity(name: string, tags: string[]) {
  return {
    apiVersion: 'scaffolder.backstage.io/v1beta3',
    kind: 'Template',
    metadata: { name, namespace: 'default', tags },
    spec: { owner: 'group:default/platform', type: 'service' },
  };
}

// Re-derives the same allow/deny bit a real request would get, by applying the conditional
// decision's rule tree the way catalog-backend's own condition applier does: hasMetadata
// checks metadata[key] contains value; isEntityKind checks kind; not/allOf combine as usual.
function evaluateDecision(decision: PolicyDecision, entity: ReturnType<typeof templateEntity>): boolean {
  if (decision.result === AuthorizeResult.ALLOW) return true;
  if (decision.result === AuthorizeResult.DENY) return false;
  const conditional = decision as ConditionalPolicyDecision;

  const evalCriteria = (criteria: any): boolean => {
    if ('not' in criteria) return !evalCriteria(criteria.not);
    if ('allOf' in criteria) return criteria.allOf.every(evalCriteria);
    if ('anyOf' in criteria) return criteria.anyOf.some(evalCriteria);
    // a leaf PermissionCondition: { rule, resourceType, params }
    if (criteria.rule === 'IS_ENTITY_KIND') {
      return criteria.params.kinds.some(
        (k: string) => k.toLowerCase() === entity.kind.toLowerCase(),
      );
    }
    if (criteria.rule === 'HAS_METADATA') {
      const { key, value } = criteria.params;
      const field = (entity.metadata as Record<string, unknown>)[key];
      if (Array.isArray(field)) return field.includes(value);
      return field === value;
    }
    throw new Error(`unhandled rule in test evaluator: ${criteria.rule}`);
  };

  return evalCriteria(conditional.conditions);
}

function userWithGroups(groups: string[]) {
  return {
    credentials: { principal: {} } as any,
    info: {
      userEntityRef: 'user:default/someone',
      ownershipEntityRefs: groups,
    },
  };
}

describe('ScaffolderTemplateAccessPolicy', () => {
  const policy = new ScaffolderTemplateAccessPolicy();
  const founderTemplate = templateEntity('run-vault-seed', [FOUNDER_ACTION_TAG, 'estate']);
  const customerTemplate = templateEntity('onboard-messaging-customer', [
    'onboarding',
    'messaging',
    'customer',
  ]);

  it('(a) denies a non-platform-group identity reading a founder-action template', async () => {
    const decision = await policy.handle(
      { permission: catalogEntityReadPermission },
      userWithGroups(['user:default/someone', 'group:default/engineering']),
    );
    expect(evaluateDecision(decision, founderTemplate)).toBe(false);
  });

  it('(b) allows a group:default/platform member reading the same founder-action template', async () => {
    const decision = await policy.handle(
      { permission: catalogEntityReadPermission },
      userWithGroups(['user:default/someone', PLATFORM_GROUP_REF]),
    );
    expect(evaluateDecision(decision, founderTemplate)).toBe(true);
  });

  it('(c) allows any identity reading a customer-facing template with no founder-action tag', async () => {
    const nonPlatform = await policy.handle(
      { permission: catalogEntityReadPermission },
      userWithGroups(['user:default/someone', 'group:default/engineering']),
    );
    expect(evaluateDecision(nonPlatform, customerTemplate)).toBe(true);

    const platform = await policy.handle(
      { permission: catalogEntityReadPermission },
      userWithGroups(['user:default/someone', PLATFORM_GROUP_REF]),
    );
    expect(evaluateDecision(platform, customerTemplate)).toBe(true);
  });

  it('defaults every non-catalog-entity permission to ALLOW (search, techdocs, notifications, kubernetes, ...)', async () => {
    const decision = await policy.handle(
      { permission: { name: 'some.other.permission', attributes: {} } as any },
      userWithGroups(['user:default/someone']),
    );
    expect(decision).toEqual({ result: AuthorizeResult.ALLOW });
  });

  it('denies with no user context at all (unauthenticated) unless the template lacks the tag', async () => {
    const decision = await policy.handle({ permission: catalogEntityReadPermission }, undefined);
    expect(evaluateDecision(decision, founderTemplate)).toBe(false);
    expect(evaluateDecision(decision, customerTemplate)).toBe(true);
  });
});
