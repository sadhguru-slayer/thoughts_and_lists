package models

import (
	"time"

	"github.com/google/uuid"
)

// Thought represents the database record in the "thoughts" table.
type Thought struct {
	ID          int        `json:"id"`
	UUID        uuid.UUID  `json:"uuid"`
	Title       string     `json:"title"`
	Content     string     `json:"content"`
	UserID      int        `json:"user_id"`
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`
	IsPinned    bool       `json:"is_pinned"`
	PinnedAt    *time.Time `json:"pinned_at"`
	PinnedOrder *int       `json:"pinned_order"`
	IsStarred   bool       `json:"is_starred"`
}

// ThoughtSummary represents a trimmed thought preview in list responses.
type ThoughtSummary struct {
	UUID           uuid.UUID  `json:"uuid"`
	Title          string     `json:"title"`
	ContentPreview string     `json:"content_preview"`
	UserID         int        `json:"user_id"`
	CreatedAt      time.Time  `json:"created_at"`
	UpdatedAt      time.Time  `json:"updated_at"`
	IsPinned       bool       `json:"is_pinned"`
	PinnedAt       *time.Time `json:"pinned_at"`
	PinnedOrder    *int       `json:"pinned_order"`
	IsStarred      bool       `json:"is_starred"`
}

// ThoughtDetail represents the full thought details.
type ThoughtDetail struct {
	UUID        uuid.UUID  `json:"uuid"`
	Title       string     `json:"title"`
	Content     string     `json:"content"`
	UserID      int        `json:"user_id"`
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`
	IsPinned    bool       `json:"is_pinned"`
	PinnedAt    *time.Time `json:"pinned_at"`
	PinnedOrder *int       `json:"pinned_order"`
	IsStarred   bool       `json:"is_starred"`
}

// PaginatedResponse is a generic pagination envelope.
type PaginatedResponse[T any] struct {
	Items      []T `json:"items"`
	Total      int `json:"total"`
	Page       int `json:"page"`
	PerPage    int `json:"per_page"`
	TotalPages int `json:"total_pages"`
}

// ThoughtCreate is the payload for creating a thought.
type ThoughtCreate struct {
	Title   string `json:"title"`
	Content string `json:"content"`
}

// ThoughtUpdate is the payload for updating a thought.
type ThoughtUpdate struct {
	Title       *string `json:"title"`
	Content     *string `json:"content"`
	IsPinned    *bool   `json:"is_pinned"`
	PinnedOrder *int    `json:"pinned_order"`
	IsStarred   *bool   `json:"is_starred"`
}

// BulkDeleteThoughts is the payload for deleting multiple thoughts by UUID.
type BulkDeleteThoughts struct {
	UUIDs []uuid.UUID `json:"uuids"`
}

// ThoughtOrderItem is an entry in BulkThoughtOrderUpdate.
type ThoughtOrderItem struct {
	UUID        uuid.UUID `json:"uuid"`
	PinnedOrder int       `json:"pinned_order"`
}

// BulkThoughtOrderUpdate is the payload for reordering pinned thoughts.
type BulkThoughtOrderUpdate struct {
	Orders []ThoughtOrderItem `json:"orders"`
}

// MoveThoughtRequest is the payload for moving a thought to a notebook note.
type MoveThoughtRequest struct {
	TargetNotebookUUID uuid.UUID `json:"target_notebook_uuid"`
}

// MoveThoughtResponse is the response returned when a thought is moved to a notebook.
type MoveThoughtResponse struct {
	Message      string `json:"message"`
	Type         string `json:"type"`
	UUID         string `json:"uuid"`
	NotebookUUID string `json:"notebook_uuid"`
}
