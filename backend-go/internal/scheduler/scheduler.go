package scheduler

import (
	"context"
	"database/sql"
	"log"
	"time"
	_ "time/tzdata"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/sadguruchenu/thoughtsgo/internal/service"
)

type Scheduler struct {
	pool     *pgxpool.Pool
	emailSvc *service.EmailService
	stopChan chan struct{}
}

func New(pool *pgxpool.Pool, emailSvc *service.EmailService) *Scheduler {
	return &Scheduler{
		pool:     pool,
		emailSvc: emailSvc,
		stopChan: make(chan struct{}),
	}
}

// Start launches the background ticker checking reminders every minute.
func (s *Scheduler) Start() {
	go func() {
		log.Println("[scheduler] background reminder worker started (running every 1m)")
		ticker := time.NewTicker(1 * time.Minute)
		defer ticker.Stop()

		// Run once on startup
		s.checkAllReminders(context.Background())

		for {
			select {
			case <-ticker.C:
				s.checkAllReminders(context.Background())
			case <-s.stopChan:
				log.Println("[scheduler] background reminder worker stopped")
				return
			}
		}
	}()
}

// Stop terminates the scheduler goroutine.
func (s *Scheduler) Stop() {
	close(s.stopChan)
}

func (s *Scheduler) checkAllReminders(ctx context.Context) {
	nowUTC := time.Now().UTC()
	journalSent := s.checkJournalReminders(ctx, nowUTC)
	taskSent := s.checkTaskReminders(ctx, nowUTC)

	log.Printf("[scheduler] tick @ %s | reminder check complete (sent: %d journal, %d task)",
		nowUTC.Format("15:04:05 UTC"), journalSent, taskSent)
}

func (s *Scheduler) checkJournalReminders(ctx context.Context, nowUTC time.Time) int {
	sentCount := 0
	rows, err := s.pool.Query(ctx, `
		SELECT id, email, timezone, journal_reminder_time::text, last_journal_reminder_date
		FROM users
		WHERE journal_reminder_active = true AND journal_reminder_time IS NOT NULL
	`)
	if err != nil {
		log.Printf("[scheduler] error querying users for journal reminders: %v", err)
		return 0
	}
	defer rows.Close()

	type uRem struct {
		id           int
		email        string
		timezone     string
		reminderTime string
		lastDate     *time.Time
	}
	var users []uRem
	for rows.Next() {
		var u uRem
		var tz, rt sql.NullString
		if err := rows.Scan(&u.id, &u.email, &tz, &rt, &u.lastDate); err == nil {
			if tz.Valid && tz.String != "" {
				u.timezone = tz.String
			} else {
				u.timezone = "Asia/Kolkata"
			}
			if rt.Valid {
				u.reminderTime = rt.String
			}
			users = append(users, u)
		}
	}

	for _, u := range users {
		loc, err := time.LoadLocation(u.timezone)
		if err != nil {
			loc, err = time.LoadLocation("Asia/Kolkata")
			if err != nil || loc == nil {
				loc = time.UTC
			}
		}
		localNow := nowUTC.In(loc)
		todayStr := localNow.Format("2006-01-02")

		if u.lastDate != nil && u.lastDate.In(loc).Format("2006-01-02") == todayStr {
			continue // Already notified today
		}

		if len(u.reminderTime) < 5 {
			continue
		}
		remT, err := time.Parse("15:04", u.reminderTime[:5])
		if err != nil {
			continue
		}

		remDateTime := time.Date(localNow.Year(), localNow.Month(), localNow.Day(), remT.Hour(), remT.Minute(), 0, 0, loc)
		if localNow.Before(remDateTime) {
			continue // Reminder time has not arrived yet
		}

		// Check if user has already written a journal today
		var count int
		err = s.pool.QueryRow(ctx, `
			SELECT COUNT(*) FROM journals
			WHERE user_id = $1 AND (date::date = $2::date OR created_at::date = $2::date)
		`, u.id, todayStr).Scan(&count)
		if err == nil && count > 0 {
			// Already journaled today; record date so we don't alert again today
			_, _ = s.pool.Exec(ctx, `UPDATE users SET last_journal_reminder_date = $1 WHERE id = $2`, todayStr, u.id)
			continue
		}

		log.Printf("[scheduler] sending daily journal reminder to %s", u.email)
		s.emailSvc.SendJournalReminderEmail(u.email)
		sentCount++
		_, _ = s.pool.Exec(ctx, `UPDATE users SET last_journal_reminder_date = $1 WHERE id = $2`, todayStr, u.id)
	}
	return sentCount
}

func (s *Scheduler) checkTaskReminders(ctx context.Context, nowUTC time.Time) int {
	sentCount := 0
	nowCheck := nowUTC.Add(10 * time.Second)

	rows, err := s.pool.Query(ctx, `
		SELECT t.id, t.uuid::text, t.title, COALESCE(t.description, ''), t.recurrence_interval::text,
		       t.reminder_at, t.last_reminder_sent_at, u.email
		FROM tasks t
		JOIN users u ON u.id = t.user_id
		WHERE t.is_archived = false
		  AND t.status::text NOT IN ('COMPLETED', 'CANCELLED')
		  AND t.reminder_at IS NOT NULL
		  AND t.reminder_at <= $1
	`, nowCheck)
	if err != nil {
		log.Printf("[scheduler] error querying task reminders: %v", err)
		return 0
	}
	defer rows.Close()

	type tRem struct {
		id                 int
		uuid               string
		title              string
		description        string
		recurrenceInterval string
		reminderAt         time.Time
		lastReminderSentAt *time.Time
		userEmail          string
	}
	var tasks []tRem
	for rows.Next() {
		var tr tRem
		if err := rows.Scan(&tr.id, &tr.uuid, &tr.title, &tr.description, &tr.recurrenceInterval, &tr.reminderAt, &tr.lastReminderSentAt, &tr.userEmail); err != nil {
			log.Printf("[scheduler] error scanning task reminder row: %v", err)
			continue
		}
		tasks = append(tasks, tr)
	}

	if len(tasks) > 0 {
		log.Printf("[scheduler] found %d task reminder(s) due", len(tasks))
	}

	for _, task := range tasks {
		isRecurring := task.recurrenceInterval != "" && task.recurrenceInterval != "NONE"

		// Non-recurring tasks: send once only
		if !isRecurring && task.lastReminderSentAt != nil {
			continue
		}

		log.Printf("[scheduler] sending task reminder for %q to %s", task.title, task.userEmail)
		s.emailSvc.SendTaskReminderEmail(task.userEmail, task.title, task.description, task.uuid, isRecurring)
		sentCount++

		// Advance reminder_at for recurring tasks
		var nextReminderAt *time.Time
		if isRecurring {
			t := task.reminderAt
			switch task.recurrenceInterval {
			case "DAILY":
				next := t.AddDate(0, 0, 1)
				nextReminderAt = &next
			case "WEEKLY":
				next := t.AddDate(0, 0, 7)
				nextReminderAt = &next
			case "MONTHLY":
				next := t.AddDate(0, 1, 0)
				nextReminderAt = &next
			}
		}

		if nextReminderAt != nil {
			_, _ = s.pool.Exec(ctx, `
				UPDATE tasks
				SET last_reminder_sent_at = $1, reminder_at = $2
				WHERE id = $3
			`, nowUTC, *nextReminderAt, task.id)
		} else {
			_, _ = s.pool.Exec(ctx, `
				UPDATE tasks
				SET last_reminder_sent_at = $1
				WHERE id = $2
			`, nowUTC, task.id)
		}
	}
	return sentCount
}
