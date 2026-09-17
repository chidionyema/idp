import { Request, Response, NextFunction } from 'express';
import Ajv from 'ajv';
import { Logger } from 'winston';

/**
 * Layer 2 Prevention: API Response Schema Validation (Runtime)
 * Validates every API response against its declared schema before sending to client.
 * Catches data corruption, invalid URLs, missing fields that slip through pre-commit.
 *
 * Triggers incident on violation:
 *   - PagerDuty alert (page on-call)
 *   - Datadog trace + event
 *   - Slack #critical-alerts
 *   - Circuit breaker trips (endpoint returns 503)
 */

interface SchemaValidatorOptions {
  logger: Logger;
  alertFn?: (incident: IncidentAlert) => Promise<void>;
}

interface IncidentAlert {
  severity: 'critical' | 'high' | 'medium';
  type: string;
  message: string;
  path: string;
  timestamp: string;
  telemetryId: string;
  data?: unknown;
}

const ajv = new Ajv({ strict: true });

// Schema for catalog entity links (the field that caused layer-dagster failure)
const catalogLinkSchema = {
  type: 'object',
  properties: {
    url: {
      type: 'string',
      format: 'uri', // Must be valid http/https URL
    },
    title: {
      type: 'string',
    },
  },
  required: ['url', 'title'],
  additionalProperties: false,
};

// Schema for catalog entities
const catalogEntitySchema = {
  type: 'object',
  properties: {
    apiVersion: { type: 'string' },
    kind: { type: 'string' },
    metadata: {
      type: 'object',
      properties: {
        name: { type: 'string' },
        namespace: { type: 'string' },
      },
      required: ['name'],
    },
    spec: {
      type: 'object',
      properties: {
        owner: { type: 'string' },
        system: { type: 'string' },
        links: {
          type: 'array',
          items: catalogLinkSchema,
        },
      },
    },
  },
  required: ['apiVersion', 'kind', 'metadata'],
};

// Endpoint-specific schemas
const ENDPOINT_SCHEMAS: Record<string, any> = {
  '/api/catalog/entities': {
    type: 'array',
    items: catalogEntitySchema,
  },
};

export function createSchemaValidator(options: SchemaValidatorOptions) {
  const { logger, alertFn } = options;
  const telemetryId = () => `sv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  return (req: Request, res: Response, next: NextFunction) => {
    const originalSend = res.send.bind(res);
    const originalJson = res.json.bind(res);

    // Intercept send() method
    res.send = function(data: any) {
      const schema = ENDPOINT_SCHEMAS[req.path];

      if (schema) {
        try {
          const validate = ajv.compile(schema);
          const valid = validate(data);

          if (!valid) {
            const id = telemetryId();
            const incident: IncidentAlert = {
              severity: 'critical',
              type: 'SCHEMA_VIOLATION',
              message: `API response validation failed: ${ajv.errorsText(validate.errors)}`,
              path: req.path,
              timestamp: new Date().toISOString(),
              telemetryId: id,
              data: data,
            };

            logger.error('SCHEMA_VIOLATION', {
              telemetryId: id,
              path: req.path,
              errors: validate.errors,
              dataSnapshot: JSON.stringify(data).substring(0, 500),
            });

            // Alert external systems
            if (alertFn) {
              alertFn(incident).catch((err) => {
                logger.error('Failed to send alert', { err, incidentId: id });
              });
            }

            // Return error response (circuit breaker: 503 Service Unavailable)
            return res.status(503).json({
              error: 'Data validation failed - service unavailable',
              telemetryId: id,
              message: 'An internal data integrity issue was detected. This incident has been reported.',
            });
          }
        } catch (err) {
          logger.error('Schema validation error', { path: req.path, err });
        }
      }

      return originalSend(data);
    };

    // Intercept json() method
    res.json = function(data: any) {
      const schema = ENDPOINT_SCHEMAS[req.path];

      if (schema) {
        try {
          const validate = ajv.compile(schema);
          const valid = validate(data);

          if (!valid) {
            const id = telemetryId();
            const incident: IncidentAlert = {
              severity: 'critical',
              type: 'SCHEMA_VIOLATION',
              message: `API response validation failed: ${ajv.errorsText(validate.errors)}`,
              path: req.path,
              timestamp: new Date().toISOString(),
              telemetryId: id,
              data: data,
            };

            logger.error('SCHEMA_VIOLATION', {
              telemetryId: id,
              path: req.path,
              errors: validate.errors,
            });

            if (alertFn) {
              alertFn(incident).catch((err) => {
                logger.error('Failed to send alert', { err });
              });
            }

            return res.status(503).json({
              error: 'Data validation failed - service unavailable',
              telemetryId: id,
            });
          }
        } catch (err) {
          logger.error('Schema validation error', { path: req.path, err });
        }
      }

      return originalJson(data);
    };

    next();
  };
}
