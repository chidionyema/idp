package newsroom

import (
	"encoding/json"
	"fmt"
	"strconv"
	"time"
)

const (
	SubjectCICD      = "epistemic.cicd"
	SubjectIncidents = "epistemic.incidents"
)

type workflowRun struct {
	ID         int64  `json:"id"`
	Name       string `json:"name"`
	Status     string `json:"status"`
	Conclusion string `json:"conclusion"`
	UpdatedAt  string `json:"updated_at"`
	HeadBranch string `json:"head_branch"`
	HTMLURL    string `json:"html_url"`
}

type issue struct {
	Number    int    `json:"number"`
	Title     string `json:"title"`
	State     string `json:"state"`
	UpdatedAt string `json:"updated_at"`
	HTMLURL   string `json:"html_url"`
}

// DecodeEpistemic decodes the plain JSON body epistemic-ingest publishes on
// epistemic.cicd / epistemic.incidents (binary-mode CloudEvents carry their
// ce-* attributes as NATS headers, not in the body).
//
// epistemic-ingest cicd publishes a run once, the first time its id is newer
// than the last seen. A run that was still in progress on that poll is never
// republished on completion, so only runs already completed when first
// polled reach the newsroom. That is a producer limit, recorded here and not
// fixed in P1.
func DecodeEpistemic(subject string, data []byte, now time.Time) (Raw, bool) {
	switch subject {
	case SubjectCICD:
		var r workflowRun
		if err := json.Unmarshal(data, &r); err != nil {
			return Raw{}, false
		}
		if r.Status != "completed" {
			return Raw{}, false
		}
		var kind, severity string
		switch r.Conclusion {
		case "failure", "timed_out", "startup_failure":
			kind, severity = "cicd.failed", "warn"
		case "success":
			kind, severity = "cicd.passed", "info"
		default:
			return Raw{}, false
		}
		at, err := time.Parse(time.RFC3339, r.UpdatedAt)
		if err != nil {
			at = now
		}
		return Raw{
			Source: "cicd", Kind: kind, Severity: severity,
			Entity:  "workflow/" + r.Name + "/" + r.HeadBranch,
			Name:    r.Name,
			Reason:  r.HeadBranch,
			Message: fmt.Sprintf("run %d %s", r.ID, r.Conclusion),
			Link:    r.HTMLURL,
			At:      at,
		}, true

	case SubjectIncidents:
		var it issue
		if err := json.Unmarshal(data, &it); err != nil {
			return Raw{}, false
		}
		var kind, severity string
		switch it.State {
		case "open":
			kind, severity = "incident.open", "danger"
		case "closed":
			kind, severity = "incident.closed", "info"
		default:
			return Raw{}, false
		}
		at, err := time.Parse(time.RFC3339, it.UpdatedAt)
		if err != nil {
			at = now
		}
		return Raw{
			Source: "incidents", Kind: kind, Severity: severity,
			Entity:  "incident/" + strconv.Itoa(it.Number),
			Name:    it.Title,
			Reason:  it.State,
			Message: it.Title,
			Link:    it.HTMLURL,
			At:      at,
		}, true

	default:
		return Raw{}, false
	}
}
