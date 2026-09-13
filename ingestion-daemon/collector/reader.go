package collector

import (
	"encoding/json"
	"fmt"
)

type RawLogEvent struct {
	Timestamp   string `json:"timestamp"`
	Service     string `json:"service"`
	Level       string `json:"level"`
	Message     string `json:"message"`
	StackTrace  string `json:"stack_trace"`
	Route       string `json:"route"`
	ContainerID string `json:"container_id"`
}

func ParseLogEvent(data []byte) (*RawLogEvent, error) {
	var event RawLogEvent
	if err := json.Unmarshal(data, &event); err != nil {
		return nil, fmt.Errorf("failed to parse json: %v", err)
	}
	return &event, nil
}
