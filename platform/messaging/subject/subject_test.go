package subject

import "testing"

// The fixtures of docs/prose/messaging-cp3.feature, scenario 1.
func TestGoodFixture(t *testing.T) {
	s, err := Parse("orders.event.order.placed.v1")
	if err != nil {
		t.Fatal(err)
	}
	if s.String() != "orders.event.order.placed.v1" {
		t.Fatalf("round trip: %s", s)
	}
}

func TestBadFixturesNameTheRule(t *testing.T) {
	cases := map[string]string{
		"prod.orders.event.order.placed.v1": "D1-shape",
		"prod.event.order.placed.v1":        "D1-no-environment",
		"orders.event.order.place.v1":       "D1-past-tense",
		"orders.event.Order.placed.v1":      "D1-case",
		"orders.event.order.placed.1":       "D1-version",
		"orders.thing.order.placed.v1":      "D1-kind",
	}
	for raw, rule := range cases {
		_, err := Parse(raw)
		if err == nil {
			t.Errorf("%s: accepted", raw)
			continue
		}
		if !contains(err.Error(), rule) {
			t.Errorf("%s: wanted rule %s, got %v", raw, rule, err)
		}
	}
}

func contains(s, sub string) bool {
	return len(sub) > 0 && len(s) >= len(sub) && (func() bool {
		for i := 0; i+len(sub) <= len(s); i++ {
			if s[i:i+len(sub)] == sub {
				return true
			}
		}
		return false
	})()
}
