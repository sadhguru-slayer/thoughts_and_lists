package models

import (
	"time"

	"github.com/google/uuid"
)

// Notebook represents a row in the "notebooks" table.
type Notebook struct {
	ID          int        `json:"id"`
	UUID        uuid.UUID  `json:"uuid"`
	Name        string     `json:"name"`
	Description *string    `json:"description"`
	UserID      int        `json:"user_id"`
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`
	Notes       []Note     `json:"notes,omitempty"`
}

// Note represents a row in the "notes" table.
type Note struct {
	ID         int       `json:"id"`
	UUID       uuid.UUID `json:"uuid"`
	Title      string    `json:"title"`
	Content    string    `json:"content"`
	NotebookID int       `json:"notebook_id"`
	UserID     int       `json:"user_id"`
	IsPinned   bool      `json:"is_pinned"`
	IsStarred  bool      `json:"is_starred"`
	CreatedAt  time.Time `json:"created_at"`
	UpdatedAt  time.Time `json:"updated_at"`
}

// NotebookCreate is the payload for creating a notebook.
type NotebookCreate struct {
	Name        string  `json:"name"`
	Description *string `json:"description"`
}

// NotebookUpdate is the payload for updating a notebook.
type NotebookUpdate struct {
	Name        *string `json:"name"`
	Description *string `json:"description"`
}

// NoteCreate is the payload for adding a note to a notebook.
type NoteCreate struct {
	Title   string `json:"title"`
	Content string `json:"content"`
}

// NoteUpdate is the payload for editing a note.
type NoteUpdate struct {
	Title     *string `json:"title"`
	Content   *string `json:"content"`
	IsPinned  *bool   `json:"is_pinned"`
	IsStarred *bool   `json:"is_starred"`
}

// MoveNoteRequest is the payload for moving a note to another notebook or quick notes.
type MoveNoteRequest struct {
	TargetNotebookUUID *uuid.UUID `json:"target_notebook_uuid"`
}
