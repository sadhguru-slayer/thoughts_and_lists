package service

import (
	"context"
	"errors"
	"fmt"
	"math"
	"strings"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sadguruchenu/thoughtsgo/internal/models"
)

var (
	ErrThoughtNotFound  = errors.New("thought not found")
	ErrNotebookNotFound = errors.New("target notebook not found")
)

// GetThoughts retrieves a paginated list of thoughts with search and summary previews.
func GetThoughts(
	ctx context.Context,
	pool *pgxpool.Pool,
	user *models.User,
	search string,
	page int,
	perPage int,
) (models.PaginatedResponse[models.ThoughtSummary], error) {
	if page < 1 {
		page = 1
	}
	if perPage < 1 || perPage > 100 {
		perPage = 20
	}

	// 1. Build COUNT query
	var countWhere []string
	var countArgs []interface{}
	argID := 1

	if user.Role != models.RoleAdmin {
		countWhere = append(countWhere, fmt.Sprintf("user_id = $%d", argID))
		countArgs = append(countArgs, user.ID)
		argID++
	}

	if search != "" {
		countWhere = append(countWhere, fmt.Sprintf("(title ILIKE $%d OR content ILIKE $%d)", argID, argID))
		countArgs = append(countArgs, "%"+search+"%")
		argID++
	}

	countQuery := "SELECT COUNT(*) FROM thoughts"
	if len(countWhere) > 0 {
		countQuery += " WHERE " + strings.Join(countWhere, " AND ")
	}

	var total int
	err := pool.QueryRow(ctx, countQuery, countArgs...).Scan(&total)
	if err != nil {
		return models.PaginatedResponse[models.ThoughtSummary]{}, fmt.Errorf("count thoughts: %w", err)
	}

	totalPages := 1
	if perPage > 0 {
		totalPages = int(math.Ceil(float64(total) / float64(perPage)))
	}
	if totalPages == 0 {
		totalPages = 1
	}

	// 2. Build SELECT query with previews
	var selectWhere []string
	var selectArgs []interface{}
	selArgID := 1

	if user.Role != models.RoleAdmin {
		selectWhere = append(selectWhere, fmt.Sprintf("user_id = $%d", selArgID))
		selectArgs = append(selectArgs, user.ID)
		selArgID++
	}

	if search != "" {
		selectWhere = append(selectWhere, fmt.Sprintf("(title ILIKE $%d OR content ILIKE $%d)", selArgID, selArgID))
		selectArgs = append(selectArgs, "%"+search+"%")
		selArgID++
	}

	selectQuery := `
		SELECT uuid,
		       CASE WHEN length(trim(title)) > 60 THEN concat(left(trim(title), 60), '…') ELSE trim(title) END AS title,
		       CASE WHEN length(trim(content)) > 120 THEN concat(left(trim(content), 120), '…') ELSE trim(content) END AS content_preview,
		       user_id, created_at, updated_at, is_pinned, pinned_at, pinned_order, is_starred
		FROM thoughts
	`
	if len(selectWhere) > 0 {
		selectQuery += " WHERE " + strings.Join(selectWhere, " AND ")
	}

	selectQuery += fmt.Sprintf(" ORDER BY id DESC OFFSET $%d LIMIT $%d", selArgID, selArgID+1)
	offset := (page - 1) * perPage
	selectArgs = append(selectArgs, offset, perPage)

	rows, err := pool.Query(ctx, selectQuery, selectArgs...)
	if err != nil {
		return models.PaginatedResponse[models.ThoughtSummary]{}, fmt.Errorf("select thoughts: %w", err)
	}
	defer rows.Close()

	items := make([]models.ThoughtSummary, 0)
	for rows.Next() {
		var item models.ThoughtSummary
		err := rows.Scan(
			&item.UUID,
			&item.Title,
			&item.ContentPreview,
			&item.UserID,
			&item.CreatedAt,
			&item.UpdatedAt,
			&item.IsPinned,
			&item.PinnedAt,
			&item.PinnedOrder,
			&item.IsStarred,
		)
		if err != nil {
			return models.PaginatedResponse[models.ThoughtSummary]{}, fmt.Errorf("scan thought: %w", err)
		}
		items = append(items, item)
	}

	return models.PaginatedResponse[models.ThoughtSummary]{
		Items:      items,
		Total:      total,
		Page:       page,
		PerPage:    perPage,
		TotalPages: totalPages,
	}, nil
}

// GetThoughtByUUID retrieves full detail of a single thought.
func GetThoughtByUUID(ctx context.Context, pool *pgxpool.Pool, user *models.User, thoughtUUID uuid.UUID) (*models.ThoughtDetail, error) {
	query := `
		SELECT uuid, title, content, user_id, created_at, updated_at,
		       is_pinned, pinned_at, pinned_order, is_starred
		FROM thoughts
		WHERE uuid = $1
	`
	args := []interface{}{thoughtUUID}
	if user.Role != models.RoleAdmin {
		query += " AND user_id = $2"
		args = append(args, user.ID)
	}
	query += " LIMIT 1"

	var t models.ThoughtDetail
	err := pool.QueryRow(ctx, query, args...).Scan(
		&t.UUID, &t.Title, &t.Content, &t.UserID, &t.CreatedAt, &t.UpdatedAt,
		&t.IsPinned, &t.PinnedAt, &t.PinnedOrder, &t.IsStarred,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrThoughtNotFound
		}
		return nil, err
	}
	return &t, nil
}

// CreateThought inserts a new thought for the authenticated user.
func CreateThought(ctx context.Context, pool *pgxpool.Pool, user *models.User, payload models.ThoughtCreate) (*models.ThoughtDetail, error) {
	newUUID, err := uuid.NewV7()
	if err != nil {
		newUUID = uuid.New()
	}

	query := `
		INSERT INTO thoughts (uuid, title, content, user_id, is_pinned, is_starred, created_at, updated_at)
		VALUES ($1, $2, $3, $4, false, false, NOW(), NOW())
		RETURNING uuid, title, content, user_id, created_at, updated_at,
		          is_pinned, pinned_at, pinned_order, is_starred
	`
	var t models.ThoughtDetail
	err = pool.QueryRow(ctx, query, newUUID, payload.Title, payload.Content, user.ID).Scan(
		&t.UUID, &t.Title, &t.Content, &t.UserID, &t.CreatedAt, &t.UpdatedAt,
		&t.IsPinned, &t.PinnedAt, &t.PinnedOrder, &t.IsStarred,
	)
	if err != nil {
		return nil, fmt.Errorf("create thought: %w", err)
	}
	return &t, nil
}

// UpdateThought updates specific fields of a thought, matching FastAPI's pinning behavior.
func UpdateThought(
	ctx context.Context,
	pool *pgxpool.Pool,
	user *models.User,
	thoughtUUID uuid.UUID,
	payload models.ThoughtUpdate,
) (*models.ThoughtDetail, error) {
	// First fetch existing thought to know current pinning state
	existing, err := GetThoughtByUUID(ctx, pool, user, thoughtUUID)
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
	if payload.Content != nil {
		sets = append(sets, fmt.Sprintf("content = $%d", argID))
		args = append(args, *payload.Content)
		argID++
	}
	if payload.IsStarred != nil {
		sets = append(sets, fmt.Sprintf("is_starred = $%d", argID))
		args = append(args, *payload.IsStarred)
		argID++
	}
	if payload.PinnedOrder != nil {
		sets = append(sets, fmt.Sprintf("pinned_order = $%d", argID))
		args = append(args, *payload.PinnedOrder)
		argID++
	}
	if payload.IsPinned != nil {
		sets = append(sets, fmt.Sprintf("is_pinned = $%d", argID))
		args = append(args, *payload.IsPinned)
		argID++

		// Pin logic:
		if *payload.IsPinned && !existing.IsPinned {
			// Newly pinned -> set pinned_at to now()
			sets = append(sets, "pinned_at = NOW()")
		} else if !*payload.IsPinned {
			// Unpinned -> reset pinned_at and pinned_order to NULL
			sets = append(sets, "pinned_at = NULL", "pinned_order = NULL")
		}
	}

	// Always update updated_at
	sets = append(sets, "updated_at = NOW()")

	args = append(args, thoughtUUID, user.ID)
	query := fmt.Sprintf(`
		UPDATE thoughts
		SET %s
		WHERE uuid = $%d AND user_id = $%d
		RETURNING uuid, title, content, user_id, created_at, updated_at,
		          is_pinned, pinned_at, pinned_order, is_starred
	`, strings.Join(sets, ", "), argID, argID+1)

	var t models.ThoughtDetail
	err = pool.QueryRow(ctx, query, args...).Scan(
		&t.UUID, &t.Title, &t.Content, &t.UserID, &t.CreatedAt, &t.UpdatedAt,
		&t.IsPinned, &t.PinnedAt, &t.PinnedOrder, &t.IsStarred,
	)
	if err != nil {
		return nil, fmt.Errorf("update thought: %w", err)
	}
	return &t, nil
}

// DeleteThought deletes a single thought by UUID for the owner.
func DeleteThought(ctx context.Context, pool *pgxpool.Pool, user *models.User, thoughtUUID uuid.UUID) error {
	tag, err := pool.Exec(ctx, "DELETE FROM thoughts WHERE uuid = $1 AND user_id = $2", thoughtUUID, user.ID)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return ErrThoughtNotFound
	}
	return nil
}

// BulkDeleteThoughts deletes multiple thoughts by UUID.
func BulkDeleteThoughts(ctx context.Context, pool *pgxpool.Pool, user *models.User, uuids []uuid.UUID) (int64, error) {
	tag, err := pool.Exec(ctx, "DELETE FROM thoughts WHERE uuid = ANY($1) AND user_id = $2", uuids, user.ID)
	if err != nil {
		return 0, err
	}
	return tag.RowsAffected(), nil
}

// UpdateThoughtOrders updates the pinned_order for multiple thoughts.
func UpdateThoughtOrders(ctx context.Context, pool *pgxpool.Pool, user *models.User, orders []models.ThoughtOrderItem) error {
	tx, err := pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	for _, item := range orders {
		_, err := tx.Exec(ctx, `
			UPDATE thoughts
			SET pinned_order = $1
			WHERE uuid = $2 AND user_id = $3
		`, item.PinnedOrder, item.UUID, user.ID)
		if err != nil {
			return err
		}
	}

	return tx.Commit(ctx)
}

// MoveThoughtToNotebook transfers a thought to a note in the specified notebook.
func MoveThoughtToNotebook(
	ctx context.Context,
	pool *pgxpool.Pool,
	user *models.User,
	thoughtUUID uuid.UUID,
	notebookUUID uuid.UUID,
) (*models.MoveThoughtResponse, error) {
	tx, err := pool.Begin(ctx)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback(ctx)

	// 1. Fetch thought
	var thoughtID int
	var title, content string
	var isPinned, isStarred bool
	err = tx.QueryRow(ctx, `
		SELECT id, title, content, is_pinned, is_starred
		FROM thoughts
		WHERE uuid = $1 AND user_id = $2
	`, thoughtUUID, user.ID).Scan(&thoughtID, &title, &content, &isPinned, &isStarred)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrThoughtNotFound
		}
		return nil, err
	}

	// 2. Fetch target notebook
	var notebookID int
	err = tx.QueryRow(ctx, `
		SELECT id FROM notebooks WHERE uuid = $1 AND user_id = $2
	`, notebookUUID, user.ID).Scan(&notebookID)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotebookNotFound
		}
		return nil, err
	}

	// 3. Create Note
	noteUUID, err := uuid.NewV7()
	if err != nil {
		noteUUID = uuid.New()
	}

	_, err = tx.Exec(ctx, `
		INSERT INTO notes (uuid, title, content, notebook_id, user_id, is_pinned, is_starred, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
	`, noteUUID, title, content, notebookID, user.ID, isPinned, isStarred)
	if err != nil {
		return nil, fmt.Errorf("insert note: %w", err)
	}

	// 4. Delete Thought
	_, err = tx.Exec(ctx, "DELETE FROM thoughts WHERE id = $1", thoughtID)
	if err != nil {
		return nil, fmt.Errorf("delete thought: %w", err)
	}

	if err := tx.Commit(ctx); err != nil {
		return nil, err
	}

	return &models.MoveThoughtResponse{
		Message:      "Thought moved to notebook",
		Type:         "note",
		UUID:         noteUUID.String(),
		NotebookUUID: notebookUUID.String(),
	}, nil
}
