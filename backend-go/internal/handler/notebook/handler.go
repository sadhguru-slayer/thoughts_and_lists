package notebook

import (
	"encoding/json"
	"net/http"

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

// NotebookRouter returns routes for /api/v1/notebooks.
func (h *Handler) NotebookRouter() chi.Router {
	r := chi.NewRouter()
	r.Use(middleware.RequireAuth(h.cfg.SecretKey, h.pool))

	r.Get("/", h.GetNotebooks)
	r.Post("/", h.CreateNotebook)
	r.Get("/{uuid}", h.GetNotebook)
	r.Put("/{uuid}", h.UpdateNotebook)
	r.Delete("/{uuid}", h.DeleteNotebook)
	r.Post("/{notebook_uuid}/notes", h.CreateNote)

	return r
}

// NoteRouter returns routes for /api/v1/notes.
func (h *Handler) NoteRouter() chi.Router {
	r := chi.NewRouter()
	r.Use(middleware.RequireAuth(h.cfg.SecretKey, h.pool))

	r.Get("/{uuid}", h.GetNote)
	r.Put("/{uuid}", h.UpdateNote)
	r.Delete("/{uuid}", h.DeleteNote)
	r.Post("/{uuid}/move", h.MoveNote)

	return r
}

// 1. GET /notebooks
func (h *Handler) GetNotebooks(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	notebooks, err := service.GetNotebooks(r.Context(), h.pool, user)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to fetch notebooks: "+err.Error())
		return
	}

	middleware.RespondJSON(w, http.StatusOK, notebooks)
}

// 2. POST /notebooks
func (h *Handler) CreateNotebook(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	var payload models.NotebookCreate
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	nb, err := service.CreateNotebook(r.Context(), h.pool, user, payload)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to create notebook: "+err.Error())
		return
	}

	middleware.RespondJSON(w, http.StatusCreated, nb)
}

// 3. GET /notebooks/{uuid}
func (h *Handler) GetNotebook(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	nbUUID, err := uuid.Parse(chi.URLParam(r, "uuid"))
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid notebook UUID")
		return
	}

	nb, err := service.GetNotebookByUUID(r.Context(), h.pool, user, nbUUID)
	if err != nil {
		if err == service.ErrNotebookNotFound {
			middleware.RespondError(w, http.StatusNotFound, "Notebook not found")
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to retrieve notebook")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, nb)
}

// 4. PUT /notebooks/{uuid}
func (h *Handler) UpdateNotebook(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	nbUUID, err := uuid.Parse(chi.URLParam(r, "uuid"))
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid notebook UUID")
		return
	}

	var payload models.NotebookUpdate
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	nb, err := service.UpdateNotebook(r.Context(), h.pool, user, nbUUID, payload)
	if err != nil {
		if err == service.ErrNotebookNotFound {
			middleware.RespondError(w, http.StatusNotFound, "Notebook not found")
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to update notebook")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, nb)
}

// 5. DELETE /notebooks/{uuid}
func (h *Handler) DeleteNotebook(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	nbUUID, err := uuid.Parse(chi.URLParam(r, "uuid"))
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid notebook UUID")
		return
	}

	if err := service.DeleteNotebook(r.Context(), h.pool, user, nbUUID); err != nil {
		if err == service.ErrNotebookNotFound {
			middleware.RespondError(w, http.StatusNotFound, "Notebook not found")
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to delete notebook")
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

// 6. POST /notebooks/{notebook_uuid}/notes
func (h *Handler) CreateNote(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	nbUUID, err := uuid.Parse(chi.URLParam(r, "notebook_uuid"))
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid notebook UUID")
		return
	}

	var payload models.NoteCreate
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	note, err := service.CreateNote(r.Context(), h.pool, user, nbUUID, payload)
	if err != nil {
		if err == service.ErrNotebookNotFound {
			middleware.RespondError(w, http.StatusNotFound, "Notebook not found")
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to create note: "+err.Error())
		return
	}

	middleware.RespondJSON(w, http.StatusCreated, note)
}

// 7. GET /notes/{uuid}
func (h *Handler) GetNote(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	noteUUID, err := uuid.Parse(chi.URLParam(r, "uuid"))
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid note UUID")
		return
	}

	note, err := service.GetNoteByUUID(r.Context(), h.pool, user, noteUUID)
	if err != nil {
		if err == service.ErrNoteNotFound {
			middleware.RespondError(w, http.StatusNotFound, "Note not found")
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to fetch note")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, note)
}

// 8. PUT /notes/{uuid}
func (h *Handler) UpdateNote(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	noteUUID, err := uuid.Parse(chi.URLParam(r, "uuid"))
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid note UUID")
		return
	}

	var payload models.NoteUpdate
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	note, err := service.UpdateNote(r.Context(), h.pool, user, noteUUID, payload)
	if err != nil {
		if err == service.ErrNoteNotFound {
			middleware.RespondError(w, http.StatusNotFound, "Note not found")
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to update note")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, note)
}

// 9. DELETE /notes/{uuid}
func (h *Handler) DeleteNote(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	noteUUID, err := uuid.Parse(chi.URLParam(r, "uuid"))
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid note UUID")
		return
	}

	if err := service.DeleteNote(r.Context(), h.pool, user, noteUUID); err != nil {
		if err == service.ErrNoteNotFound {
			middleware.RespondError(w, http.StatusNotFound, "Note not found")
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to delete note")
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

// 10. POST /notes/{uuid}/move
func (h *Handler) MoveNote(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	noteUUID, err := uuid.Parse(chi.URLParam(r, "uuid"))
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid note UUID")
		return
	}

	var payload models.MoveNoteRequest
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	resp, err := service.MoveNote(r.Context(), h.pool, user, noteUUID, payload.TargetNotebookUUID)
	if err != nil {
		if err == service.ErrNoteNotFound {
			middleware.RespondError(w, http.StatusNotFound, "Note not found")
			return
		}
		if err == service.ErrNotebookNotFound {
			middleware.RespondError(w, http.StatusNotFound, "Target notebook not found")
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to move note: "+err.Error())
		return
	}

	middleware.RespondJSON(w, http.StatusOK, resp)
}
