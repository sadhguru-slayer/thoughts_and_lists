package service

import (
	"context"
	"errors"
	"fmt"
	"math"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sadguruchenu/thoughtsgo/internal/models"
)

var (
	ErrTaskNotFound = errors.New("task not found")
)

// TaskFilterParams represents the query filter options for GET /tasks.
type TaskFilterParams struct {
	Status    *models.TaskStatus
	Priority  *models.TaskPriority
	Completed *bool
	Today     bool
	Overdue   bool
	Search    string
	Archived  bool
	Page      int
	PerPage   int
}

// addMonth correctly adds 1 calendar month, clipping to the month's maximum day (like Python's relativedelta).
func addMonth(t time.Time) time.Time {
	year, month, day := t.Date()
	targetMonth := month + 1
	targetYear := year
	if targetMonth > 12 {
		targetMonth = 1
		targetYear++
	}

	// Determine the last day of targetMonth
	firstOfNext := time.Date(targetYear, targetMonth+1, 1, 0, 0, 0, 0, t.Location())
	lastDayOfTarget := firstOfNext.AddDate(0, 0, -1).Day()

	targetDay := day
	if targetDay > lastDayOfTarget {
		targetDay = lastDayOfTarget
	}

	return time.Date(targetYear, targetMonth, targetDay, t.Hour(), t.Minute(), t.Second(), t.Nanosecond(), t.Location())
}

// GetTasks fetches a smart-sorted and filtered list of tasks for the user.
func GetTasks(
	ctx context.Context,
	pool *pgxpool.Pool,
	user *models.User,
	params TaskFilterParams,
) (models.PaginatedResponse[models.TaskSummary], error) {
	if params.Page < 1 {
		params.Page = 1
	}
	if params.PerPage < 1 || params.PerPage > 100 {
		params.PerPage = 20
	}

	var where []string
	var args []interface{}
	argID := 1

	where = append(where, fmt.Sprintf("user_id = $%d", argID))
	args = append(args, user.ID)
	argID++

	where = append(where, fmt.Sprintf("is_archived = $%d", argID))
	args = append(args, params.Archived)
	argID++

	if params.Status != nil {
		where = append(where, fmt.Sprintf("status = $%d", argID))
		args = append(args, string(*params.Status))
		argID++
	}

	if params.Priority != nil {
		where = append(where, fmt.Sprintf("priority = $%d", argID))
		args = append(args, string(*params.Priority))
		argID++
	}

	if params.Completed != nil {
		if *params.Completed {
			where = append(where, fmt.Sprintf("status = $%d", argID))
			args = append(args, string(models.StatusCompleted))
			argID++
		} else {
			where = append(where, fmt.Sprintf("status != $%d", argID))
			args = append(args, string(models.StatusCompleted))
			argID++
		}
	}

	nowUTC := time.Now().UTC()

	if params.Today {
		todayStart := time.Date(nowUTC.Year(), nowUTC.Month(), nowUTC.Day(), 0, 0, 0, 0, time.UTC)
		todayEnd := todayStart.Add(24 * time.Hour)
		where = append(where, fmt.Sprintf("due_date IS NOT NULL AND due_date >= $%d AND due_date < $%d", argID, argID+1))
		args = append(args, todayStart, todayEnd)
		argID += 2
	}

	if params.Overdue {
		where = append(where, fmt.Sprintf("due_date IS NOT NULL AND due_date < $%d AND status != $%d", argID, argID+1))
		args = append(args, nowUTC, string(models.StatusCompleted))
		argID += 2
	}

	if params.Search != "" {
		where = append(where, fmt.Sprintf("(title ILIKE $%d OR COALESCE(description, '') ILIKE $%d)", argID, argID))
		args = append(args, "%"+params.Search+"%")
		argID++
	}

	whereClause := strings.Join(where, " AND ")

	// 1. Count query
	countQuery := fmt.Sprintf("SELECT COUNT(*) FROM tasks WHERE %s", whereClause)
	var total int
	if err := pool.QueryRow(ctx, countQuery, args...).Scan(&total); err != nil {
		return models.PaginatedResponse[models.TaskSummary]{}, fmt.Errorf("count tasks: %w", err)
	}

	totalPages := 1
	if params.PerPage > 0 {
		totalPages = int(math.Ceil(float64(total) / float64(params.PerPage)))
	}
	if totalPages == 0 {
		totalPages = 1
	}

	// 2. Select query with smart sort
	selectQuery := fmt.Sprintf(`
		SELECT uuid, title, status, priority, completed, due_date, created_at, recurrence_interval
		FROM tasks
		WHERE %s
		ORDER BY 
			CASE 
				WHEN status IN ('COMPLETED', 'CANCELLED') THEN 2
				WHEN due_date IS NULL THEN 1
				ELSE 0
			END ASC,
			due_date ASC NULLS LAST,
			created_at DESC
		OFFSET $%d LIMIT $%d
	`, whereClause, argID, argID+1)

	offset := (params.Page - 1) * params.PerPage
	args = append(args, offset, params.PerPage)

	rows, err := pool.Query(ctx, selectQuery, args...)
	if err != nil {
		return models.PaginatedResponse[models.TaskSummary]{}, fmt.Errorf("select tasks: %w", err)
	}
	defer rows.Close()

	items := make([]models.TaskSummary, 0)
	for rows.Next() {
		var item models.TaskSummary
		var statusStr, priorityStr, recurStr string
		err := rows.Scan(
			&item.UUID,
			&item.Title,
			&statusStr,
			&priorityStr,
			&item.Completed,
			&item.DueDate,
			&item.CreatedAt,
			&recurStr,
		)
		if err != nil {
			return models.PaginatedResponse[models.TaskSummary]{}, fmt.Errorf("scan task summary: %w", err)
		}
		item.Status = models.TaskStatus(statusStr)
		item.Priority = models.TaskPriority(priorityStr)
		item.RecurrenceInterval = models.TaskRecurrence(recurStr)
		items = append(items, item)
	}

	return models.PaginatedResponse[models.TaskSummary]{
		Items:      items,
		Total:      total,
		Page:       params.Page,
		PerPage:    params.PerPage,
		TotalPages: totalPages,
	}, nil
}

// GetTaskByUUID fetches a full task record.
func GetTaskByUUID(ctx context.Context, pool *pgxpool.Pool, user *models.User, taskUUID uuid.UUID) (*models.TaskDetail, error) {
	query := `
		SELECT uuid, title, description, status, priority, completed,
		       due_date, reminder_at, completed_at, recurrence_interval,
		       position, is_archived, created_at, updated_at, user_id
		FROM tasks
		WHERE uuid = $1 AND user_id = $2
		LIMIT 1
	`
	var t models.TaskDetail
	var statusStr, priorityStr, recurStr string
	err := pool.QueryRow(ctx, query, taskUUID, user.ID).Scan(
		&t.UUID, &t.Title, &t.Description, &statusStr, &priorityStr, &t.Completed,
		&t.DueDate, &t.ReminderAt, &t.CompletedAt, &recurStr,
		&t.Position, &t.IsArchived, &t.CreatedAt, &t.UpdatedAt, &t.UserID,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrTaskNotFound
		}
		return nil, err
	}
	t.Status = models.TaskStatus(statusStr)
	t.Priority = models.TaskPriority(priorityStr)
	t.RecurrenceInterval = models.TaskRecurrence(recurStr)
	return &t, nil
}

// CreateTask adds a new task.
func CreateTask(ctx context.Context, pool *pgxpool.Pool, user *models.User, payload models.TaskCreate) (*models.TaskDetail, error) {
	newUUID, err := uuid.NewV7()
	if err != nil {
		newUUID = uuid.New()
	}

	priority := models.PriorityMedium
	if payload.Priority != nil {
		priority = *payload.Priority
	}

	recurrence := models.RecurrenceNone
	if payload.RecurrenceInterval != nil {
		recurrence = *payload.RecurrenceInterval
	}

	var dueDate *time.Time
	if payload.DueDate != nil {
		t := payload.DueDate.Time
		dueDate = &t
	}
	var reminderAt *time.Time
	if payload.ReminderAt != nil {
		t := payload.ReminderAt.Time
		reminderAt = &t
	} else {
		reminderAt = dueDate
	}

	query := `
		INSERT INTO tasks (uuid, user_id, title, description, status, completed, priority, due_date, reminder_at, reminder_sent, recurrence_interval, position, is_archived, created_at, updated_at)
		VALUES ($1, $2, $3, $4, 'TODO', false, $5, $6, $7, false, $8, 0, false, NOW(), NOW())
		RETURNING uuid, title, description, status, priority, completed, due_date, reminder_at, completed_at, recurrence_interval, position, is_archived, created_at, updated_at, user_id
	`
	var t models.TaskDetail
	var statusStr, priorityStr, recurStr string
	err = pool.QueryRow(ctx, query, newUUID, user.ID, payload.Title, payload.Description, string(priority), dueDate, reminderAt, string(recurrence)).Scan(
		&t.UUID, &t.Title, &t.Description, &statusStr, &priorityStr, &t.Completed,
		&t.DueDate, &t.ReminderAt, &t.CompletedAt, &recurStr,
		&t.Position, &t.IsArchived, &t.CreatedAt, &t.UpdatedAt, &t.UserID,
	)
	if err != nil {
		return nil, fmt.Errorf("create task: %w", err)
	}
	t.Status = models.TaskStatus(statusStr)
	t.Priority = models.TaskPriority(priorityStr)
	t.RecurrenceInterval = models.TaskRecurrence(recurStr)
	return &t, nil
}

// UpdateTask updates task fields with reminder synchronization.
func UpdateTask(
	ctx context.Context,
	pool *pgxpool.Pool,
	user *models.User,
	taskUUID uuid.UUID,
	payload models.TaskUpdate,
) (*models.TaskDetail, error) {
	existing, err := GetTaskByUUID(ctx, pool, user, taskUUID)
	if err != nil {
		return nil, err
	}

	var sets []string
	var args []interface{}
	argID := 1

	if payload.Title != nil {
		sets = append(sets, fmt.Sprintf("title = $%d", argID))
		args = append(args, *payload.Title)
		argID++
	}
	if payload.Description != nil {
		sets = append(sets, fmt.Sprintf("description = $%d", argID))
		args = append(args, *payload.Description)
		argID++
	}
	if payload.Priority != nil {
		sets = append(sets, fmt.Sprintf("priority = $%d", argID))
		args = append(args, string(*payload.Priority))
		argID++
	}
	if payload.Status != nil {
		sets = append(sets, fmt.Sprintf("status = $%d", argID))
		args = append(args, string(*payload.Status))
		argID++
	}
	if payload.RecurrenceInterval != nil {
		sets = append(sets, fmt.Sprintf("recurrence_interval = $%d", argID))
		args = append(args, string(*payload.RecurrenceInterval))
		argID++
	}

	// Reminder sync logic:
	dueDateChanged := payload.DueDate != nil
	reminderAtChanged := payload.ReminderAt != nil

	if dueDateChanged {
		t := payload.DueDate.Time
		sets = append(sets, fmt.Sprintf("due_date = $%d", argID))
		args = append(args, t)
		argID++

		// Sync reminder_at if reminder_at was not provided or is nil
		if !reminderAtChanged {
			sets = append(sets, fmt.Sprintf("reminder_at = $%d", argID))
			args = append(args, t)
			argID++
			reminderAtChanged = true
		}
	} else if reminderAtChanged {
		t := payload.ReminderAt.Time
		sets = append(sets, fmt.Sprintf("reminder_at = $%d", argID))
		args = append(args, t)
		argID++
	}

	// Reset reminder_sent when reminder_at or due_date changes
	if dueDateChanged || reminderAtChanged {
		sets = append(sets, "reminder_sent = false", "last_reminder_sent_at = NULL")
	}

	sets = append(sets, "updated_at = NOW()")

	if len(sets) == 1 { // Only updated_at
		return existing, nil
	}

	args = append(args, taskUUID, user.ID)
	query := fmt.Sprintf(`
		UPDATE tasks
		SET %s
		WHERE uuid = $%d AND user_id = $%d
		RETURNING uuid, title, description, status, priority, completed,
		          due_date, reminder_at, completed_at, recurrence_interval,
		          position, is_archived, created_at, updated_at, user_id
	`, strings.Join(sets, ", "), argID, argID+1)

	var t models.TaskDetail
	var statusStr, priorityStr, recurStr string
	err = pool.QueryRow(ctx, query, args...).Scan(
		&t.UUID, &t.Title, &t.Description, &statusStr, &priorityStr, &t.Completed,
		&t.DueDate, &t.ReminderAt, &t.CompletedAt, &recurStr,
		&t.Position, &t.IsArchived, &t.CreatedAt, &t.UpdatedAt, &t.UserID,
	)
	if err != nil {
		return nil, fmt.Errorf("update task: %w", err)
	}
	t.Status = models.TaskStatus(statusStr)
	t.Priority = models.TaskPriority(priorityStr)
	t.RecurrenceInterval = models.TaskRecurrence(recurStr)
	return &t, nil
}

// DeleteTask removes a task.
func DeleteTask(ctx context.Context, pool *pgxpool.Pool, user *models.User, taskUUID uuid.UUID) error {
	tag, err := pool.Exec(ctx, "DELETE FROM tasks WHERE uuid = $1 AND user_id = $2", taskUUID, user.ID)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return ErrTaskNotFound
	}
	return nil
}

// CompleteTask marks a task completed and schedules next recurrence if recurring.
func CompleteTask(ctx context.Context, pool *pgxpool.Pool, user *models.User, taskUUID uuid.UUID) (*models.TaskDetail, error) {
	task, err := GetTaskByUUID(ctx, pool, user, taskUUID)
	if err != nil {
		return nil, err
	}

	tx, err := pool.Begin(ctx)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback(ctx)

	// If recurring: spawn next occurrence
	if task.RecurrenceInterval == models.RecurrenceDaily ||
		task.RecurrenceInterval == models.RecurrenceWeekly ||
		task.RecurrenceInterval == models.RecurrenceMonthly {

		var nextDue *time.Time
		var nextReminder *time.Time

		switch task.RecurrenceInterval {
		case models.RecurrenceDaily:
			if task.DueDate != nil {
				d := task.DueDate.Add(24 * time.Hour)
				nextDue = &d
			}
			if task.ReminderAt != nil {
				r := task.ReminderAt.Add(24 * time.Hour)
				nextReminder = &r
			}
		case models.RecurrenceWeekly:
			if task.DueDate != nil {
				d := task.DueDate.Add(7 * 24 * time.Hour)
				nextDue = &d
			}
			if task.ReminderAt != nil {
				r := task.ReminderAt.Add(7 * 24 * time.Hour)
				nextReminder = &r
			}
		case models.RecurrenceMonthly:
			if task.DueDate != nil {
				d := addMonth(*task.DueDate)
				nextDue = &d
			}
			if task.ReminderAt != nil {
				r := addMonth(*task.ReminderAt)
				nextReminder = &r
			}
		}

		nextUUID, _ := uuid.NewV7()
		_, err := tx.Exec(ctx, `
			INSERT INTO tasks (uuid, user_id, title, description, priority, due_date, reminder_at, reminder_sent, recurrence_interval, position, is_archived, created_at, updated_at)
			VALUES ($1, $2, $3, $4, $5, $6, $7, false, $8, 0, false, NOW(), NOW())
		`, nextUUID, user.ID, task.Title, task.Description, string(task.Priority), nextDue, nextReminder, string(task.RecurrenceInterval))
		if err != nil {
			return nil, fmt.Errorf("create recurring occurrence: %w", err)
		}

		// Current task recurrence is reset to NONE
		_, err = tx.Exec(ctx, "UPDATE tasks SET recurrence_interval = 'NONE' WHERE uuid = $1", taskUUID)
		if err != nil {
			return nil, err
		}
	}

	// Mark current task completed
	query := `
		UPDATE tasks
		SET status = 'COMPLETED', completed = true, completed_at = NOW(), updated_at = NOW()
		WHERE uuid = $1 AND user_id = $2
		RETURNING uuid, title, description, status, priority, completed,
		          due_date, reminder_at, completed_at, recurrence_interval,
		          position, is_archived, created_at, updated_at, user_id
	`
	var t models.TaskDetail
	var statusStr, priorityStr, recurStr string
	err = tx.QueryRow(ctx, query, taskUUID, user.ID).Scan(
		&t.UUID, &t.Title, &t.Description, &statusStr, &priorityStr, &t.Completed,
		&t.DueDate, &t.ReminderAt, &t.CompletedAt, &recurStr,
		&t.Position, &t.IsArchived, &t.CreatedAt, &t.UpdatedAt, &t.UserID,
	)
	if err != nil {
		return nil, err
	}

	if err := tx.Commit(ctx); err != nil {
		return nil, err
	}

	t.Status = models.TaskStatus(statusStr)
	t.Priority = models.TaskPriority(priorityStr)
	t.RecurrenceInterval = models.TaskRecurrence(recurStr)
	return &t, nil
}

// UncompleteTask resets completed status.
func UncompleteTask(ctx context.Context, pool *pgxpool.Pool, user *models.User, taskUUID uuid.UUID) (*models.TaskDetail, error) {
	query := `
		UPDATE tasks
		SET status = 'TODO', completed = false, completed_at = NULL, updated_at = NOW()
		WHERE uuid = $1 AND user_id = $2
		RETURNING uuid, title, description, status, priority, completed,
		          due_date, reminder_at, completed_at, recurrence_interval,
		          position, is_archived, created_at, updated_at, user_id
	`
	var t models.TaskDetail
	var statusStr, priorityStr, recurStr string
	err := pool.QueryRow(ctx, query, taskUUID, user.ID).Scan(
		&t.UUID, &t.Title, &t.Description, &statusStr, &priorityStr, &t.Completed,
		&t.DueDate, &t.ReminderAt, &t.CompletedAt, &recurStr,
		&t.Position, &t.IsArchived, &t.CreatedAt, &t.UpdatedAt, &t.UserID,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrTaskNotFound
		}
		return nil, err
	}
	t.Status = models.TaskStatus(statusStr)
	t.Priority = models.TaskPriority(priorityStr)
	t.RecurrenceInterval = models.TaskRecurrence(recurStr)
	return &t, nil
}

// ArchiveTask soft-archives a task.
func ArchiveTask(ctx context.Context, pool *pgxpool.Pool, user *models.User, taskUUID uuid.UUID) (*models.TaskDetail, error) {
	query := `
		UPDATE tasks
		SET is_archived = true, updated_at = NOW()
		WHERE uuid = $1 AND user_id = $2
		RETURNING uuid, title, description, status, priority, completed,
		          due_date, reminder_at, completed_at, recurrence_interval,
		          position, is_archived, created_at, updated_at, user_id
	`
	var t models.TaskDetail
	var statusStr, priorityStr, recurStr string
	err := pool.QueryRow(ctx, query, taskUUID, user.ID).Scan(
		&t.UUID, &t.Title, &t.Description, &statusStr, &priorityStr, &t.Completed,
		&t.DueDate, &t.ReminderAt, &t.CompletedAt, &recurStr,
		&t.Position, &t.IsArchived, &t.CreatedAt, &t.UpdatedAt, &t.UserID,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrTaskNotFound
		}
		return nil, err
	}
	t.Status = models.TaskStatus(statusStr)
	t.Priority = models.TaskPriority(priorityStr)
	t.RecurrenceInterval = models.TaskRecurrence(recurStr)
	return &t, nil
}
