package db

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/jackc/pgx/v5/pgxpool"
)

// NewPool creates and validates a pgxpool connection pool.
// pgxpool is concurrency-safe and reuses connections – equivalent to
// SQLAlchemy's async engine with a pool.
//
// The caller owns the pool and must call pool.Close() on shutdown.
func normalizeDatabaseURL(rawURL string) string {
	schemes := []string{
		"postgresql+asyncpg://",
		"postgres+asyncpg://",
		"postgresql+psycopg2://",
		"postgres+psycopg2://",
		"postgresql+psycopg://",
		"postgres+psycopg://",
	}
	for _, s := range schemes {
		if strings.HasPrefix(rawURL, s) {
			return "postgresql://" + strings.TrimPrefix(rawURL, s)
		}
	}
	return rawURL
}

func NewPool(ctx context.Context, databaseURL string) (*pgxpool.Pool, error) {
	databaseURL = normalizeDatabaseURL(databaseURL)
	cfg, err := pgxpool.ParseConfig(databaseURL)
	if err != nil {
		return nil, fmt.Errorf("db: parse config: %w", err)
	}

	// Mirror what Python does: statement_cache_size = 0
	// (needed when pgbouncer is in transaction-mode or on some managed DBs)
	cfg.ConnConfig.DefaultQueryExecMode = 4 // pgx.QueryExecModeSimpleProtocol

	pool, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		return nil, fmt.Errorf("db: create pool: %w", err)
	}

	// Fail fast — surface bad DATABASE_URL before the server starts.
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("db: ping failed: %w", err)
	}

	log.Println("[db] postgres connection pool established")
	return pool, nil
}
