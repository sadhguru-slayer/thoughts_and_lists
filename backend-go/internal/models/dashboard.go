package models

import "time"

type DashboardStats struct {
	TotalJournals  int64 `json:"total_journals"`
	TotalWords     int   `json:"total_words"`
	CurrentStreak  int   `json:"current_streak"`
	LongestStreak  int   `json:"longest_streak"`
	TotalThoughts  int64 `json:"total_thoughts"`
	TotalTasks     int64 `json:"total_tasks"`
	CompletedTasks int64 `json:"completed_tasks"`
}

type RecentTask struct {
	UUID     string     `json:"uuid"`
	Title    string     `json:"title"`
	Priority string     `json:"priority"`
	DueDate  *time.Time `json:"due_date"`
}

type RecentNote struct {
	UUID           string    `json:"uuid"`
	Title          string    `json:"title"`
	ContentPreview string    `json:"content_preview"`
	CreatedAt      time.Time `json:"created_at"`
}

type RecentJournal struct {
	UUID           string    `json:"uuid"`
	Title          string    `json:"title"`
	Date           time.Time `json:"date"`
	ContentPreview string    `json:"content_preview"`
}

type DashboardResponse struct {
	Stats             DashboardStats  `json:"stats"`
	DailyActivity     []interface{}   `json:"daily_activity"`
	HasJournaledToday bool            `json:"has_journaled_today"`
	RecentTasks       []RecentTask    `json:"recent_tasks"`
	RecentNotes       []RecentNote    `json:"recent_notes"`
	RecentJournals    []RecentJournal `json:"recent_journals"`
}
