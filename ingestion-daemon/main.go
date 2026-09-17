package main

import (
	"context"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"ingestion-daemon/collector"
	"ingestion-daemon/redisclient"
)

var (
	incidentsIngested = promauto.NewCounter(prometheus.CounterOpts{
		Name: "agenticmesh_incidents_ingested_total",
		Help: "The total number of ingested incidents",
	})
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

	mux := http.NewServeMux()

	mux.HandleFunc("/ingest", func(w http.ResponseWriter, r *http.Request) {
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

		if event.Level == "ERROR" || event.Level == "CRITICAL" {
			dedup.Process(event)
			incidentsIngested.Inc()
		}

		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, "{\"status\": \"ingested\"}")
	})

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, "{\"status\": \"OK\"}")
	})

	mux.Handle("/metrics", promhttp.Handler())

	port := "8080"
	server := &http.Server{
		Addr:    ":" + port,
		Handler: mux,
	}

	go func() {
		log.Printf("Starting Ingestion Daemon on port %s", port)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server failed: %v", err)
		}
	}()

	// Graceful shutdown
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)
	<-stop

	log.Println("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	log.Println("Server exiting")
}
