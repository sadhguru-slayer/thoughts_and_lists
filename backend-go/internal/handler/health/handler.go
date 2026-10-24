package health

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

// Response is what GET /health returns.
type Response struct {
	Status   string `json:"status"`
	Postgres string `json:"postgres"`
	Redis    string `json:"redis"`
}

// Handler returns an http.HandlerFunc that checks liveness of both
// Postgres and Redis, then responds with a JSON health report.
func Handler(pool *pgxpool.Pool, rdb *redis.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
		defer cancel()

		resp := Response{
			Status:   "ok",
			Postgres: "ok",
			Redis:    "ok",
		}
		statusCode := http.StatusOK

		// Check Postgres
		if err := pool.Ping(ctx); err != nil {
			resp.Postgres = "unreachable: " + err.Error()
			resp.Status = "degraded"
			statusCode = http.StatusServiceUnavailable
		}

		// Check Redis
		if err := rdb.Ping(ctx).Err(); err != nil {
			resp.Redis = "unreachable: " + err.Error()
			resp.Status = "degraded"
			statusCode = http.StatusServiceUnavailable
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(statusCode)
		_ = json.NewEncoder(w).Encode(resp)
	}
}
