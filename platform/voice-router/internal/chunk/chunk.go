// Package chunk turns a stream of LLM tokens into speakable phrases, so the
// voice can start on the first sentence while the brain is still writing the
// rest.
package chunk

import (
	"strings"
	"unicode"
)

// commaFlush is how long a phrase may grow before a comma also ends it. Long
// clauses otherwise hold the first audio back.
const commaFlush = 60

var abbrev = map[string]bool{"mr": true, "mrs": true, "ms": true, "dr": true, "st": true, "vs": true, "etc": true, "e.g": true, "i.e": true, "approx": true}

// firstComma is the shorter comma limit for a reply's first phrase: the
// synthesiser renders a phrase whole, so a short opener is the first audio.
const firstComma = 4

// Chunker buffers tokens and releases whole phrases. With First set, the
// first phrase also ends at an early comma.
type Chunker struct {
	First bool
	buf   strings.Builder
}

// Push adds a token and returns any phrases it completed.
func (c *Chunker) Push(tok string) []string {
	c.buf.WriteString(tok)
	var out []string
	for {
		s := c.buf.String()
		limit := commaFlush
		if c.First {
			limit = firstComma
		}
		i := boundary(s, limit)
		if i < 0 {
			return out
		}
		if p := strings.TrimSpace(s[:i]); p != "" {
			out = append(out, p)
		}
		c.First = false
		rest := s[i:]
		c.buf.Reset()
		c.buf.WriteString(rest)
	}
}

// Flush returns whatever is left once the stream ends.
func (c *Chunker) Flush() string {
	s := strings.TrimSpace(c.buf.String())
	c.buf.Reset()
	return s
}

// boundary returns the index just past a phrase end, or -1. A boundary is
// terminal punctuation followed by whitespace, so "3.5" and "v1.2" never split
// and a trailing "." waits for the next token to confirm it.
func boundary(s string, comma int) int {
	for i := 0; i < len(s)-1; i++ {
		ch := s[i]
		next := rune(s[i+1])
		if ch == '\n' {
			return i + 1
		}
		if !unicode.IsSpace(next) {
			continue
		}
		switch ch {
		case '.':
			if isAbbrev(s[:i]) {
				continue
			}
			return i + 1
		case '!', '?', ';', ':':
			return i + 1
		case ',':
			if i >= comma {
				return i + 1
			}
		}
	}
	return -1
}

func isAbbrev(before string) bool {
	j := strings.LastIndexFunc(before, func(r rune) bool { return unicode.IsSpace(r) })
	w := strings.ToLower(before[j+1:])
	if len(w) == 1 && unicode.IsLetter(rune(w[0])) {
		return true // initials: "J. Smith"
	}
	return abbrev[w]
}
