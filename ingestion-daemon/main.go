package main

import (
	"context"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"time"

	"ingestion-daemon/collector"
	"ingestion-daemon/redisclient"
)

func main() {
	redisCli, err := redisclient.NewRedisClient()
	if err != nil {
		log.Fatalf("Failed to initialize Redis client: %v", err)
	}

	emitChan := make(chan map[string]interface{}, 100)
	dedup := collector.NewDeduplicator(emitChan, 5*time.Second)

	// Background worker to publish to Redis
	go func() {
		ctx := context.Background()
		for incident := range emitChan {
			err := redisCli.PublishIncident(ctx, "incidents", incident)
			if err != nil {
				log.Printf("Error publishing to Redis: %v", err)
			} else {
				log.Printf("Published incident %v to Redis", incident["incident_id"])
			}
		}
	}()

	http.HandleFunc("/ingest", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		body, err := ioutil.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "Failed to read body", http.StatusBadRequest)
			return
		}
		defer r.Body.Close()

		event, err := collector.ParseLogEvent(body)
		if err != nil {
			http.Error(w, "Invalid log format", http.StatusBadRequest)
			return
		}

		// Only process non-health events if they are errors
		if event.Level == "ERROR" || event.Level == "CRITICAL" {
			dedup.Process(event)
		}

		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, "{\"status\": \"ingested\"}")
	})

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, "{\"status\": \"OK\"}")
	})

	port := "8080"
	log.Printf("Starting Ingestion Daemon on port %s", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
