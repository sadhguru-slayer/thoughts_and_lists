package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
	_ "time/tzdata"

	"github.com/go-chi/chi/v5"
	chimiddleware "github.com/go-chi/chi/v5/middleware"

	"github.com/sadguruchenu/thoughtsgo/internal/config"
	"github.com/sadguruchenu/thoughtsgo/internal/db"
	"github.com/sadguruchenu/thoughtsgo/internal/handler/auth"
	"github.com/sadguruchenu/thoughtsgo/internal/handler/dashboard"
	"github.com/sadguruchenu/thoughtsgo/internal/handler/health"
	"github.com/sadguruchenu/thoughtsgo/internal/handler/journal"
	"github.com/sadguruchenu/thoughtsgo/internal/handler/notebook"
	"github.com/sadguruchenu/thoughtsgo/internal/handler/task"
	"github.com/sadguruchenu/thoughtsgo/internal/handler/thought"
	"github.com/sadguruchenu/thoughtsgo/internal/middleware"
	"github.com/sadguruchenu/thoughtsgo/internal/scheduler"
	"github.com/sadguruchenu/thoughtsgo/internal/service"
)

func main() {
	// ── 1. Load config ───────────────────────────────────────────────────────
	cfg := config.Load()
	log.Printf("[main] environment=%s  addr=%s", cfg.Environment, cfg.Addr())

	// ── 2. Connect to Postgres & Redis ───────────────────────────────────────
	ctx := context.Background()

	pool, err := db.NewPool(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("[main] postgres: %v", err)
	}
	defer pool.Close()

	rdb, err := db.NewRedis(ctx, cfg.RedisURL)
	if err != nil {
		log.Fatalf("[main] redis: %v", err)
	}
	defer rdb.Close()

	// ── 3. Build router ───────────────────────────────────────────────────────
	r := chi.NewRouter()

	// Built-in chi middleware
	r.Use(chimiddleware.RequestID) // adds X-Request-Id header
	r.Use(chimiddleware.RealIP)    // reads X-Real-IP / X-Forwarded-For
	r.Use(chimiddleware.Logger)    // structured request log (like uvicorn access log)
	r.Use(chimiddleware.Recoverer) // catches panics → 500 instead of crash

	// CORS – mirrors FastAPI CORSMiddleware
	allowedOrigins := []string{cfg.FrontendURL, cfg.FrontendURL2}
	if cfg.IsDevelopment() {
		allowedOrigins = append(allowedOrigins,
			"http://localhost:3000",
			"http://127.0.0.1:3000",
		)
	}
	r.Use(middleware.CORS(allowedOrigins))

	// ── 4. Routes ─────────────────────────────────────────────────────────────

	// Services
	emailService := service.NewEmailService(cfg)
	journalService := service.NewJournalService(pool)
	dashboardService := service.NewDashboardService(pool)

	// Background reminder scheduler (Task reminders + Daily Journal reminders)
	sched := scheduler.New(pool, emailService)
	sched.Start()
	defer sched.Stop()

	// Handlers
	authHandler := auth.NewHandler(cfg, pool, rdb, emailService)
	thoughtHandler := thought.NewHandler(cfg, pool)
	taskHandler := task.NewHandler(cfg, pool)
	notebookHandler := notebook.NewHandler(cfg, pool)
	journalHandler := journal.NewHandler(cfg, pool, journalService)
	dashboardHandler := dashboard.NewHandler(cfg, pool, dashboardService)

	// Health check (used by Docker HEALTHCHECK and monitoring)
	r.Get("/health", health.Handler(pool, rdb))

	// API v1 routes
	r.Route("/api/v1", func(api chi.Router) {
		api.Mount("/auth", authHandler.Router())
		api.Mount("/thoughts", thoughtHandler.Router())
		api.Mount("/tasks", taskHandler.Router())
		api.Mount("/notebooks", notebookHandler.NotebookRouter())
		api.Mount("/notes", notebookHandler.NoteRouter())
		api.Mount("/journals", journalHandler.JournalsRouter())
		api.Mount("/journal", journalHandler.JournalRouter())
		api.Mount("/templates", journalHandler.TemplatesRouter())
		api.Mount("/dashboard", dashboardHandler.Router())
	})

	// ── 5. HTTP server with graceful shutdown ─────────────────────────────────
	srv := &http.Server{
		Addr:         cfg.Addr(),
		Handler:      r,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Start server in a goroutine so we can listen for OS signals.
	go func() {
		log.Printf("[main] server listening on %s", cfg.Addr())
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("[main] server error: %v", err)
		}
	}()

	// Block until SIGINT or SIGTERM (docker stop sends SIGTERM)
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("[main] shutting down gracefully…")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Printf("[main] shutdown error: %v", err)
	}

	log.Println("[main] server stopped")
}
