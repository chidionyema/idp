// Command talk is an end-to-end probe: it streams a WAV into /voice/ws at real
// time, as a microphone would, then silence, and times what comes back from
// the moment speech ends.
package main

import (
	"context"
	"encoding/binary"
	"encoding/json"
	"flag"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/coder/websocket"
	sherpa "github.com/k2-fsa/sherpa-onnx-go/sherpa_onnx"
)

func main() {
	url := flag.String("url", "ws://127.0.0.1:8091/voice/ws", "voice-router socket")
	origin := flag.String("origin", "http://localhost:3100", "Origin header")
	wav := flag.String("wav", "/tmp/vbench/q.wav", "16 kHz mono speech")
	out := flag.String("out", "", "write the reply audio here (raw int16 LE)")
	say := flag.String("say", "", "send this as a say instead of streaming the wav; times from the send")
	flag.Parse()

	w := sherpa.ReadWave(*wav)
	if w == nil || w.SampleRate != 16000 {
		fmt.Println("need a 16 kHz wav")
		os.Exit(2)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()
	c, _, err := websocket.Dial(ctx, *url, &websocket.DialOptions{HTTPHeader: http.Header{"Origin": {*origin}}})
	if err != nil {
		fmt.Println("dial:", err)
		os.Exit(1)
	}
	defer c.CloseNow()
	c.SetReadLimit(8 << 20)

	var speechEnd time.Time
	if *say != "" {
		b, _ := json.Marshal(map[string]string{"type": "say", "text": *say})
		speechEnd = time.Now()
		if err := c.Write(ctx, websocket.MessageText, b); err != nil {
			fmt.Println("say:", err)
			os.Exit(1)
		}
	} else {
		go stream(ctx, c, w.Samples, &speechEnd)
	}

	since := func() string {
		if speechEnd.IsZero() {
			return "  (speaking)"
		}
		return fmt.Sprintf("+%5dms", time.Since(speechEnd).Milliseconds())
	}
	var f *os.File
	if *out != "" {
		f, _ = os.Create(*out)
		defer f.Close()
	}
	var audioSamples, rate int
	firstAudio := true
	for {
		typ, data, err := c.Read(ctx)
		if err != nil {
			fmt.Println("read:", err)
			return
		}
		if typ == websocket.MessageBinary {
			if firstAudio {
				fmt.Printf("%s first audio (turn %d)\n", since(), binary.LittleEndian.Uint32(data))
				firstAudio = false
			}
			audioSamples += (len(data) - 4) / 2
			if f != nil {
				_, _ = f.Write(data[4:])
			}
			continue
		}
		var e struct {
			Type, Text string
			Turn, Rate int
		}
		_ = json.Unmarshal(data, &e)
		if e.Type == "hello" {
			rate = e.Rate
		}
		fmt.Printf("%s %-6s %d %q\n", since(), e.Type, e.Turn, e.Text)
		if e.Type == "done" || e.Type == "error" {
			fmt.Printf("reply audio %.2fs at %d Hz\n", float64(audioSamples)/float64(rate), rate)
			return
		}
	}
}

// stream sends samples at real time, then room silence, as a live mic does.
func stream(ctx context.Context, c *websocket.Conn, samples []float32, speechEnd *time.Time) {
	const frame = 320 // 20 ms
	send := func(s []float32) {
		b := make([]byte, 2*len(s))
		for i, v := range s {
			binary.LittleEndian.PutUint16(b[2*i:], uint16(int16(v*32767)))
		}
		_ = c.Write(ctx, websocket.MessageBinary, b)
	}
	tick := time.NewTicker(20 * time.Millisecond)
	defer tick.Stop()
	for i := 0; i < len(samples); i += frame {
		<-tick.C
		send(samples[i:min(i+frame, len(samples))])
	}
	*speechEnd = time.Now()
	for ctx.Err() == nil { // room silence, as a live mic keeps sending
		<-tick.C
		send(make([]float32, frame))
	}
}
