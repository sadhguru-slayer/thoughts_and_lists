package dashboard

import (
	"encoding/json"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sadguruchenu/thoughtsgo/internal/config"
	"github.com/sadguruchenu/thoughtsgo/internal/middleware"
	"github.com/sadguruchenu/thoughtsgo/internal/service"
)

type Handler struct {
	cfg  *config.Config
	pool *pgxpool.Pool
	svc  *service.DashboardService
}

func NewHandler(cfg *config.Config, pool *pgxpool.Pool, svc *service.DashboardService) *Handler {
	return &Handler{cfg: cfg, pool: pool, svc: svc}
}

func (h *Handler) Router() chi.Router {
	r := chi.NewRouter()
	r.Use(middleware.RequireAuth(h.cfg.SecretKey, h.pool))
	r.Get("/", h.getDashboard)
	return r
}

func (h *Handler) getDashboard(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		http.Error(w, `{"detail":"Unauthorized"}`, http.StatusUnauthorized)
		return
	}

	data, err := h.svc.GetDashboardData(r.Context(), user.ID)
	if err != nil {
		http.Error(w, `{"detail":"Failed to get dashboard data"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(data)
}
