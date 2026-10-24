package journal

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strconv"

	"github.com/go-chi/chi/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sadguruchenu/thoughtsgo/internal/config"
	"github.com/sadguruchenu/thoughtsgo/internal/middleware"
	"github.com/sadguruchenu/thoughtsgo/internal/models"
	"github.com/sadguruchenu/thoughtsgo/internal/service"
)

type Handler struct {
	cfg  *config.Config
	pool *pgxpool.Pool
	svc  *service.JournalService
}

func NewHandler(cfg *config.Config, pool *pgxpool.Pool, svc *service.JournalService) *Handler {
	return &Handler{cfg: cfg, pool: pool, svc: svc}
}

// JournalsRouter handles /api/v1/journals
func (h *Handler) JournalsRouter() chi.Router {
	r := chi.NewRouter()
	r.Use(middleware.RequireAuth(h.cfg.SecretKey, h.pool))
	r.Get("/", h.getJournals)
	r.Post("/", h.createJournal)
	r.Get("/{uuid}", h.getJournalDetail)
	r.Patch("/{uuid}", h.updateJournal)
	r.Delete("/{uuid}", h.deleteJournal)
	return r
}

// JournalRouter handles /api/v1/journal
func (h *Handler) JournalRouter() chi.Router {
	r := chi.NewRouter()
	r.Use(middleware.RequireAuth(h.cfg.SecretKey, h.pool))
	r.Post("/", h.createJournal)
	r.Get("/structure/latest", h.getLatestStructure)
	r.Get("/analytics", h.getAnalytics)
	r.Get("/{uuid}", h.getJournalDetail)
	r.Patch("/{uuid}", h.updateJournal)
	r.Delete("/{uuid}", h.deleteJournal)
	return r
}

// TemplatesRouter handles /api/v1/templates
func (h *Handler) TemplatesRouter() chi.Router {
	r := chi.NewRouter()
	r.Use(middleware.RequireAuth(h.cfg.SecretKey, h.pool))
	r.Get("/", h.getTemplates)
	r.Delete("/{uuid}", h.deleteTemplate)
	return r
}

func (h *Handler) getJournals(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		http.Error(w, `{"detail":"Unauthorized"}`, http.StatusUnauthorized)
		return
	}

	page := 1
	if p, err := strconv.Atoi(r.URL.Query().Get("page")); err == nil && p > 0 {
		page = p
	}

	perPage := 20
	if pp, err := strconv.Atoi(r.URL.Query().Get("per_page")); err == nil && pp > 0 {
		perPage = pp
	}

	search := r.URL.Query().Get("search")
	sortOrder := r.URL.Query().Get("sort_order")
	dateFilter := r.URL.Query().Get("date_filter")

	res, err := h.svc.GetJournals(r.Context(), user.ID, page, perPage, search, sortOrder, dateFilter)
	if err != nil {
		http.Error(w, `{"detail":"Failed to fetch journals"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(res)
}

func (h *Handler) getJournalDetail(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		http.Error(w, `{"detail":"Unauthorized"}`, http.StatusUnauthorized)
		return
	}

	journalUUID := chi.URLParam(r, "uuid")
	res, err := h.svc.GetJournalDetail(r.Context(), user.ID, journalUUID)
	if err != nil {
		if errors.Is(err, service.ErrJournalNotFound) {
			http.Error(w, `{"detail":"Journal not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, `{"detail":"Failed to get journal"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(res)
}

func (h *Handler) getLatestStructure(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		http.Error(w, `{"detail":"Unauthorized"}`, http.StatusUnauthorized)
		return
	}

	res, err := h.svc.GetLatestJournalStructure(r.Context(), user.ID)
	if err != nil {
		http.Error(w, `{"detail":"Failed to get latest structure"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(res)
}

func (h *Handler) getAnalytics(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		http.Error(w, `{"detail":"Unauthorized"}`, http.StatusUnauthorized)
		return
	}

	res, err := h.svc.GetJournalAnalytics(r.Context(), user.ID)
	if err != nil {
		http.Error(w, `{"detail":"Failed to get analytics"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(res)
}

func (h *Handler) getTemplates(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		http.Error(w, `{"detail":"Unauthorized"}`, http.StatusUnauthorized)
		return
	}

	res, err := h.svc.GetTemplates(r.Context(), user.ID)
	if err != nil {
		http.Error(w, `{"detail":"Failed to get templates"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(res)
}

func (h *Handler) deleteTemplate(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		http.Error(w, `{"detail":"Unauthorized"}`, http.StatusUnauthorized)
		return
	}

	templateUUID := chi.URLParam(r, "uuid")
	err := h.svc.DeleteTemplate(r.Context(), user.ID, templateUUID)
	if err != nil {
		if errors.Is(err, service.ErrTemplateNotFound) {
			http.Error(w, `{"detail":"Template not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, `{"detail":"Failed to delete template"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]string{"message": "Template marked as inactive"})
}

func (h *Handler) createJournal(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		http.Error(w, `{"detail":"Unauthorized"}`, http.StatusUnauthorized)
		return
	}

	var req models.JournalCreate
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		fmt.Printf("[createJournal] decode error: %v\n", err)
		http.Error(w, fmt.Sprintf(`{"detail":"Invalid request body: %s"}`, err.Error()), http.StatusBadRequest)
		return
	}

	res, err := h.svc.CreateJournal(r.Context(), user.ID, req)
	if err != nil {
		fmt.Printf("[createJournal] service error: %v\n", err)
		if errors.Is(err, service.ErrInvalidInput) {
			http.Error(w, fmt.Sprintf(`{"detail":"%s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		http.Error(w, fmt.Sprintf(`{"detail":"Failed to create journal: %s"}`, err.Error()), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(res)
}

func (h *Handler) updateJournal(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		http.Error(w, `{"detail":"Unauthorized"}`, http.StatusUnauthorized)
		return
	}

	journalUUID := chi.URLParam(r, "uuid")
	var req models.JournalUpdate
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"detail":"Invalid request body"}`, http.StatusBadRequest)
		return
	}

	err := h.svc.UpdateJournal(r.Context(), user.ID, journalUUID, req)
	if err != nil {
		if errors.Is(err, service.ErrJournalNotFound) {
			http.Error(w, `{"detail":"Journal not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, `{"detail":"Failed to update journal"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]string{"message": "Journal updated successfully"})
}

func (h *Handler) deleteJournal(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		http.Error(w, `{"detail":"Unauthorized"}`, http.StatusUnauthorized)
		return
	}

	journalUUID := chi.URLParam(r, "uuid")
	err := h.svc.DeleteJournal(r.Context(), user.ID, journalUUID)
	if err != nil {
		if errors.Is(err, service.ErrJournalNotFound) {
			http.Error(w, `{"detail":"Journal not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, `{"detail":"Failed to delete journal"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]string{"message": "Deleted successfully"})
}
