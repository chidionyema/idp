package main

import "testing"

func sample(n int) []Row {
	rows := make([]Row, 0, n)
	prev := ZeroHash
	for i := 0; i < n; i++ {
		a := Action{
			ActionID: "act-" + string(rune('a'+i)), AgentURN: "urn:estate:agent:test", SessionID: "s1",
			Method: "POST", URI: "/v1/messages", Timestamp: "1727700000", BodyHash: "b", Signature: "sig",
		}
		if i > 0 {
			a.ParentActionID = rows[i-1].Action.ActionID
		}
		h := RowHash(prev, a)
		rows = append(rows, Row{Seq: int64(i + 1), Action: a, PrevHash: prev, RowHash: h})
		prev = h
	}
	return rows
}

func TestIntactChainVerifies(t *testing.T) {
	rows := sample(5)
	head, bad, err := Verify(rows, rows[4].RowHash)
	if err != nil || bad != 0 || head != rows[4].RowHash {
		t.Fatalf("intact chain failed: head=%s bad=%d err=%v", head, bad, err)
	}
}

// Planted fault 1: an operator edits one field of one row after the fact.
func TestAlteredRowGoesRed(t *testing.T) {
	rows := sample(5)
	rows[2].Action.URI = "/v1/admin/delete-namespace" // the lie
	_, bad, err := Verify(rows, rows[4].RowHash)
	if err == nil || bad != 3 {
		t.Fatalf("altered row not detected: bad=%d err=%v", bad, err)
	}
}

// Planted fault 2: a row is deleted and the chain re-linked to hide it.
func TestDeletedRowGoesRed(t *testing.T) {
	rows := sample(5)
	anchored := rows[4].RowHash
	cut := append(rows[:2:2], rows[3:]...) // drop seq 3
	cut[2].PrevHash = rows[1].RowHash      // re-link so prev_hash agrees
	cut[2].RowHash = RowHash(cut[2].PrevHash, cut[2].Action)
	cut[3].PrevHash = cut[2].RowHash
	cut[3].RowHash = RowHash(cut[3].PrevHash, cut[3].Action)
	_, _, err := Verify(cut, anchored)
	if err == nil {
		t.Fatal("deleted row with re-linked chain not detected against the anchor")
	}
}

// Planted fault 3: rows appended after the anchor are fine; rows removed after the anchor are not.
func TestTruncationGoesRed(t *testing.T) {
	rows := sample(5)
	_, _, err := Verify(rows[:4], rows[4].RowHash)
	if err == nil {
		t.Fatal("truncated chain verified against a longer anchor")
	}
}
