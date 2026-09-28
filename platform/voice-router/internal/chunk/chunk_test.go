package chunk

import (
	"reflect"
	"strings"
	"testing"
)

func run(tokens []string) []string {
	var c Chunker
	var out []string
	for _, t := range tokens {
		out = append(out, c.Push(t)...)
	}
	if rest := c.Flush(); rest != "" {
		out = append(out, rest)
	}
	return out
}

func TestChunker(t *testing.T) {
	cases := []struct {
		name   string
		tokens []string
		want   []string
	}{
		{"two sentences split across tokens", []string{"All five", " agents are", " healthy", ".", " The build", " passed."},
			[]string{"All five agents are healthy.", "The build passed."}},
		{"question and exclamation", []string{"Ready? ", "Go! ", "Now"}, []string{"Ready?", "Go!", "Now"}},
		{"decimal is not a boundary", []string{"Latency is 3.5", " seconds. Done"}, []string{"Latency is 3.5 seconds.", "Done"}},
		{"version is not a boundary", []string{"Running v1.2.3 now."}, []string{"Running v1.2.3 now."}},
		{"abbreviation is not a boundary", []string{"Ask Dr. Smith, e.g. today. Then"}, []string{"Ask Dr. Smith, e.g. today.", "Then"}},
		{"initial is not a boundary", []string{"J. Smith approved it. Next"}, []string{"J. Smith approved it.", "Next"}},
		{"newline ends a phrase", []string{"one\ntwo"}, []string{"one", "two"}},
		{"short comma clause stays whole", []string{"Yes, it did. "}, []string{"Yes, it did."}},
		{"long comma clause is released early",
			[]string{strings.Repeat("word ", 13) + "and more, then the rest"},
			[]string{strings.Repeat("word ", 13) + "and more,", "then the rest"}},
		{"trailing period waits for confirmation", []string{"Done."}, []string{"Done."}},
		{"empty stream", nil, nil},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if got := run(c.tokens); !reflect.DeepEqual(got, c.want) {
				t.Fatalf("got %q want %q", got, c.want)
			}
		})
	}
}

// The first phrase must come out the moment its boundary is confirmed, not
// when the stream ends; that is the whole latency win.
func TestFirstPhraseIsReleasedMidStream(t *testing.T) {
	var c Chunker
	if got := c.Push("Hello there."); got != nil {
		t.Fatalf("released before boundary confirmed: %q", got)
	}
	if got := c.Push(" How"); !reflect.DeepEqual(got, []string{"Hello there."}) {
		t.Fatalf("got %q", got)
	}
}

func TestFirstPhraseBreaksAtEarlyComma(t *testing.T) {
	c := Chunker{First: true}
	got := c.Push("Right now, five agents are working, and two builds are queued. ")
	want := []string{"Right now,", "five agents are working, and two builds are queued."}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("got %q want %q", got, want)
	}
}
