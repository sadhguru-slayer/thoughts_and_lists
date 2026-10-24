package models

import "time"

type Journal struct {
	ID        int64     `json:"-"`
	UUID      string    `json:"uuid"`
	UserID    int       `json:"user_id"`
	Date      time.Time `json:"date"`
	Content   *string   `json:"content"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type JournalResponse struct {
	UUID      string    `json:"uuid"`
	UserID    int       `json:"user_id"`
	Date      time.Time `json:"date"`
	Content   *string   `json:"content"`
	CreatedAt time.Time `json:"created_at"`
}

type FieldValueDetailResponse struct {
	UUID      string  `json:"uuid"`
	Label     string  `json:"label"`
	FieldType string  `json:"field_type"`
	Value     *string `json:"value"`
}

type SectionDetailResponse struct {
	UUID        string                     `json:"uuid"`
	Name        string                     `json:"name"`
	TemplateUUID *string                   `json:"template_uuid"`
	FieldValues []FieldValueDetailResponse `json:"field_values"`
}

type JournalDetailResponse struct {
	UUID     string                  `json:"uuid"`
	Date     time.Time               `json:"date"`
	Content  *string                 `json:"content"`
	Sections []SectionDetailResponse `json:"sections"`
}

type FieldStructure struct {
	Label     string  `json:"label"`
	FieldType string  `json:"field_type"`
	Value     *string `json:"value"`
}

type SectionStructure struct {
	Name         string           `json:"name"`
	TemplateUUID string           `json:"template_uuid"`
	Fields       []FieldStructure `json:"fields"`
}

type LatestStructureResponse struct {
	Sections []SectionStructure `json:"sections"`
}

type JournalListResponse struct {
	Items      []JournalResponse `json:"items"`
	Total      int64             `json:"total"`
	Page       int               `json:"page"`
	PerPage    int               `json:"per_page"`
	TotalPages int               `json:"total_pages"`
}

type FieldValueCreate struct {
	Label     string  `json:"label"`
	FieldType string  `json:"field_type"`
	Value     *string `json:"value"`
	FieldUUID *string `json:"field_uuid"`
}

type JournalSectionCreate struct {
	Name         string             `json:"name"`
	TemplateUUID *string            `json:"template_uuid"`
	Reusable     *bool              `json:"reusable"`
	FieldValues  []FieldValueCreate `json:"field_values"`
}

type JournalCreate struct {
	Date         FlexibleTime           `json:"date"`
	Content      *string                `json:"content"`
	TemplateUUID *string                `json:"template_uuid"`
	Sections     []JournalSectionCreate `json:"sections"`
}

type FieldValueUpdate struct {
	UUID  string  `json:"uuid"`
	Value *string `json:"value"`
	Order *int    `json:"order"`
}

type JournalSectionUpdate struct {
	UUID        string             `json:"uuid"`
	Name        *string            `json:"name"`
	FieldValues []FieldValueUpdate `json:"field_values"`
}

type JournalUpdate struct {
	Date     *FlexibleTime          `json:"date"`
	Content  *string                `json:"content"`
	Sections []JournalSectionUpdate `json:"sections"`
}

type SectionFieldResponse struct {
	UUID        string  `json:"uuid"`
	Label       string  `json:"label"`
	FieldType   string  `json:"field_type"`
	Placeholder *string `json:"placeholder"`
	Required    bool    `json:"required"`
	Order       int     `json:"order"`
}

type TemplateResponse struct {
	UUID        string                 `json:"uuid"`
	Name        string                 `json:"name"`
	Description *string                `json:"description"`
	Status      string                 `json:"status"`
	Fields      []SectionFieldResponse `json:"fields"`
}

type DailyActivity struct {
	Date           string `json:"date"`
	Count          int    `json:"count"`
	TotalActions   int    `json:"total_actions"`
	JournalCreated int    `json:"journal_created"`
	JournalEdited  int    `json:"journal_edited"`
	ThoughtCreated int    `json:"thought_created"`
	ThoughtEdited  int    `json:"thought_edited"`
}

type JournalAnalyticsResponse struct {
	TotalJournals int             `json:"total_journals"`
	TotalWords    int             `json:"total_words"`
	CurrentStreak int             `json:"current_streak"`
	LongestStreak int             `json:"longest_streak"`
	TotalThoughts int             `json:"total_thoughts"`
	DailyActivity []DailyActivity `json:"daily_activity"`
}
