// cmd/quad-ledger/chain.go
// Layer 4: the hash chain. Pure functions, no I/O, so the tamper test below needs no database.
//
// Each action row commits to every row before it: row_hash = SHA-256(prev_hash || canonical(row)).
// The chain head after N rows is the commitment the anchor job publishes to OCI Object Storage.
// A hash chain is the degenerate Merkle tree (one leaf per level); it gives the same tamper
// evidence the spec asks of merkle_root, with an O(N) verify that the estate's row counts allow.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strings"
)

// ZeroHash is prev_hash of the first row.
const ZeroHash = "0000000000000000000000000000000000000000000000000000000000000000"

// Action is one signed request as Elpis reported it on the bus (subject estate.quad.actions.>).
type Action struct {
	ActionID       string `json:"action_id"`
	ParentActionID string `json:"parent_action_id,omitempty"`
	AgentURN       string `json:"agent_urn"`
	SessionID      string `json:"session_id"`
	Method         string `json:"method"`
	URI            string `json:"uri"`
	Timestamp      string `json:"timestamp"`
	BodyHash       string `json:"body_hash"`
	Signature      string `json:"signature"`
}

// Canonical is the byte string the row hash covers. Newline-delimited, same discipline as the
// Elpis signing string, so a field cannot be moved into another.
func (a Action) Canonical() string {
	return strings.Join([]string{
		a.ActionID, a.ParentActionID, a.AgentURN, a.SessionID,
		a.Method, a.URI, a.Timestamp, a.BodyHash, a.Signature,
	}, "\n")
}

// RowHash chains this action onto prev.
func RowHash(prev string, a Action) string {
	h := sha256.New()
	h.Write([]byte(prev))
	h.Write([]byte{'\n'})
	h.Write([]byte(a.Canonical()))
	return hex.EncodeToString(h.Sum(nil))
}

// Row is what the database holds.
type Row struct {
	Seq      int64
	Action   Action
	PrevHash string
	RowHash  string
}

// Verify walks rows in seq order and recomputes every hash. It returns the head and the first
// seq that disagrees (0 when the chain is intact). expectedHead, when non-empty, is the anchored
// root; a chain that verifies internally but does not end at the anchor is still a failure,
// because that is exactly what a truncation looks like.
func Verify(rows []Row, expectedHead string) (head string, badSeq int64, err error) {
	prev := ZeroHash
	for _, r := range rows {
		if r.PrevHash != prev {
			return prev, r.Seq, fmt.Errorf("seq %d: prev_hash %s does not match chain %s", r.Seq, short(r.PrevHash), short(prev))
		}
		want := RowHash(prev, r.Action)
		if r.RowHash != want {
			return prev, r.Seq, fmt.Errorf("seq %d: row_hash %s, recomputed %s (row altered)", r.Seq, short(r.RowHash), short(want))
		}
		prev = r.RowHash
	}
	if expectedHead != "" && prev != expectedHead {
		return prev, -1, fmt.Errorf("chain head %s does not match anchor %s (rows removed or anchor stale)", short(prev), short(expectedHead))
	}
	return prev, 0, nil
}

func short(h string) string {
	if len(h) > 12 {
		return h[:12]
	}
	return h
}
