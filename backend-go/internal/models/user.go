package models

import (
	"time"

	"github.com/google/uuid"
)

// UserRole represents permissions level.
type UserRole string

const (
	RoleUser  UserRole = "user"
	RoleAdmin UserRole = "admin"
)

// User represents the full record in the "users" table.
type User struct {
	ID                      int        `json:"id"`
	UUID                    uuid.UUID  `json:"uuid"`
	Email                   string     `json:"email"`
	Username                string     `json:"username"`
	HashedPassword          string     `json:"-"` // Never expose in JSON!
	Role                    UserRole   `json:"role"`
	IsActive                bool       `json:"is_active"`
	CreatedAt               time.Time  `json:"created_at"`
	Timezone                string     `json:"timezone"`
	JournalReminderActive   bool       `json:"journal_reminder_active"`
	JournalReminderTime     string     `json:"journal_reminder_time"`
	LastJournalReminderDate *time.Time `json:"last_journal_reminder_date,omitempty"`
}

// UserOut is the public response representation matching FastAPI's UserOut schema.
type UserOut struct {
	UUID                  uuid.UUID `json:"uuid"`
	Username              string    `json:"username"`
	Email                 string    `json:"email"`
	Role                  UserRole  `json:"role"`
	CreatedAt             time.Time `json:"created_at"`
	Timezone              string    `json:"timezone"`
	JournalReminderActive bool      `json:"journal_reminder_active"`
	JournalReminderTime   *string   `json:"journal_reminder_time"`
}

// ToUserOut maps a User database model to the public UserOut API response.
func (u *User) ToUserOut() UserOut {
	var reminderTime *string
	if u.JournalReminderTime != "" {
		t := u.JournalReminderTime
		reminderTime = &t
	}
	return UserOut{
		UUID:                  u.UUID,
		Username:              u.Username,
		Email:                 u.Email,
		Role:                  u.Role,
		CreatedAt:             u.CreatedAt,
		Timezone:              u.Timezone,
		JournalReminderActive: u.JournalReminderActive,
		JournalReminderTime:   reminderTime,
	}
}

// TokenResponse represents OAuth2 / JWT authentication response.
type TokenResponse struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	TokenType    string `json:"token_type"`
}

// RegisterResponse represents the response when a user registers.
type RegisterResponse struct {
	Message      string   `json:"message"`
	User         UserOut  `json:"user"`
	AccessToken  string   `json:"access_token"`
	RefreshToken string   `json:"refresh_token"`
	TokenType    string   `json:"token_type"`
}

// OTPRequest represents incoming request to send an OTP.
type OTPRequest struct {
	Email string `json:"email"`
}

// OTPVerify represents incoming request to verify an OTP.
type OTPVerify struct {
	Email string `json:"email"`
	OTP   string `json:"otp"`
}

// RegisterPasswordRequest represents password payload during registration.
type RegisterPasswordRequest struct {
	Password string   `json:"password"`
	Role     UserRole `json:"role"`
}

// ResetPasswordRequest represents payload to set a new password.
type ResetPasswordRequest struct {
	NewPassword string `json:"new_password"`
}

// UserSettingsUpdate represents payload to update preferences.
type UserSettingsUpdate struct {
	Timezone              *string `json:"timezone"`
	JournalReminderActive *bool   `json:"journal_reminder_active"`
	JournalReminderTime   *string `json:"journal_reminder_time"`
}
