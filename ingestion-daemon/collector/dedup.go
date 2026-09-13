package collector

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"strings"
	"sync"
	"time"
)

type DeduplicatedIncident struct {
	IncidentID       string `json:"incident_id"`
	FingerprintHash  string `json:"fingerprint_hash"`
	Service          string `json:"service"`
	ContainerID      string `json:"container_id"`
	OccurrenceCount  int    `json:"occurrence_count"`
	FirstSeen        string `json:"first_seen"`
	LastSeen         string `json:"last_seen"`
	SampleStackTrace string `json:"sample_stack_trace"`
	Status           string `json:"status"`
}

type Deduplicator struct {
	mu           sync.Mutex
	incidents    map[string]*DeduplicatedIncident
	debounceTime time.Duration
	emitChan     chan<- map[string]interface{}
}

func NewDeduplicator(emitChan chan<- map[string]interface{}, debounceTime time.Duration) *Deduplicator {
	d := &Deduplicator{
		incidents:    make(map[string]*DeduplicatedIncident),
		debounceTime: debounceTime,
		emitChan:     emitChan,
	}
	go d.flushLoop()
	return d
}

func (d *Deduplicator) generateHash(event *RawLogEvent) string {
	topFrame := ""
	if len(event.StackTrace) > 0 {
		lines := strings.Split(event.StackTrace, "\n")
		for i := len(lines) - 1; i >= 0; i-- {
			if strings.TrimSpace(lines[i]) != "" {
				topFrame = lines[i]
				break
			}
		}
	} else {
		topFrame = event.Message
	}
	
	payload := fmt.Sprintf("%s|%s|%s", event.Service, event.Message, topFrame)
	hash := sha256.Sum256([]byte(payload))
	return hex.EncodeToString(hash[:])
}

func (d *Deduplicator) Process(event *RawLogEvent) {
	if event.Level != "ERROR" && event.Level != "CRITICAL" {
		return // Only process errors
	}

	hash := d.generateHash(event)

	d.mu.Lock()
	defer d.mu.Unlock()

	incident, exists := d.incidents[hash]
	if !exists {
		incident = &DeduplicatedIncident{
			IncidentID:       fmt.Sprintf("inc_%s", hash[:8]),
			FingerprintHash:  hash,
			Service:          event.Service,
			ContainerID:      event.ContainerID,
			OccurrenceCount:  1,
			FirstSeen:        event.Timestamp,
			LastSeen:         event.Timestamp,
			SampleStackTrace: event.StackTrace,
			Status:           "NEW",
		}
		d.incidents[hash] = incident
	} else {
		incident.OccurrenceCount++
		incident.LastSeen = event.Timestamp
	}
}

func (d *Deduplicator) flushLoop() {
	ticker := time.NewTicker(d.debounceTime)
	for range ticker.C {
		d.mu.Lock()
		for hash, incident := range d.incidents {
			// Convert struct to map for JSON/Redis serialization
			var incidentMap map[string]interface{}
			data, _ := json.Marshal(incident)
			json.Unmarshal(data, &incidentMap)

			// Emit and remove from map
			select {
			case d.emitChan <- incidentMap:
				delete(d.incidents, hash)
			default:
				fmt.Println("Warning: emitChan full, dropping incident")
			}
		}
		d.mu.Unlock()
	}
}
