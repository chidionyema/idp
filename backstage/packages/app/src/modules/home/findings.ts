// The cluster doctor's findings (crew#718, founder 2026-09-01: "we did not conclude the cluster
// gpt, i need to be using it ... no black boxes in estate ... everything must be visible to
// founder"). K8sGPT (platform/healing) has analysed the cluster since 2026-08-27 and written
// every diagnosis as a Result object in the healing namespace; a Prometheus rule counts them,
// and nobody ever read one. This module turns the Result list and the doctor's own Deployment
// into the sentence and the rows the Ops page shows. Pure: no fetch, no clock.
//
// Shape from the operator's API (k8sgpt-operator api/v1alpha1/result_types.go): spec.kind and
// spec.name say which object is broken, spec.error[].text is what K8sGPT saw, spec.details is
// the model's plain-English diagnosis.

/** The K8sGPT object platform/healing/analyzer/k8sgpt.yaml declares; the operator names the
 * doctor's Deployment and Service after it. tests/test_crew718_cluster_doctor_findings_reach_
 * the_ops_page.py refuses a drift between these two constants and that manifest. */
export const DOCTOR_NAMESPACE = 'healing';
export const DOCTOR_NAME = 'estate';

export type ResultObject = {
  metadata: { name: string; namespace?: string; creationTimestamp?: string };
  spec?: {
    kind?: string;
    name?: string;
    parentObject?: string;
    details?: string;
    backend?: string;
    error?: { text?: string }[];
  };
};

export type DeploymentObject = {
  metadata: { name: string; namespace?: string };
  status?: { readyReplicas?: number; replicas?: number };
};

export type Finding = {
  key: string;
  /** "Pod healing/estate-7c9d" — the broken object, as K8sGPT names it. */
  object: string;
  /** What K8sGPT saw, one line each. */
  seen: string[];
  /** The model's diagnosis, verbatim; may be several paragraphs. */
  details: string;
  since?: string;
};

export type Doctor = {
  /** The doctor's Deployment has a ready replica. */
  running: boolean;
  findings: Finding[];
};

const isDoctor = (d: DeploymentObject) =>
  d.metadata.name === DOCTOR_NAME &&
  (d.metadata.namespace ?? DOCTOR_NAMESPACE) === DOCTOR_NAMESPACE;

export const summariseFindings = (
  results: ResultObject[],
  deployments: DeploymentObject[],
): Doctor => {
  const doctor = deployments.find(isDoctor);
  const running = (doctor?.status?.readyReplicas ?? 0) > 0;
  const findings = results
    .map<Finding>(r => ({
      key: `${r.metadata.namespace ?? ''}/${r.metadata.name}`,
      object: `${r.spec?.kind ?? 'Object'} ${r.spec?.name ?? r.metadata.name}`,
      seen: (r.spec?.error ?? [])
        .map(e => (e.text ?? '').trim())
        .filter(Boolean),
      details: (r.spec?.details ?? '').trim(),
      since: r.metadata.creationTimestamp,
    }))
    .sort((a, b) => (b.since ?? '').localeCompare(a.since ?? ''));
  return { running, findings };
};

/** The one sentence the tile leads with; the login drill grades the page on "Cluster doctor". */
export const doctorSentence = (d: Doctor): string => {
  const n = d.findings.length;
  const count = `${n} finding${n === 1 ? '' : 's'}`;
  if (!d.running && n === 0)
    return 'The cluster doctor (K8sGPT) is not running, so nothing has been checked.';
  if (!d.running)
    return `The cluster doctor (K8sGPT) is not running; these ${count} are from its last run.`;
  if (n === 0)
    return 'The cluster doctor (K8sGPT) is running and has nothing to report.';
  return `The cluster doctor (K8sGPT) has ${count}, newest first.`;
};
