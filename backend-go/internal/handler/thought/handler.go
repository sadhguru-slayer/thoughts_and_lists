package thought

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sadguruchenu/thoughtsgo/internal/config"
	"github.com/sadguruchenu/thoughtsgo/internal/middleware"
	"github.com/sadguruchenu/thoughtsgo/internal/models"
	"github.com/sadguruchenu/thoughtsgo/internal/service"
)

type Handler struct {
	cfg  *config.Config
	pool *pgxpool.Pool
}

func NewHandler(cfg *config.Config, pool *pgxpool.Pool) *Handler {
	return &Handler{
		cfg:  cfg,
		pool: pool,
	}
}

// Router returns a chi.Router with all thought endpoints mounted.
func (h *Handler) Router() chi.Router {
	r := chi.NewRouter()

	// All thoughts endpoints require authentication
	r.Use(middleware.RequireAuth(h.cfg.SecretKey, h.pool))

	r.Get("/", h.ReadThoughts)
	r.Post("/", h.AddThought)
	r.Post("/bulk-delete", h.BulkDelete)
	r.Post("/update-order", h.UpdateThoughtOrders)
	r.Get("/{uuid}", h.ReadThought)
	r.Patch("/{uuid}", h.UpdateThought)
	r.Delete("/{uuid}", h.RemoveThought)
	r.Post("/{uuid}/move-to-notebook", h.MoveThoughtToNotebook)

	return r
}

// 1. GET /thoughts
func (h *Handler) ReadThoughts(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	search := r.URL.Query().Get("search")
	page, _ := strconv.Atoi(r.URL.Query().Get("page"))
	perPage, _ := strconv.Atoi(r.URL.Query().Get("per_page"))

	resp, err := service.GetThoughts(r.Context(), h.pool, user, search, page, perPage)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to retrieve thoughts: "+err.Error())
		return
	}

	middleware.RespondJSON(w, http.StatusOK, resp)
}

// 2. GET /thoughts/{uuid}
func (h *Handler) ReadThought(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	uuidStr := chi.URLParam(r, "uuid")
	thoughtUUID, err := uuid.Parse(uuidStr)
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid thought UUID")
		return
	}

	thought, err := service.GetThoughtByUUID(r.Context(), h.pool, user, thoughtUUID)
	if err != nil {
		if err == service.ErrThoughtNotFound {
			detail := fmt.Sprintf("Thought with uuid %s not found or you do not have permission to view it.", uuidStr)
			middleware.RespondError(w, http.StatusNotFound, detail)
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to fetch thought")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, thought)
}

// 3. POST /thoughts
func (h *Handler) AddThought(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	var payload models.ThoughtCreate
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	thought, err := service.CreateThought(r.Context(), h.pool, user, payload)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to create thought: "+err.Error())
		return
	}

	middleware.RespondJSON(w, http.StatusOK, thought)
}

// 4. PATCH /thoughts/{uuid}
func (h *Handler) UpdateThought(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	uuidStr := chi.URLParam(r, "uuid")
	thoughtUUID, err := uuid.Parse(uuidStr)
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid thought UUID")
		return
	}

	var payload models.ThoughtUpdate
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	updated, err := service.UpdateThought(r.Context(), h.pool, user, thoughtUUID, payload)
	if err != nil {
		if err == service.ErrThoughtNotFound {
			detail := fmt.Sprintf("Thought with uuid %s not found or you do not have permission to update it.", uuidStr)
			middleware.RespondError(w, http.StatusNotFound, detail)
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to update thought: "+err.Error())
		return
	}

	middleware.RespondJSON(w, http.StatusOK, map[string]interface{}{
		"message": "Thought updated successfully",
		"thought": updated,
	})
}

// 5. DELETE /thoughts/{uuid}
func (h *Handler) RemoveThought(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	uuidStr := chi.URLParam(r, "uuid")
	thoughtUUID, err := uuid.Parse(uuidStr)
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid thought UUID")
		return
	}

	if err := service.DeleteThought(r.Context(), h.pool, user, thoughtUUID); err != nil {
		if err == service.ErrThoughtNotFound {
			detail := fmt.Sprintf("Thought with uuid %s not found or you do not have permission to delete it.", uuidStr)
			middleware.RespondError(w, http.StatusNotFound, detail)
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to delete thought")
		return
	}

	detail := fmt.Sprintf("Thought with uuid %s deleted successfully.", uuidStr)
	middleware.RespondJSON(w, http.StatusOK, map[string]string{
		"message": detail,
	})
}

// 6. POST /thoughts/bulk-delete
func (h *Handler) BulkDelete(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	var payload models.BulkDeleteThoughts
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	count, err := service.BulkDeleteThoughts(r.Context(), h.pool, user, payload.UUIDs)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to bulk delete thoughts")
		return
	}

	detail := fmt.Sprintf("%d thought(s) deleted successfully.", count)
	middleware.RespondJSON(w, http.StatusOK, map[string]string{
		"message": detail,
	})
}

// 7. POST /thoughts/update-order
func (h *Handler) UpdateThoughtOrders(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	var payload models.BulkThoughtOrderUpdate
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	if err := service.UpdateThoughtOrders(r.Context(), h.pool, user, payload.Orders); err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to update thought orders")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, map[string]string{
		"message": "Thought orders updated successfully",
	})
}

// 8. POST /thoughts/{uuid}/move-to-notebook
func (h *Handler) MoveThoughtToNotebook(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	uuidStr := chi.URLParam(r, "uuid")
	thoughtUUID, err := uuid.Parse(uuidStr)
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid thought UUID")
		return
	}

	var payload models.MoveThoughtRequest
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	resp, err := service.MoveThoughtToNotebook(r.Context(), h.pool, user, thoughtUUID, payload.TargetNotebookUUID)
	if err != nil {
		if err == service.ErrThoughtNotFound {
			middleware.RespondError(w, http.StatusNotFound, "Thought not found")
			return
		}
		if err == service.ErrNotebookNotFound {
			middleware.RespondError(w, http.StatusNotFound, "Target notebook not found")
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to move thought: "+err.Error())
		return
	}

	middleware.RespondJSON(w, http.StatusOK, resp)
}
