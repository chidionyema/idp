package main

import (
	"bufio"
	"fmt"
	"net"
	"strings"
	"testing"
	"time"
)

// fakeRedis speaks the minimum RESP needed to grade AUTH: it records every command
// it receives and answers +OK to AUTH, *2 to SMEMBERS.
func fakeRedis(t *testing.T) (addr string, received func() []string) {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	var cmds []string
	go func() {
		for {
			c, err := ln.Accept()
			if err != nil {
				return
			}
			go func(c net.Conn) {
				defer c.Close()
				r := bufio.NewReader(c)
				for {
					line, err := r.ReadString('\n')
					if err != nil {
						return
					}
					line = strings.TrimRight(line, "\r\n")
					if !strings.HasPrefix(line, "*") {
						return
					}
					var count int
					fmt.Sscanf(line, "*%d", &count)
					fields := []string{}
					for i := 0; i < count; i++ {
						h, _ := r.ReadString('\n')
						h = strings.TrimRight(h, "\r\n")
						var blen int
						fmt.Sscanf(h, "$%d", &blen)
						buf := make([]byte, blen+2)
						r.Read(buf)
						fields = append(fields, string(buf[:blen]))
					}
					cmds = append(cmds, strings.Join(fields, " "))
					if strings.EqualFold(fields[0], "AUTH") {
						c.Write([]byte("+OK\r\n"))
					} else if strings.EqualFold(fields[0], "SMEMBERS") {
						c.Write([]byte("*2\r\n$3\r\nfoo\r\n$3\r\nbar\r\n"))
					} else {
						c.Write([]byte("*0\r\n"))
					}
				}
			}(c)
		}
	}()
	return ln.Addr().String(), func() []string { return cmds }
}

// The bug this proves fixed: a password folded into the URL was never turned into an
// AUTH command, so Redis answered -NOAUTH and the proxy served a frozen cache for 4 days.
func TestRedisCommandSendsAuthWhenURLHasPassword(t *testing.T) {
	addr, received := fakeRedis(t)
	u := "redis://:s3cret@" + addr + "/0"
	out, err := redisCommand(u, []string{"SMEMBERS", "k"}, 3*time.Second)
	if err != nil {
		t.Fatalf("redisCommand errored: %v", err)
	}
	got := received()
	if len(got) == 0 || !strings.HasPrefix(strings.ToUpper(got[0]), "AUTH") {
		t.Fatalf("expected AUTH first, got %q", got)
	}
	if len(got) < 2 || !strings.HasPrefix(strings.ToUpper(got[1]), "SMEMBERS") {
		t.Fatalf("expected SMEMBERS second, got %q", got)
	}
	if len(out) != 2 || out[0] != "foo" {
		t.Fatalf("expected the SMEMBERS reply, got %q", out)
	}
}

// A URL with no password must not send AUTH.
func TestRedisCommandSendsNoAuthWithoutPassword(t *testing.T) {
	addr, received := fakeRedis(t)
	out, err := redisCommand("redis://"+addr, []string{"SMEMBERS", "k"}, 3*time.Second)
	if err != nil {
		t.Fatalf("redisCommand errored: %v", err)
	}
	got := received()
	if len(got) == 0 || strings.HasPrefix(strings.ToUpper(got[0]), "AUTH") {
		t.Fatalf("expected no AUTH, got %q", got)
	}
	if len(out) != 2 {
		t.Fatalf("expected the reply, got %q", out)
	}
}

// A user-qualified URL (Redis 6 ACL) must send AUTH <user> <pass>.
func TestRedisCommandSendsUserQualifiedAuth(t *testing.T) {
	addr, received := fakeRedis(t)
	u := "redis://default:s3cret@" + addr + "/0"
	if _, err := redisCommand(u, []string{"SMEMBERS", "k"}, 3*time.Second); err != nil {
		t.Fatalf("redisCommand errored: %v", err)
	}
	got := received()
	if len(got) == 0 || got[0] != "AUTH default s3cret" {
		t.Fatalf("expected 'AUTH default s3cret', got %q", got)
	}
}
