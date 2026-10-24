package service

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"math"
	"sort"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sadguruchenu/thoughtsgo/internal/models"
)

var (
	ErrJournalNotFound  = errors.New("journal not found")
	ErrTemplateNotFound = errors.New("template not found")
	ErrInvalidInput     = errors.New("invalid input")
)

type JournalService struct {
	pool *pgxpool.Pool
}

func NewJournalService(pool *pgxpool.Pool) *JournalService {
	return &JournalService{pool: pool}
}

func (s *JournalService) GetJournals(ctx context.Context, userID int, page, perPage int, search, sortOrder, dateFilter string) (*models.JournalListResponse, error) {
	if page < 1 {
		page = 1
	}
	if perPage < 1 || perPage > 100 {
		perPage = 20
	}

	whereClauses := []string{"j.user_id = $1"}
	args := []interface{}{userID}
	argIdx := 2

	now := time.Now().UTC()
	if dateFilter == "this_month" || dateFilter == "month" {
		whereClauses = append(whereClauses, fmt.Sprintf("EXTRACT(YEAR FROM j.date) = $%d AND EXTRACT(MONTH FROM j.date) = $%d", argIdx, argIdx+1))
		args = append(args, now.Year(), int(now.Month()))
		argIdx += 2
	} else if dateFilter == "this_year" || dateFilter == "year" {
		whereClauses = append(whereClauses, fmt.Sprintf("EXTRACT(YEAR FROM j.date) = $%d", argIdx))
		args = append(args, now.Year())
		argIdx++
	}

	if search != "" {
		sPattern := "%" + strings.ToLower(search) + "%"
		searchClause := fmt.Sprintf(`(
			LOWER(COALESCE(j.content, '')) LIKE $%d
			OR LOWER(j.date::text) LIKE $%d
			OR EXISTS (
				SELECT 1 FROM journal_sections js
				JOIN field_values fv ON fv.section_id = js.id
				WHERE js.journal_id = j.id AND LOWER(COALESCE(fv.value, '')) LIKE $%d
			)
		)`, argIdx, argIdx, argIdx)
		whereClauses = append(whereClauses, searchClause)
		args = append(args, sPattern)
		argIdx++
	}

	whereSQL := strings.Join(whereClauses, " AND ")

	countQuery := fmt.Sprintf("SELECT COUNT(*) FROM journals j WHERE %s", whereSQL)
	var total int64
	if err := s.pool.QueryRow(ctx, countQuery, args...).Scan(&total); err != nil {
		return nil, fmt.Errorf("count journals: %w", err)
	}

	orderSQL := "ORDER BY j.date DESC, j.id DESC"
	if sortOrder == "asc" || sortOrder == "oldest" {
		orderSQL = "ORDER BY j.date ASC, j.id ASC"
	}

	offset := (page - 1) * perPage
	query := fmt.Sprintf(`
		SELECT j.uuid::text, j.user_id, j.date, j.content, j.created_at
		FROM journals j
		WHERE %s
		%s
		LIMIT $%d OFFSET $%d
	`, whereSQL, orderSQL, argIdx, argIdx+1)
	queryArgs := append(args, perPage, offset)

	rows, err := s.pool.Query(ctx, query, queryArgs...)
	if err != nil {
		return nil, fmt.Errorf("query journals: %w", err)
	}
	defer rows.Close()

	items := make([]models.JournalResponse, 0)
	for rows.Next() {
		var j models.JournalResponse
		if err := rows.Scan(&j.UUID, &j.UserID, &j.Date, &j.Content, &j.CreatedAt); err != nil {
			return nil, fmt.Errorf("scan journal: %w", err)
		}
		items = append(items, j)
	}

	totalPages := 1
	if perPage > 0 {
		totalPages = int(math.Ceil(float64(total) / float64(perPage)))
		if totalPages < 1 {
			totalPages = 1
		}
	}

	return &models.JournalListResponse{
		Items:      items,
		Total:      total,
		Page:       page,
		PerPage:    perPage,
		TotalPages: totalPages,
	}, nil
}

func (s *JournalService) GetJournalDetail(ctx context.Context, userID int, journalUUID string) (*models.JournalDetailResponse, error) {
	var jID int64
	var res models.JournalDetailResponse
	res.Sections = make([]models.SectionDetailResponse, 0)

	err := s.pool.QueryRow(ctx, `
		SELECT id, uuid::text, date, content
		FROM journals
		WHERE uuid = $1 AND user_id = $2
	`, journalUUID, userID).Scan(&jID, &res.UUID, &res.Date, &res.Content)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrJournalNotFound
		}
		return nil, fmt.Errorf("get journal: %w", err)
	}

	secRows, err := s.pool.Query(ctx, `
		SELECT js.id, js.uuid::text, js.name, st.uuid::text
		FROM journal_sections js
		LEFT JOIN section_templates st ON st.id = js.template_id
		WHERE js.journal_id = $1
		ORDER BY js.id ASC
	`, jID)
	if err != nil {
		return nil, fmt.Errorf("query sections: %w", err)
	}
	defer secRows.Close()

	type secMeta struct {
		id      int64
		section models.SectionDetailResponse
	}
	var sectionMetas []secMeta

	for secRows.Next() {
		var sm secMeta
		var tmplUUID sql.NullString
		if err := secRows.Scan(&sm.id, &sm.section.UUID, &sm.section.Name, &tmplUUID); err != nil {
			return nil, fmt.Errorf("scan section: %w", err)
		}
		if tmplUUID.Valid {
			sm.section.TemplateUUID = &tmplUUID.String
		}
		sm.section.FieldValues = make([]models.FieldValueDetailResponse, 0)
		sectionMetas = append(sectionMetas, sm)
	}

	for i := range sectionMetas {
		fvRows, err := s.pool.Query(ctx, `
			SELECT uuid::text, label, field_type, value
			FROM field_values
			WHERE section_id = $1
			ORDER BY "order" ASC, id ASC
		`, sectionMetas[i].id)
		if err != nil {
			return nil, fmt.Errorf("query field values: %w", err)
		}

		for fvRows.Next() {
			var fv models.FieldValueDetailResponse
			if err := fvRows.Scan(&fv.UUID, &fv.Label, &fv.FieldType, &fv.Value); err != nil {
				fvRows.Close()
				return nil, fmt.Errorf("scan field value: %w", err)
			}
			sectionMetas[i].section.FieldValues = append(sectionMetas[i].section.FieldValues, fv)
		}
		fvRows.Close()
		res.Sections = append(res.Sections, sectionMetas[i].section)
	}

	return &res, nil
}

func (s *JournalService) GetLatestJournalStructure(ctx context.Context, userID int) (*models.LatestStructureResponse, error) {
	var jID int64
	err := s.pool.QueryRow(ctx, `
		SELECT id FROM journals
		WHERE user_id = $1
		ORDER BY date DESC
		LIMIT 1
	`, userID).Scan(&jID)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return &models.LatestStructureResponse{Sections: []models.SectionStructure{}}, nil
		}
		return nil, fmt.Errorf("get latest journal: %w", err)
	}

	secRows, err := s.pool.Query(ctx, `
		SELECT js.id, js.name, st.uuid::text
		FROM journal_sections js
		JOIN section_templates st ON st.id = js.template_id
		WHERE js.journal_id = $1 AND st.status::text ILIKE 'active'
		ORDER BY js.id ASC
	`, jID)
	if err != nil {
		return nil, fmt.Errorf("query latest sections: %w", err)
	}
	defer secRows.Close()

	type secMeta struct {
		id   int64
		name string
		uuid string
	}
	var sections []secMeta
	for secRows.Next() {
		var sm secMeta
		if err := secRows.Scan(&sm.id, &sm.name, &sm.uuid); err != nil {
			return nil, fmt.Errorf("scan latest section: %w", err)
		}
		sections = append(sections, sm)
	}

	activeSections := make([]models.SectionStructure, 0, len(sections))
	for _, sec := range sections {
		fvRows, err := s.pool.Query(ctx, `
			SELECT label, field_type
			FROM field_values
			WHERE section_id = $1
			ORDER BY "order" ASC, id ASC
		`, sec.id)
		if err != nil {
			return nil, fmt.Errorf("query latest field values: %w", err)
		}

		fields := make([]models.FieldStructure, 0)
		for fvRows.Next() {
			var f models.FieldStructure
			if err := fvRows.Scan(&f.Label, &f.FieldType); err != nil {
				fvRows.Close()
				return nil, fmt.Errorf("scan latest field structure: %w", err)
			}
			f.Value = nil
			fields = append(fields, f)
		}
		fvRows.Close()

		activeSections = append(activeSections, models.SectionStructure{
			Name:         sec.name,
			TemplateUUID: sec.uuid,
			Fields:       fields,
		})
	}

	return &models.LatestStructureResponse{Sections: activeSections}, nil
}

func (s *JournalService) GetTemplates(ctx context.Context, userID int) ([]models.TemplateResponse, error) {
	rows, err := s.pool.Query(ctx, `
		SELECT id, uuid::text, name, description, status
		FROM section_templates
		WHERE user_id = $1 AND status::text ILIKE 'active'
		ORDER BY id ASC
	`, userID)
	if err != nil {
		return nil, fmt.Errorf("query templates: %w", err)
	}
	defer rows.Close()

	type tMeta struct {
		id   int64
		resp models.TemplateResponse
	}
	var tMetas []tMeta
	for rows.Next() {
		var tm tMeta
		if err := rows.Scan(&tm.id, &tm.resp.UUID, &tm.resp.Name, &tm.resp.Description, &tm.resp.Status); err != nil {
			return nil, fmt.Errorf("scan template: %w", err)
		}
		tm.resp.Fields = make([]models.SectionFieldResponse, 0)
		tMetas = append(tMetas, tm)
	}

	result := make([]models.TemplateResponse, 0, len(tMetas))
	for _, tm := range tMetas {
		fRows, err := s.pool.Query(ctx, `
			SELECT uuid::text, label, field_type, placeholder, required, "order"
			FROM section_fields
			WHERE template_id = $1
			ORDER BY "order" ASC, id ASC
		`, tm.id)
		if err != nil {
			return nil, fmt.Errorf("query section fields: %w", err)
		}

		for fRows.Next() {
			var f models.SectionFieldResponse
			if err := fRows.Scan(&f.UUID, &f.Label, &f.FieldType, &f.Placeholder, &f.Required, &f.Order); err != nil {
				fRows.Close()
				return nil, fmt.Errorf("scan section field: %w", err)
			}
			tm.resp.Fields = append(tm.resp.Fields, f)
		}
		fRows.Close()
		result = append(result, tm.resp)
	}

	return result, nil
}

func (s *JournalService) DeleteTemplate(ctx context.Context, userID int, templateUUID string) error {
	cmd, err := s.pool.Exec(ctx, `
		UPDATE section_templates
		SET status = (SELECT e FROM unnest(enum_range(NULL::template_status)) e WHERE e::text ILIKE 'terminated' LIMIT 1)
		WHERE uuid = $1 AND user_id = $2
	`, templateUUID, userID)
	if err != nil {
		return fmt.Errorf("delete template: %w", err)
	}
	if cmd.RowsAffected() == 0 {
		return ErrTemplateNotFound
	}
	return nil
}

func (s *JournalService) CreateJournal(ctx context.Context, userID int, req models.JournalCreate) (*models.JournalResponse, error) {
	if (req.TemplateUUID == nil || *req.TemplateUUID == "") && len(req.Sections) == 0 && (req.Content == nil || *req.Content == "") {
		return nil, fmt.Errorf("%w: journal must have content, template_uuid, or sections", ErrInvalidInput)
	}

	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return nil, fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback(ctx)

	jUUID := uuid.New().String()
	now := time.Now().UTC()
	var jID int64

	err = tx.QueryRow(ctx, `
		INSERT INTO journals (uuid, user_id, date, content, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $5)
		RETURNING id
	`, jUUID, userID, req.Date.UTC(), req.Content, now).Scan(&jID)
	if err != nil {
		return nil, fmt.Errorf("insert journal: %w", err)
	}

	type existingField struct {
		id        int64
		uuid      string
		order     int
		label     string
		fieldType string
	}

	for _, sec := range req.Sections {
		var tID *int64
		reusable := true
		if sec.Reusable != nil {
			reusable = *sec.Reusable
		}

		// Map to store internal field IDs per field_value
		fieldIDMap := make([]*int64, len(sec.FieldValues))

		if sec.TemplateUUID != nil && *sec.TemplateUUID != "" {
			var foundID int64
			err := tx.QueryRow(ctx, `
				SELECT id FROM section_templates
				WHERE uuid::text = $1 AND user_id = $2
			`, *sec.TemplateUUID, userID).Scan(&foundID)
			if err != nil && !errors.Is(err, pgx.ErrNoRows) {
				return nil, fmt.Errorf("query section_template: %w", err)
			}
			if err == nil {
				tID = &foundID
				// Load template fields
				fRows, err := tx.Query(ctx, `
					SELECT id, uuid::text, "order", label, field_type::text
					FROM section_fields
					WHERE template_id = $1
					ORDER BY "order" ASC
				`, foundID)
				if err != nil {
					return nil, fmt.Errorf("query section_fields: %w", err)
				}

				var tFields []existingField
				maxOrder := -1
				for fRows.Next() {
					var ef existingField
					if err := fRows.Scan(&ef.id, &ef.uuid, &ef.order, &ef.label, &ef.fieldType); err == nil {
						tFields = append(tFields, ef)
						if ef.order > maxOrder {
							maxOrder = ef.order
						}
					}
				}
				fRows.Close()

				for idx, fv := range sec.FieldValues {
					if fv.FieldUUID == nil || *fv.FieldUUID == "" {
						maxOrder++
						newFUUID := uuid.New().String()
						var newFID int64
						err := tx.QueryRow(ctx, `
							INSERT INTO section_fields (uuid, template_id, label, field_type, placeholder, required, "order")
							VALUES ($1, $2, $3, (SELECT e FROM unnest(enum_range(NULL::field_type)) e WHERE e::text ILIKE $4 LIMIT 1), NULL, false, $5)
							RETURNING id
						`, newFUUID, foundID, fv.Label, fv.FieldType, maxOrder).Scan(&newFID)
						if err != nil {
							return nil, fmt.Errorf("insert template field: %w", err)
						}
						fieldIDMap[idx] = &newFID
					} else {
						for _, ef := range tFields {
							if ef.uuid == *fv.FieldUUID {
								fid := ef.id
								fieldIDMap[idx] = &fid
								break
							}
						}
					}
				}

				if !reusable {
					_, err = tx.Exec(ctx, `
						UPDATE section_templates
						SET status = (SELECT e FROM unnest(enum_range(NULL::template_status)) e WHERE e::text ILIKE 'terminated' LIMIT 1)
						WHERE id = $1
					`, foundID)
					if err != nil {
						return nil, fmt.Errorf("terminate template: %w", err)
					}
				}
			}
		} else if reusable {
			// Create new template with explicit status and non-null defaults
			newTUUID := uuid.New().String()
			desc := fmt.Sprintf("Created from journal %d", jID)
			var newTID int64
			err := tx.QueryRow(ctx, `
				INSERT INTO section_templates (uuid, user_id, name, description, status)
				VALUES ($1, $2, $3, $4, (SELECT e FROM unnest(enum_range(NULL::template_status)) e WHERE e::text ILIKE 'active' LIMIT 1))
				RETURNING id
			`, newTUUID, userID, sec.Name, desc).Scan(&newTID)
			if err != nil {
				return nil, fmt.Errorf("insert section_template: %w", err)
			}
			tID = &newTID

			for idx, fv := range sec.FieldValues {
				newFUUID := uuid.New().String()
				var newFID int64
				err := tx.QueryRow(ctx, `
					INSERT INTO section_fields (uuid, template_id, label, field_type, placeholder, required, "order")
					VALUES ($1, $2, $3, (SELECT e FROM unnest(enum_range(NULL::field_type)) e WHERE e::text ILIKE $4 LIMIT 1), NULL, false, $5)
					RETURNING id
				`, newFUUID, newTID, fv.Label, fv.FieldType, idx).Scan(&newFID)
				if err != nil {
					return nil, fmt.Errorf("insert section_field: %w", err)
				}
				fieldIDMap[idx] = &newFID
			}
		}

		secUUID := uuid.New().String()
		var secID int64
		err = tx.QueryRow(ctx, `
			INSERT INTO journal_sections (uuid, journal_id, template_id, name)
			VALUES ($1, $2, $3, $4)
			RETURNING id
		`, secUUID, jID, tID, sec.Name).Scan(&secID)
		if err != nil {
			return nil, fmt.Errorf("insert journal_section: %w", err)
		}

		for idx, fv := range sec.FieldValues {
			fvUUID := uuid.New().String()
			fid := fieldIDMap[idx]
			_, err = tx.Exec(ctx, `
				INSERT INTO field_values (uuid, section_id, field_id, label, field_type, value, "order")
				VALUES ($1, $2, $3, $4, $5, $6, $7)
			`, fvUUID, secID, fid, fv.Label, fv.FieldType, fv.Value, idx)
			if err != nil {
				return nil, fmt.Errorf("insert field_value: %w", err)
			}
		}
	}

	if err := tx.Commit(ctx); err != nil {
		return nil, fmt.Errorf("commit tx: %w", err)
	}

	return &models.JournalResponse{
		UUID:      jUUID,
		UserID:    userID,
		Date:      req.Date.UTC(),
		Content:   req.Content,
		CreatedAt: now,
	}, nil
}

func (s *JournalService) UpdateJournal(ctx context.Context, userID int, journalUUID string, req models.JournalUpdate) error {
	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback(ctx)

	var jID int64
	err = tx.QueryRow(ctx, `
		SELECT id FROM journals
		WHERE uuid = $1 AND user_id = $2
	`, journalUUID, userID).Scan(&jID)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return ErrJournalNotFound
		}
		return fmt.Errorf("query journal: %w", err)
	}

	hasUpdates := false
	if req.Date != nil {
		_, err := tx.Exec(ctx, `UPDATE journals SET date = $1 WHERE id = $2`, req.Date.UTC(), jID)
		if err != nil {
			return fmt.Errorf("update date: %w", err)
		}
		hasUpdates = true
	}
	if req.Content != nil {
		_, err := tx.Exec(ctx, `UPDATE journals SET content = $1 WHERE id = $2`, *req.Content, jID)
		if err != nil {
			return fmt.Errorf("update content: %w", err)
		}
		hasUpdates = true
	}

	for _, sec := range req.Sections {
		var secID int64
		err := tx.QueryRow(ctx, `
			SELECT id FROM journal_sections
			WHERE uuid = $1 AND journal_id = $2
		`, sec.UUID, jID).Scan(&secID)
		if err != nil {
			continue
		}

		if sec.Name != nil {
			_, err = tx.Exec(ctx, `UPDATE journal_sections SET name = $1 WHERE id = $2`, *sec.Name, secID)
			if err != nil {
				return fmt.Errorf("update section name: %w", err)
			}
			hasUpdates = true
		}

		for _, fv := range sec.FieldValues {
			var fieldID sql.NullInt64
			var fvID int64
			err := tx.QueryRow(ctx, `
				SELECT id, field_id FROM field_values
				WHERE uuid = $1 AND section_id = $2
			`, fv.UUID, secID).Scan(&fvID, &fieldID)
			if err != nil {
				continue
			}

			if fv.Value != nil {
				_, err = tx.Exec(ctx, `UPDATE field_values SET value = $1 WHERE id = $2`, *fv.Value, fvID)
				if err != nil {
					return fmt.Errorf("update field value: %w", err)
				}
				hasUpdates = true
			}

			if fv.Order != nil {
				_, err = tx.Exec(ctx, `UPDATE field_values SET "order" = $1 WHERE id = $2`, *fv.Order, fvID)
				if err != nil {
					return fmt.Errorf("update field order: %w", err)
				}
				if fieldID.Valid {
					_, _ = tx.Exec(ctx, `UPDATE section_fields SET "order" = $1 WHERE id = $2`, *fv.Order, fieldID.Int64)
				}
				hasUpdates = true
			}
		}
	}

	if hasUpdates {
		_, _ = tx.Exec(ctx, `UPDATE journals SET updated_at = NOW() WHERE id = $1`, jID)
	}

	return tx.Commit(ctx)
}

func (s *JournalService) DeleteJournal(ctx context.Context, userID int, journalUUID string) error {
	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback(ctx)

	var jID int64
	err = tx.QueryRow(ctx, `
		SELECT id FROM journals
		WHERE uuid = $1 AND user_id = $2
	`, journalUUID, userID).Scan(&jID)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return ErrJournalNotFound
		}
		return fmt.Errorf("find journal: %w", err)
	}

	_, err = tx.Exec(ctx, `
		DELETE FROM field_values
		WHERE section_id IN (SELECT id FROM journal_sections WHERE journal_id = $1)
	`, jID)
	if err != nil {
		return fmt.Errorf("delete field_values: %w", err)
	}

	_, err = tx.Exec(ctx, `DELETE FROM journal_sections WHERE journal_id = $1`, jID)
	if err != nil {
		return fmt.Errorf("delete journal_sections: %w", err)
	}

	_, err = tx.Exec(ctx, `DELETE FROM journals WHERE id = $1`, jID)
	if err != nil {
		return fmt.Errorf("delete journal: %w", err)
	}

	return tx.Commit(ctx)
}

func (s *JournalService) GetJournalAnalytics(ctx context.Context, userID int) (*models.JournalAnalyticsResponse, error) {
	rows, err := s.pool.Query(ctx, `
		SELECT date, content, created_at, updated_at
		FROM journals
		WHERE user_id = $1
		ORDER BY date DESC
	`, userID)
	if err != nil {
		return nil, fmt.Errorf("query journals for analytics: %w", err)
	}
	defer rows.Close()

	type jRecord struct {
		date      time.Time
		content   *string
		createdAt time.Time
		updatedAt time.Time
	}
	var journals []jRecord
	totalWords := 0
	for rows.Next() {
		var j jRecord
		if err := rows.Scan(&j.date, &j.content, &j.createdAt, &j.updatedAt); err != nil {
			return nil, fmt.Errorf("scan journal analytics: %w", err)
		}
		if j.content != nil {
			totalWords += len(strings.Fields(*j.content))
		}
		journals = append(journals, j)
	}

	tRows, err := s.pool.Query(ctx, `
		SELECT created_at, updated_at
		FROM thoughts
		WHERE user_id = $1
	`, userID)
	if err != nil {
		return nil, fmt.Errorf("query thoughts for analytics: %w", err)
	}
	defer tRows.Close()

	type tRecord struct {
		createdAt time.Time
		updatedAt time.Time
	}
	var thoughts []tRecord
	for tRows.Next() {
		var t tRecord
		if err := tRows.Scan(&t.createdAt, &t.updatedAt); err != nil {
			return nil, fmt.Errorf("scan thought analytics: %w", err)
		}
		thoughts = append(thoughts, t)
	}

	dailyMap := make(map[string]*models.DailyActivity)

	getDaily := func(day string) *models.DailyActivity {
		if d, ok := dailyMap[day]; ok {
			return d
		}
		d := &models.DailyActivity{Date: day}
		dailyMap[day] = d
		return d
	}

	toDayStr := func(t time.Time) string {
		if t.IsZero() {
			return ""
		}
		return t.Format("2006-01-02")
	}

	for _, j := range journals {
		createdDay := toDayStr(j.createdAt)
		if createdDay == "" {
			createdDay = toDayStr(j.date)
		}
		editedDay := toDayStr(j.updatedAt)

		if createdDay != "" {
			getDaily(createdDay).JournalCreated++
		}
		if editedDay != "" && editedDay != createdDay {
			getDaily(editedDay).JournalEdited++
		}
	}

	for _, t := range thoughts {
		createdDay := toDayStr(t.createdAt)
		editedDay := toDayStr(t.updatedAt)

		if createdDay != "" {
			getDaily(createdDay).ThoughtCreated++
		}
		if editedDay != "" && editedDay != createdDay {
			getDaily(editedDay).ThoughtEdited++
		}
	}

	var days []string
	for d := range dailyMap {
		days = append(days, d)
	}
	sort.Strings(days)

	dailyCounts := make([]models.DailyActivity, 0, len(days))
	for _, day := range days {
		da := dailyMap[day]
		totalActions := da.JournalCreated + da.JournalEdited + da.ThoughtCreated + da.ThoughtEdited
		da.Count = totalActions
		da.TotalActions = totalActions
		dailyCounts = append(dailyCounts, *da)
	}

	// Calculate streaks based on unique journal dates
	uniqueDateMap := make(map[string]bool)
	for _, j := range journals {
		dStr := toDayStr(j.date)
		if dStr != "" {
			uniqueDateMap[dStr] = true
		}
	}

	var uniqueDates []string
	for d := range uniqueDateMap {
		uniqueDates = append(uniqueDates, d)
	}
	// Sort descending
	sort.Slice(uniqueDates, func(i, j int) bool {
		return uniqueDates[i] > uniqueDates[j]
	})

	currentStreak := 0
	longestStreak := 0

	if len(uniqueDates) > 0 {
		tempLongest := 1
		for i := 0; i < len(uniqueDates)-1; i++ {
			d1, _ := time.Parse("2006-01-02", uniqueDates[i])
			d2, _ := time.Parse("2006-01-02", uniqueDates[i+1])
			if int(d1.Sub(d2).Hours()/24) == 1 {
				tempLongest++
			} else {
				if tempLongest > longestStreak {
					longestStreak = tempLongest
				}
				tempLongest = 1
			}
		}
		if tempLongest > longestStreak {
			longestStreak = tempLongest
		}

		todayUTC := time.Now().UTC().Format("2006-01-02")
		yesterdayUTC := time.Now().UTC().AddDate(0, 0, -1).Format("2006-01-02")

		if uniqueDates[0] == todayUTC || uniqueDates[0] == yesterdayUTC {
			currentStreak = 1
			for i := 0; i < len(uniqueDates)-1; i++ {
				d1, _ := time.Parse("2006-01-02", uniqueDates[i])
				d2, _ := time.Parse("2006-01-02", uniqueDates[i+1])
				if int(d1.Sub(d2).Hours()/24) == 1 {
					currentStreak++
				} else {
					break
				}
			}
		}
	}

	return &models.JournalAnalyticsResponse{
		TotalJournals: len(journals),
		TotalWords:    totalWords,
		CurrentStreak: currentStreak,
		LongestStreak: longestStreak,
		TotalThoughts: len(thoughts),
		DailyActivity: dailyCounts,
	}, nil
}
