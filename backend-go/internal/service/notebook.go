package service

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sadguruchenu/thoughtsgo/internal/models"
)

var (
	ErrNoteNotFound = errors.New("note not found")
)

// GetNotebooks retrieves all notebooks for the user, with nested notes.
func GetNotebooks(ctx context.Context, pool *pgxpool.Pool, user *models.User) ([]models.Notebook, error) {
	query := `
		SELECT id, uuid, name, description, user_id, created_at, updated_at
		FROM notebooks
		WHERE user_id = $1
		ORDER BY id DESC
	`
	rows, err := pool.Query(ctx, query, user.ID)
	if err != nil {
		return nil, fmt.Errorf("select notebooks: %w", err)
	}
	defer rows.Close()

	notebooks := make([]models.Notebook, 0)
	notebookMap := make(map[int]int) // id -> index

	for rows.Next() {
		var nb models.Notebook
		if err := rows.Scan(&nb.ID, &nb.UUID, &nb.Name, &nb.Description, &nb.UserID, &nb.CreatedAt, &nb.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan notebook: %w", err)
		}
		nb.Notes = make([]models.Note, 0)
		notebookMap[nb.ID] = len(notebooks)
		notebooks = append(notebooks, nb)
	}

	if len(notebooks) == 0 {
		return notebooks, nil
	}

	// Fetch notes for all notebooks
	notesQuery := `
		SELECT id, uuid, title, content, notebook_id, user_id, is_pinned, is_starred, created_at, updated_at
		FROM notes
		WHERE user_id = $1
		ORDER BY is_pinned DESC, id DESC
	`
	noteRows, err := pool.Query(ctx, notesQuery, user.ID)
	if err != nil {
		return nil, fmt.Errorf("select notes: %w", err)
	}
	defer noteRows.Close()

	for noteRows.Next() {
		var n models.Note
		if err := noteRows.Scan(&n.ID, &n.UUID, &n.Title, &n.Content, &n.NotebookID, &n.UserID, &n.IsPinned, &n.IsStarred, &n.CreatedAt, &n.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan note: %w", err)
		}
		if idx, ok := notebookMap[n.NotebookID]; ok {
			notebooks[idx].Notes = append(notebooks[idx].Notes, n)
		}
	}

	return notebooks, nil
}

// GetNotebookByUUID retrieves a single notebook by UUID with its notes.
func GetNotebookByUUID(ctx context.Context, pool *pgxpool.Pool, user *models.User, nbUUID uuid.UUID) (*models.Notebook, error) {
	query := `
		SELECT id, uuid, name, description, user_id, created_at, updated_at
		FROM notebooks
		WHERE uuid = $1 AND user_id = $2
		LIMIT 1
	`
	var nb models.Notebook
	err := pool.QueryRow(ctx, query, nbUUID, user.ID).Scan(
		&nb.ID, &nb.UUID, &nb.Name, &nb.Description, &nb.UserID, &nb.CreatedAt, &nb.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotebookNotFound
		}
		return nil, err
	}
	nb.Notes = make([]models.Note, 0)

	notesQuery := `
		SELECT id, uuid, title, content, notebook_id, user_id, is_pinned, is_starred, created_at, updated_at
		FROM notes
		WHERE notebook_id = $1 AND user_id = $2
		ORDER BY is_pinned DESC, id DESC
	`
	rows, err := pool.Query(ctx, notesQuery, nb.ID, user.ID)
	if err != nil {
		return nil, fmt.Errorf("select notes: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var n models.Note
		if err := rows.Scan(&n.ID, &n.UUID, &n.Title, &n.Content, &n.NotebookID, &n.UserID, &n.IsPinned, &n.IsStarred, &n.CreatedAt, &n.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan note: %w", err)
		}
		nb.Notes = append(nb.Notes, n)
	}

	return &nb, nil
}

// CreateNotebook inserts a new notebook.
func CreateNotebook(ctx context.Context, pool *pgxpool.Pool, user *models.User, payload models.NotebookCreate) (*models.Notebook, error) {
	newUUID, err := uuid.NewV7()
	if err != nil {
		newUUID = uuid.New()
	}

	query := `
		INSERT INTO notebooks (uuid, name, description, user_id, created_at, updated_at)
		VALUES ($1, $2, $3, $4, NOW(), NOW())
		RETURNING id, uuid, name, description, user_id, created_at, updated_at
	`
	var nb models.Notebook
	err = pool.QueryRow(ctx, query, newUUID, payload.Name, payload.Description, user.ID).Scan(
		&nb.ID, &nb.UUID, &nb.Name, &nb.Description, &nb.UserID, &nb.CreatedAt, &nb.UpdatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("create notebook: %w", err)
	}
	nb.Notes = make([]models.Note, 0)
	return &nb, nil
}

// UpdateNotebook edits a notebook's name or description.
func UpdateNotebook(ctx context.Context, pool *pgxpool.Pool, user *models.User, nbUUID uuid.UUID, payload models.NotebookUpdate) (*models.Notebook, error) {
	var sets []string
	var args []interface{}
	argID := 1

	if payload.Name != nil {
		sets = append(sets, fmt.Sprintf("name = $%d", argID))
		args = append(args, *payload.Name)
		argID++
	}
	if payload.Description != nil {
		sets = append(sets, fmt.Sprintf("description = $%d", argID))
		args = append(args, *payload.Description)
		argID++
	}

	sets = append(sets, "updated_at = NOW()")

	args = append(args, nbUUID, user.ID)
	query := fmt.Sprintf(`
		UPDATE notebooks
		SET %s
		WHERE uuid = $%d AND user_id = $%d
		RETURNING id, uuid, name, description, user_id, created_at, updated_at
	`, strings.Join(sets, ", "), argID, argID+1)

	var nb models.Notebook
	err := pool.QueryRow(ctx, query, args...).Scan(
		&nb.ID, &nb.UUID, &nb.Name, &nb.Description, &nb.UserID, &nb.CreatedAt, &nb.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotebookNotFound
		}
		return nil, fmt.Errorf("update notebook: %w", err)
	}
	return &nb, nil
}

// DeleteNotebook removes a notebook and cascade-deletes its notes.
func DeleteNotebook(ctx context.Context, pool *pgxpool.Pool, user *models.User, nbUUID uuid.UUID) error {
	tag, err := pool.Exec(ctx, "DELETE FROM notebooks WHERE uuid = $1 AND user_id = $2", nbUUID, user.ID)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return ErrNotebookNotFound
	}
	return nil
}

// CreateNote adds a note into a specific notebook.
func CreateNote(ctx context.Context, pool *pgxpool.Pool, user *models.User, nbUUID uuid.UUID, payload models.NoteCreate) (*models.Note, error) {
	var notebookID int
	err := pool.QueryRow(ctx, "SELECT id FROM notebooks WHERE uuid = $1 AND user_id = $2", nbUUID, user.ID).Scan(&notebookID)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotebookNotFound
		}
		return nil, err
	}

	newUUID, err := uuid.NewV7()
	if err != nil {
		newUUID = uuid.New()
	}

	query := `
		INSERT INTO notes (uuid, title, content, notebook_id, user_id, is_pinned, is_starred, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, false, false, NOW(), NOW())
		RETURNING id, uuid, title, content, notebook_id, user_id, is_pinned, is_starred, created_at, updated_at
	`
	var n models.Note
	err = pool.QueryRow(ctx, query, newUUID, payload.Title, payload.Content, notebookID, user.ID).Scan(
		&n.ID, &n.UUID, &n.Title, &n.Content, &n.NotebookID, &n.UserID, &n.IsPinned, &n.IsStarred, &n.CreatedAt, &n.UpdatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("create note: %w", err)
	}
	return &n, nil
}

// GetNoteByUUID retrieves a single note by UUID.
func GetNoteByUUID(ctx context.Context, pool *pgxpool.Pool, user *models.User, noteUUID uuid.UUID) (*models.Note, error) {
	query := `
		SELECT id, uuid, title, content, notebook_id, user_id, is_pinned, is_starred, created_at, updated_at
		FROM notes
		WHERE uuid = $1 AND user_id = $2
		LIMIT 1
	`
	var n models.Note
	err := pool.QueryRow(ctx, query, noteUUID, user.ID).Scan(
		&n.ID, &n.UUID, &n.Title, &n.Content, &n.NotebookID, &n.UserID, &n.IsPinned, &n.IsStarred, &n.CreatedAt, &n.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNoteNotFound
		}
		return nil, err
	}
	return &n, nil
}

// UpdateNote updates a note's title, content, pin, or star status.
func UpdateNote(ctx context.Context, pool *pgxpool.Pool, user *models.User, noteUUID uuid.UUID, payload models.NoteUpdate) (*models.Note, error) {
	var sets []string
	var args []interface{}
	argID := 1

	if payload.Title != nil {
		sets = append(sets, fmt.Sprintf("title = $%d", argID))
		args = append(args, *payload.Title)
		argID++
	}
	if payload.Content != nil {
		sets = append(sets, fmt.Sprintf("content = $%d", argID))
		args = append(args, *payload.Content)
		argID++
	}
	if payload.IsPinned != nil {
		sets = append(sets, fmt.Sprintf("is_pinned = $%d", argID))
		args = append(args, *payload.IsPinned)
		argID++
	}
	if payload.IsStarred != nil {
		sets = append(sets, fmt.Sprintf("is_starred = $%d", argID))
		args = append(args, *payload.IsStarred)
		argID++
	}

	sets = append(sets, "updated_at = NOW()")

	args = append(args, noteUUID, user.ID)
	query := fmt.Sprintf(`
		UPDATE notes
		SET %s
		WHERE uuid = $%d AND user_id = $%d
		RETURNING id, uuid, title, content, notebook_id, user_id, is_pinned, is_starred, created_at, updated_at
	`, strings.Join(sets, ", "), argID, argID+1)

	var n models.Note
	err := pool.QueryRow(ctx, query, args...).Scan(
		&n.ID, &n.UUID, &n.Title, &n.Content, &n.NotebookID, &n.UserID, &n.IsPinned, &n.IsStarred, &n.CreatedAt, &n.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNoteNotFound
		}
		return nil, fmt.Errorf("update note: %w", err)
	}
	return &n, nil
}

// DeleteNote deletes a note by UUID.
func DeleteNote(ctx context.Context, pool *pgxpool.Pool, user *models.User, noteUUID uuid.UUID) error {
	tag, err := pool.Exec(ctx, "DELETE FROM notes WHERE uuid = $1 AND user_id = $2", noteUUID, user.ID)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return ErrNoteNotFound
	}
	return nil
}

// MoveNote moves a note to another notebook or into thoughts (Quick Notes) if target is nil.
func MoveNote(
	ctx context.Context,
	pool *pgxpool.Pool,
	user *models.User,
	noteUUID uuid.UUID,
	targetNotebookUUID *uuid.UUID,
) (map[string]interface{}, error) {
	tx, err := pool.Begin(ctx)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback(ctx)

	var note models.Note
	err = tx.QueryRow(ctx, `
		SELECT id, uuid, title, content, is_pinned, is_starred
		FROM notes
		WHERE uuid = $1 AND user_id = $2
	`, noteUUID, user.ID).Scan(&note.ID, &note.UUID, &note.Title, &note.Content, &note.IsPinned, &note.IsStarred)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNoteNotFound
		}
		return nil, err
	}

	if targetNotebookUUID == nil {
		// Move to Quick Notes (thoughts)
		thoughtUUID, _ := uuid.NewV7()
		_, err := tx.Exec(ctx, `
			INSERT INTO thoughts (uuid, title, content, user_id, is_pinned, is_starred, created_at, updated_at)
			VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
		`, thoughtUUID, note.Title, note.Content, user.ID, note.IsPinned, note.IsStarred)
		if err != nil {
			return nil, fmt.Errorf("insert thought: %w", err)
		}

		_, err = tx.Exec(ctx, "DELETE FROM notes WHERE id = $1", note.ID)
		if err != nil {
			return nil, err
		}

		if err := tx.Commit(ctx); err != nil {
			return nil, err
		}

		return map[string]interface{}{
			"message": "Moved to Quick Notes",
			"type":    "thought",
			"uuid":    thoughtUUID.String(),
		}, nil
	}

	// Move to another notebook
	var targetNotebookID int
	err = tx.QueryRow(ctx, `
		SELECT id FROM notebooks WHERE uuid = $1 AND user_id = $2
	`, *targetNotebookUUID, user.ID).Scan(&targetNotebookID)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotebookNotFound
		}
		return nil, err
	}

	_, err = tx.Exec(ctx, `
		UPDATE notes SET notebook_id = $1, updated_at = NOW() WHERE id = $2
	`, targetNotebookID, note.ID)
	if err != nil {
		return nil, err
	}

	if err := tx.Commit(ctx); err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"message":       "Note moved to target notebook",
		"type":          "note",
		"uuid":          note.UUID.String(),
		"notebook_uuid": targetNotebookUUID.String(),
	}, nil
}
