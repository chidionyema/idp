package main

import (
	"reflect"
	"testing"
	"time"

	"github.com/nats-io/nats.go"
)

func TestNewsStreamConfig(t *testing.T) {
	cfg := newsStreamConfig()
	if cfg.Name != "ESTATE_NEWS" {
		t.Errorf("Name = %q, want ESTATE_NEWS", cfg.Name)
	}
	if !reflect.DeepEqual(cfg.Subjects, []string{"estate.news.>"}) {
		t.Errorf("Subjects = %v, want [estate.news.>]", cfg.Subjects)
	}
	if cfg.Storage != nats.FileStorage {
		t.Errorf("Storage = %v, want FileStorage", cfg.Storage)
	}
	if cfg.MaxAge != 24*time.Hour {
		t.Errorf("MaxAge = %v, want 24h", cfg.MaxAge)
	}
	if cfg.MaxMsgs != 5000 {
		t.Errorf("MaxMsgs = %d, want 5000", cfg.MaxMsgs)
	}
	if cfg.MaxBytes != 10485760 {
		t.Errorf("MaxBytes = %d, want 10485760", cfg.MaxBytes)
	}
}

func TestEpistemicSubjects(t *testing.T) {
	want := []string{"epistemic.cicd", "epistemic.incidents"}
	if !reflect.DeepEqual(epistemicSubjects, want) {
		t.Errorf("epistemicSubjects = %v, want %v", epistemicSubjects, want)
	}
}
