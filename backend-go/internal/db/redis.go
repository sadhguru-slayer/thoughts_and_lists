package db

import (
	"context"
	"fmt"
	"log"

	"github.com/redis/go-redis/v9"
)

// NewRedis parses REDIS_URL and returns a connected *redis.Client.
// Equivalent to the Python:
//
//	redis_client = redis.from_url(REDIS_URL, decode_responses=True)
//
// The caller owns the client and must call client.Close() on shutdown.
func NewRedis(ctx context.Context, redisURL string) (*redis.Client, error) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("redis: parse url: %w", err)
	}

	client := redis.NewClient(opts)

	// Equivalent to the Python startup: await redis_client.ping()
	if err := client.Ping(ctx).Err(); err != nil {
		_ = client.Close()
		return nil, fmt.Errorf("redis: ping failed: %w", err)
	}

	log.Println("[db] redis connection established")
	return client, nil
}
