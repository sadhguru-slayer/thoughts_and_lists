package models

import (
	"time"

	"github.com/google/uuid"
)

// TaskPriority represents priority level.
type TaskPriority string

const (
	PriorityLow    TaskPriority = "LOW"
	PriorityMedium TaskPriority = "MEDIUM"
	PriorityHigh   TaskPriority = "HIGH"
	PriorityUrgent TaskPriority = "URGENT"
)

// TaskRecurrence represents recurring interval.
type TaskRecurrence string

const (
	RecurrenceNone    TaskRecurrence = "NONE"
	RecurrenceDaily   TaskRecurrence = "DAILY"
	RecurrenceWeekly  TaskRecurrence = "WEEKLY"
	RecurrenceMonthly TaskRecurrence = "MONTHLY"
)

// TaskStatus represents current progress state.
type TaskStatus string

const (
	StatusTodo       TaskStatus = "TODO"
	StatusInProgress TaskStatus = "IN_PROGRESS"
	StatusCompleted  TaskStatus = "COMPLETED"
	StatusCancelled  TaskStatus = "CANCELLED"
)

// Task represents the database record in the "tasks" table.
type Task struct {
	ID                 int            `json:"id"`
	UUID               uuid.UUID      `json:"uuid"`
	UserID             int            `json:"user_id"`
	Title              string         `json:"title"`
	Description        *string        `json:"description"`
	Status             TaskStatus     `json:"status"`
	Completed          bool           `json:"completed"`
	Priority           TaskPriority   `json:"priority"`
	DueDate            *time.Time     `json:"due_date"`
	ReminderAt         *time.Time     `json:"reminder_at"`
	ReminderSent       bool           `json:"reminder_sent"`
	LastReminderSentAt *time.Time     `json:"last_reminder_sent_at"`
	CompletedAt        *time.Time     `json:"completed_at"`
	RecurrenceInterval TaskRecurrence `json:"recurrence_interval"`
	Position           int            `json:"position"`
	IsArchived         bool           `json:"is_archived"`
	CreatedAt          time.Time      `json:"created_at"`
	UpdatedAt          time.Time      `json:"updated_at"`
}

// TaskSummary is returned in the GET /tasks list.
type TaskSummary struct {
	UUID               uuid.UUID      `json:"uuid"`
	Title              string         `json:"title"`
	Status             TaskStatus     `json:"status"`
	Priority           TaskPriority   `json:"priority"`
	Completed          bool           `json:"completed"`
	DueDate            *time.Time     `json:"due_date"`
	CreatedAt          time.Time      `json:"created_at"`
	RecurrenceInterval TaskRecurrence `json:"recurrence_interval"`
}

// TaskDetail is returned for detail, create, and update responses.
type TaskDetail struct {
	UUID               uuid.UUID      `json:"uuid"`
	Title              string         `json:"title"`
	Description        *string        `json:"description"`
	Status             TaskStatus     `json:"status"`
	Priority           TaskPriority   `json:"priority"`
	Completed          bool           `json:"completed"`
	DueDate            *time.Time     `json:"due_date"`
	ReminderAt         *time.Time     `json:"reminder_at"`
	CompletedAt        *time.Time     `json:"completed_at"`
	RecurrenceInterval TaskRecurrence `json:"recurrence_interval"`
	Position           int            `json:"position"`
	IsArchived         bool           `json:"is_archived"`
	CreatedAt          time.Time      `json:"created_at"`
	UpdatedAt          time.Time      `json:"updated_at"`
	UserID             int            `json:"user_id"`
}

// TaskCreate is the payload for creating a new task.
type TaskCreate struct {
	Title              string          `json:"title"`
	Description        *string         `json:"description"`
	Priority           *TaskPriority   `json:"priority"`
	DueDate            *FlexibleTime   `json:"due_date"`
	ReminderAt         *FlexibleTime   `json:"reminder_at"`
	RecurrenceInterval *TaskRecurrence `json:"recurrence_interval"`
}

// TaskUpdate is the payload for editing a task.
type TaskUpdate struct {
	Title              *string         `json:"title"`
	Description        *string         `json:"description"`
	Priority           *TaskPriority   `json:"priority"`
	Status             *TaskStatus     `json:"status"`
	DueDate            *FlexibleTime   `json:"due_date"`
	ReminderAt         *FlexibleTime   `json:"reminder_at"`
	RecurrenceInterval *TaskRecurrence `json:"recurrence_interval"`
}
