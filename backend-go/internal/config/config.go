package config

import (
	"fmt"
	"log"
	"os"

	"github.com/joho/godotenv"
)

// Config holds every environment variable the app needs.
// Add new fields here as we build more phases.
type Config struct {
	// Server
	Port        string
	Environment string

	// Postgres
	DatabaseURL string

	// Redis
	RedisURL string

	// JWT
	SecretKey string

	// SMTP Email
	SMTPHost     string
	SMTPPort     string
	SMTPUsername string
	SMTPPassword string

	// Gmail OAuth (matches Python FastAPI setup)
	GmailClientID     string
	GmailClientSecret string
	GmailRefreshToken string

	// CORS
	FrontendURL  string
	FrontendURL2 string
}

// Load reads the .env file (if present) then overlays actual environment
// variables. Docker supplies real env vars so .env is optional in prod.
func Load() *Config {
	// Best-effort: load .env when running locally without Docker.
	// In Docker we use env_file / environment in compose so this is a no-op.
	if err := godotenv.Load(); err != nil {
		log.Println("[config] no .env file found – using environment variables")
	}

	secretKey := getEnv("SECRET_KEY", "3RA27JmF18ikTwH19dsdfb772t3YDzSl4LKEzDNzcCq2dBsqY=")

	cfg := &Config{
		Port:              getEnv("PORT", "8000"),
		Environment:       getEnv("ENVIRONMENT", "development"),
		DatabaseURL:       mustGetEnv("DATABASE_URL"),
		RedisURL:          mustGetEnv("REDIS_URL"),
		SecretKey:         secretKey,
		SMTPHost:          getEnv("SMTP_SERVER", "smtp.gmail.com"),
		SMTPPort:          getEnv("SMTP_PORT", "587"),
		SMTPUsername:      getEnv("EMAIL", ""),
		SMTPPassword:      getEnv("APP_PASSWORD", ""),
		GmailClientID:     getEnv("CLIENT_ID", getEnv("GMAIL_CLIENT_ID", "")),
		GmailClientSecret: getEnv("CLIENT_SECRET", getEnv("GMAIL_CLIENT_SECRET", "")),
		GmailRefreshToken: getEnv("REFRESH_TOKEN", getEnv("GMAIL_REFRESH_TOKEN", "")),
		FrontendURL:       getEnv("FRONTEND_URL", "http://localhost:3000"),
		FrontendURL2:      getEnv("FRONTEND_URL_2", "http://localhost:3000"),
	}

	return cfg
}

// IsDevelopment returns true when running outside production.
func (c *Config) IsDevelopment() bool {
	return c.Environment == "development"
}

// Addr returns the full ":PORT" listen address.
func (c *Config) Addr() string {
	return fmt.Sprintf(":%s", c.Port)
}

// ─── helpers ────────────────────────────────────────────────────────────────

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func mustGetEnv(key string) string {
	v := os.Getenv(key)
	if v == "" {
		log.Fatalf("[config] required environment variable %q is not set", key)
	}
	return v
}
