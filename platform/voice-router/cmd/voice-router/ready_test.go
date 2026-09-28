package main

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestReadyzIsTheBrainLaneAndCachesItsVerdict(t *testing.T) {
	calls := 0
	var fail error
	h := readyz(func(context.Context) error { calls++; return fail }, time.Hour)

	rec := httptest.NewRecorder()
	h(rec, httptest.NewRequest(http.MethodGet, "/readyz", nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("a lane that answers is ready: %d", rec.Code)
	}
	fail = errors.New("brain voice: 400 Bad Request: no healthy deployments")
	h(httptest.NewRecorder(), httptest.NewRequest(http.MethodGet, "/readyz", nil))
	if calls != 1 {
		t.Fatalf("within ttl the verdict is reused, not re-asked: %d calls", calls)
	}

	h = readyz(func(context.Context) error { return fail }, 0)
	rec = httptest.NewRecorder()
	h(rec, httptest.NewRequest(http.MethodGet, "/readyz", nil))
	if rec.Code != http.StatusServiceUnavailable || !strings.Contains(rec.Body.String(), "no healthy deployments") {
		t.Fatalf("a lane the router cannot serve is 503 with the router's words: %d %q", rec.Code, rec.Body.String())
	}
}
