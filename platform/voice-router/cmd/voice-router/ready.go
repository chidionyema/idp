package main

import (
	"context"
	"net/http"
	"sync"
	"time"
)

// readyz answers 200 only when the brain lane answers, and 503 with the router's own error
// when it does not. The verdict is kept for ttl so a probe loop costs one token per ttl.
func readyz(ready func(context.Context) error, ttl time.Duration) http.HandlerFunc {
	var mu sync.Mutex
	var at time.Time
	var last error
	return func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		if at.IsZero() || time.Since(at) >= ttl {
			ctx, cancel := context.WithTimeout(r.Context(), 15*time.Second)
			last, at = ready(ctx), time.Now()
			cancel()
		}
		err := last
		mu.Unlock()
		if err != nil {
			http.Error(w, err.Error(), http.StatusServiceUnavailable)
			return
		}
		_, _ = w.Write([]byte("ok\n"))
	}
}
