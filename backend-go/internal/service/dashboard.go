package service

import (
	"context"
	"sort"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sadguruchenu/thoughtsgo/internal/models"
)

type DashboardService struct {
	pool *pgxpool.Pool
}

func NewDashboardService(pool *pgxpool.Pool) *DashboardService {
	return &DashboardService{pool: pool}
}

func (s *DashboardService) GetDashboardData(ctx context.Context, userID int) (*models.DashboardResponse, error) {
	var totalJournals, totalThoughts, totalTasks, completedTasks int64

	_ = s.pool.QueryRow(ctx, "SELECT COUNT(*) FROM journals WHERE user_id = $1", userID).Scan(&totalJournals)
	_ = s.pool.QueryRow(ctx, "SELECT COUNT(*) FROM thoughts WHERE user_id = $1", userID).Scan(&totalThoughts)
	_ = s.pool.QueryRow(ctx, "SELECT COUNT(*) FROM tasks WHERE user_id = $1", userID).Scan(&totalTasks)
	_ = s.pool.QueryRow(ctx, "SELECT COUNT(*) FROM tasks WHERE user_id = $1 AND status = 'COMPLETED'", userID).Scan(&completedTasks)

	// Recent journals (top 5)
	jRows, err := s.pool.Query(ctx, `
		SELECT uuid::text, date, COALESCE(content, '')
		FROM journals
		WHERE user_id = $1
		ORDER BY date DESC
		LIMIT 5
	`, userID)
	recentJournals := make([]models.RecentJournal, 0)
	if err == nil {
		for jRows.Next() {
			var rj models.RecentJournal
			var content string
			if err := jRows.Scan(&rj.UUID, &rj.Date, &content); err == nil {
				rj.Title = rj.Date.Format("Jan 02, 2006")
				if len(content) > 150 {
					rj.ContentPreview = content[:150]
				} else {
					rj.ContentPreview = content
				}
				recentJournals = append(recentJournals, rj)
			}
		}
		jRows.Close()
	}

	// Recent notes (thoughts) (top 5)
	tRows, err := s.pool.Query(ctx, `
		SELECT uuid::text, title, COALESCE(content, ''), created_at
		FROM thoughts
		WHERE user_id = $1
		ORDER BY created_at DESC
		LIMIT 5
	`, userID)
	recentNotes := make([]models.RecentNote, 0)
	if err == nil {
		for tRows.Next() {
			var rn models.RecentNote
			var content string
			if err := tRows.Scan(&rn.UUID, &rn.Title, &content, &rn.CreatedAt); err == nil {
				if len(content) > 150 {
					rn.ContentPreview = content[:150]
				} else {
					rn.ContentPreview = content
				}
				recentNotes = append(recentNotes, rn)
			}
		}
		tRows.Close()
	}

	// Recent tasks (top 5 pending)
	taskRows, err := s.pool.Query(ctx, `
		SELECT uuid::text, title, priority, due_date
		FROM tasks
		WHERE user_id = $1 AND status != 'COMPLETED' AND completed = false AND is_archived = false
		ORDER BY 
			CASE priority 
				WHEN 'URGENT' THEN 0 
				WHEN 'HIGH' THEN 1 
				WHEN 'MEDIUM' THEN 2 
				WHEN 'LOW' THEN 3 
				ELSE 99 
			END ASC,
			due_date ASC NULLS LAST
		LIMIT 5
	`, userID)
	recentTasks := make([]models.RecentTask, 0)
	if err == nil {
		for taskRows.Next() {
			var rt models.RecentTask
			if err := taskRows.Scan(&rt.UUID, &rt.Title, &rt.Priority, &rt.DueDate); err == nil {
				recentTasks = append(recentTasks, rt)
			}
		}
		taskRows.Close()
	}

	// Streak calculation from all journal dates
	dRows, err := s.pool.Query(ctx, `
		SELECT date FROM journals
		WHERE user_id = $1
		ORDER BY date DESC
	`, userID)
	var allDates []time.Time
	if err == nil {
		for dRows.Next() {
			var d time.Time
			if err := dRows.Scan(&d); err == nil {
				allDates = append(allDates, d)
			}
		}
		dRows.Close()
	}

	uniqueDateMap := make(map[string]bool)
	for _, d := range allDates {
		uniqueDateMap[d.Format("2006-01-02")] = true
	}

	var uniqueDates []string
	for d := range uniqueDateMap {
		uniqueDates = append(uniqueDates, d)
	}
	sort.Slice(uniqueDates, func(i, j int) bool {
		return uniqueDates[i] > uniqueDates[j]
	})

	currentStreak := 0
	longestStreak := 0
	todayStr := time.Now().UTC().Format("2006-01-02")
	yesterdayStr := time.Now().UTC().AddDate(0, 0, -1).Format("2006-01-02")
	tomorrowStr := time.Now().UTC().AddDate(0, 0, 1).Format("2006-01-02")

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

		if uniqueDates[0] == tomorrowStr || uniqueDates[0] == todayStr || uniqueDates[0] == yesterdayStr {
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

	hasJournaledToday := uniqueDateMap[todayStr]

	return &models.DashboardResponse{
		Stats: models.DashboardStats{
			TotalJournals:  totalJournals,
			TotalWords:     0,
			CurrentStreak:  currentStreak,
			LongestStreak:  longestStreak,
			TotalThoughts:  totalThoughts,
			TotalTasks:     totalTasks,
			CompletedTasks: completedTasks,
		},
		DailyActivity:     []interface{}{},
		HasJournaledToday: hasJournaledToday,
		RecentTasks:       recentTasks,
		RecentNotes:       recentNotes,
		RecentJournals:    recentJournals,
	}, nil
}
