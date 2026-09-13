package redisclient

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	"github.com/redis/go-redis/v9"
)

type RedisClient struct {
	client *redis.Client
}

func NewRedisClient() (*RedisClient, error) {
	redisURL := os.Getenv("UPSTASH_REDIS_URL")
	if redisURL == "" {
		redisURL = "redis://redis:6379/0"
	}

	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse redis url: %v", err)
	}

	client := redis.NewClient(opts)

	if err := client.Ping(context.Background()).Err(); err != nil {
		return nil, fmt.Errorf("failed to ping redis: %v", err)
	}

	return &RedisClient{client: client}, nil
}

func (r *RedisClient) PublishIncident(ctx context.Context, stream string, incident map[string]interface{}) error {
	data, err := json.Marshal(incident)
	if err != nil {
		return err
	}

	err = r.client.XAdd(ctx, &redis.XAddArgs{
		Stream: stream,
		Values: map[string]interface{}{"payload": string(data)},
	}).Err()

	return err
}
