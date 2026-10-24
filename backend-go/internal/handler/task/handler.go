package task

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

// Router returns a chi.Router mounting all task endpoints.
func (h *Handler) Router() chi.Router {
	r := chi.NewRouter()

	// Authentication required for all task operations
	r.Use(middleware.RequireAuth(h.cfg.SecretKey, h.pool))

	r.Get("/", h.ReadTasks)
	r.Post("/", h.AddTask)
	r.Get("/{uuid}", h.ReadTask)
	r.Patch("/{uuid}", h.EditTask)
	r.Delete("/{uuid}", h.RemoveTask)
	r.Patch("/{uuid}/complete", h.MarkComplete)
	r.Patch("/{uuid}/uncomplete", h.MarkUncomplete)
	r.Patch("/{uuid}/archive", h.Archive)

	return r
}

// 1. GET /tasks
func (h *Handler) ReadTasks(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	q := r.URL.Query()

	var status *models.TaskStatus
	if s := q.Get("status"); s != "" {
		st := models.TaskStatus(s)
		status = &st
	}

	var priority *models.TaskPriority
	if p := q.Get("priority"); p != "" {
		pr := models.TaskPriority(p)
		priority = &pr
	}

	var completed *bool
	if c := q.Get("completed"); c != "" {
		b, err := strconv.ParseBool(c)
		if err == nil {
			completed = &b
		}
	}

	today, _ := strconv.ParseBool(q.Get("today"))
	overdue, _ := strconv.ParseBool(q.Get("overdue"))
	archived, _ := strconv.ParseBool(q.Get("archived"))
	search := q.Get("search")

	page, _ := strconv.Atoi(q.Get("page"))
	perPage, _ := strconv.Atoi(q.Get("per_page"))

	params := service.TaskFilterParams{
		Status:    status,
		Priority:  priority,
		Completed: completed,
		Today:     today,
		Overdue:   overdue,
		Search:    search,
		Archived:  archived,
		Page:      page,
		PerPage:   perPage,
	}

	resp, err := service.GetTasks(r.Context(), h.pool, user, params)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to fetch tasks: "+err.Error())
		return
	}

	middleware.RespondJSON(w, http.StatusOK, resp)
}

// 2. GET /tasks/{uuid}
func (h *Handler) ReadTask(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	uuidStr := chi.URLParam(r, "uuid")
	taskUUID, err := uuid.Parse(uuidStr)
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid task UUID")
		return
	}

	task, err := service.GetTaskByUUID(r.Context(), h.pool, user, taskUUID)
	if err != nil {
		if err == service.ErrTaskNotFound {
			detail := fmt.Sprintf("Task with uuid %s not found.", uuidStr)
			middleware.RespondError(w, http.StatusNotFound, detail)
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to retrieve task")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, task)
}

// 3. POST /tasks
func (h *Handler) AddTask(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	var payload models.TaskCreate
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	task, err := service.CreateTask(r.Context(), h.pool, user, payload)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to create task: "+err.Error())
		return
	}

	middleware.RespondJSON(w, http.StatusOK, task)
}

// 4. PATCH /tasks/{uuid}
func (h *Handler) EditTask(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	uuidStr := chi.URLParam(r, "uuid")
	taskUUID, err := uuid.Parse(uuidStr)
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid task UUID")
		return
	}

	var payload models.TaskUpdate
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	updated, err := service.UpdateTask(r.Context(), h.pool, user, taskUUID, payload)
	if err != nil {
		if err == service.ErrTaskNotFound {
			detail := fmt.Sprintf("Task with uuid %s not found.", uuidStr)
			middleware.RespondError(w, http.StatusNotFound, detail)
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to update task: "+err.Error())
		return
	}

	middleware.RespondJSON(w, http.StatusOK, map[string]interface{}{
		"message": "Task updated successfully.",
		"task":    updated,
	})
}

// 5. DELETE /tasks/{uuid}
func (h *Handler) RemoveTask(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	uuidStr := chi.URLParam(r, "uuid")
	taskUUID, err := uuid.Parse(uuidStr)
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid task UUID")
		return
	}

	if err := service.DeleteTask(r.Context(), h.pool, user, taskUUID); err != nil {
		if err == service.ErrTaskNotFound {
			detail := fmt.Sprintf("Task with uuid %s not found.", uuidStr)
			middleware.RespondError(w, http.StatusNotFound, detail)
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to delete task")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, map[string]string{
		"message": "Task deleted successfully.",
	})
}

// 6. PATCH /tasks/{uuid}/complete
func (h *Handler) MarkComplete(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	uuidStr := chi.URLParam(r, "uuid")
	taskUUID, err := uuid.Parse(uuidStr)
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid task UUID")
		return
	}

	task, err := service.CompleteTask(r.Context(), h.pool, user, taskUUID)
	if err != nil {
		if err == service.ErrTaskNotFound {
			detail := fmt.Sprintf("Task with uuid %s not found.", uuidStr)
			middleware.RespondError(w, http.StatusNotFound, detail)
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to complete task: "+err.Error())
		return
	}

	middleware.RespondJSON(w, http.StatusOK, task)
}

// 7. PATCH /tasks/{uuid}/uncomplete
func (h *Handler) MarkUncomplete(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	uuidStr := chi.URLParam(r, "uuid")
	taskUUID, err := uuid.Parse(uuidStr)
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid task UUID")
		return
	}

	task, err := service.UncompleteTask(r.Context(), h.pool, user, taskUUID)
	if err != nil {
		if err == service.ErrTaskNotFound {
			detail := fmt.Sprintf("Task with uuid %s not found.", uuidStr)
			middleware.RespondError(w, http.StatusNotFound, detail)
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to uncomplete task: "+err.Error())
		return
	}

	middleware.RespondJSON(w, http.StatusOK, task)
}

// 8. PATCH /tasks/{uuid}/archive
func (h *Handler) Archive(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	uuidStr := chi.URLParam(r, "uuid")
	taskUUID, err := uuid.Parse(uuidStr)
	if err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid task UUID")
		return
	}

	task, err := service.ArchiveTask(r.Context(), h.pool, user, taskUUID)
	if err != nil {
		if err == service.ErrTaskNotFound {
			detail := fmt.Sprintf("Task with uuid %s not found.", uuidStr)
			middleware.RespondError(w, http.StatusNotFound, detail)
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to archive task: "+err.Error())
		return
	}

	middleware.RespondJSON(w, http.StatusOK, task)
}
