package service

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"golang.org/x/crypto/bcrypt"

	"github.com/sadguruchenu/thoughtsgo/internal/models"
)

var (
	ErrUserNotFound      = errors.New("user not found")
	ErrUserAlreadyExists = errors.New("user already exists")
	ErrInvalidToken      = errors.New("invalid token")
	ErrTokenExpired      = errors.New("token has expired")
	ErrInvalidScope      = errors.New("invalid token scope")
)

const (
	AccessTokenDuration  = 24 * time.Hour
	RefreshTokenDuration = 7 * 24 * time.Hour
)

// HashPassword hashes a plaintext password using bcrypt.
func HashPassword(password string) (string, error) {
	bytes, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	return string(bytes), err
}

// CheckPassword compares a plaintext password with a bcrypt hash.
func CheckPassword(password, hash string) bool {
	err := bcrypt.CompareHashAndPassword([]byte(hash), []byte(password))
	return err == nil
}

// CreateAccessToken generates an access token (24 hour expiration).
func CreateAccessToken(secretKey, email string, role models.UserRole) (string, error) {
	claims := jwt.MapClaims{
		"sub":  email,
		"role": string(role),
		"exp":  time.Now().Add(AccessTokenDuration).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(secretKey))
}

// CreateRefreshToken generates a refresh token (7 day expiration).
func CreateRefreshToken(secretKey, email string) (string, error) {
	claims := jwt.MapClaims{
		"sub": email,
		"exp": time.Now().Add(RefreshTokenDuration).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(secretKey))
}

// CreateScopedToken creates a temporary token for actions like register_verify or password_reset.
func CreateScopedToken(secretKey, email, scope string, duration time.Duration, role models.UserRole) (string, error) {
	claims := jwt.MapClaims{
		"sub":   email,
		"scope": scope,
		"exp":   time.Now().Add(duration).Unix(),
	}
	if role != "" {
		claims["role"] = string(role)
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(secretKey))
}

// VerifyToken parses and validates a JWT signature and expiration.
func VerifyToken(secretKey, tokenString string) (jwt.MapClaims, error) {
	token, err := jwt.Parse(tokenString, func(t *jwt.Token) (interface{}, error) {
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", t.Header["alg"])
		}
		return []byte(secretKey), nil
	})

	if err != nil {
		if errors.Is(err, jwt.ErrTokenExpired) {
			return nil, ErrTokenExpired
		}
		return nil, ErrInvalidToken
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok || !token.Valid {
		return nil, ErrInvalidToken
	}

	return claims, nil
}

// GetUserByEmail queries a user from Postgres by email.
func GetUserByEmail(ctx context.Context, pool *pgxpool.Pool, email string) (*models.User, error) {
	query := `
		SELECT id, uuid, email, username, hashed_password, role, is_active, 
		       created_at, timezone, journal_reminder_active, 
		       COALESCE(to_char(journal_reminder_time, 'HH24:MI:SS'), '22:00:00'),
		       last_journal_reminder_date
		FROM users
		WHERE email = $1
		LIMIT 1
	`
	var u models.User
	var roleStr string
	err := pool.QueryRow(ctx, query, email).Scan(
		&u.ID, &u.UUID, &u.Email, &u.Username, &u.HashedPassword, &roleStr,
		&u.IsActive, &u.CreatedAt, &u.Timezone, &u.JournalReminderActive,
		&u.JournalReminderTime, &u.LastJournalReminderDate,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil // Not found
		}
		return nil, err
	}
	u.Role = models.UserRole(roleStr)
	return &u, nil
}

// GenerateUniqueUsername creates a clean username from email, appending hex digits if taken.
func GenerateUniqueUsername(ctx context.Context, pool *pgxpool.Pool, email string) (string, error) {
	parts := strings.Split(email, "@")
	base := strings.ToLower(parts[0])
	reg := regexp.MustCompile("[^a-z0-9_]")
	base = reg.ReplaceAllString(base, "")
	if base == "" {
		base = "user"
	}

	username := base
	for {
		var exists bool
		err := pool.QueryRow(ctx, "SELECT EXISTS(SELECT 1 FROM users WHERE username = $1)", username).Scan(&exists)
		if err != nil {
			return "", err
		}
		if !exists {
			return username, nil
		}
		b := make([]byte, 2)
		_, _ = rand.Read(b)
		username = fmt.Sprintf("%s_%s", base, hex.EncodeToString(b))
	}
}

// CreateUser inserts a newly registered user into Postgres.
func CreateUser(ctx context.Context, pool *pgxpool.Pool, email, password string, role models.UserRole) (*models.User, error) {
	username, err := GenerateUniqueUsername(ctx, pool, email)
	if err != nil {
		return nil, fmt.Errorf("generate username: %w", err)
	}

	hashed, err := HashPassword(password)
	if err != nil {
		return nil, fmt.Errorf("hash password: %w", err)
	}

	if role == "" {
		role = models.RoleUser
	}

	userUUID, err := uuid.NewV7()
	if err != nil {
		userUUID = uuid.New()
	}

	query := `
		INSERT INTO users (uuid, email, username, hashed_password, role, is_active, timezone, journal_reminder_active, journal_reminder_time)
		VALUES ($1, $2, $3, $4, $5, true, 'Asia/Kolkata', true, '22:00:00')
		RETURNING id, uuid, email, username, hashed_password, role, is_active, created_at, timezone, journal_reminder_active, to_char(journal_reminder_time, 'HH24:MI:SS')
	`

	var u models.User
	var roleStr string
	err = pool.QueryRow(ctx, query, userUUID, email, username, hashed, string(role)).Scan(
		&u.ID, &u.UUID, &u.Email, &u.Username, &u.HashedPassword, &roleStr,
		&u.IsActive, &u.CreatedAt, &u.Timezone, &u.JournalReminderActive,
		&u.JournalReminderTime,
	)
	if err != nil {
		return nil, err
	}
	u.Role = models.UserRole(roleStr)
	return &u, nil
}

// UpdatePassword updates a user's password.
func UpdatePassword(ctx context.Context, pool *pgxpool.Pool, email, newPassword string) error {
	hashed, err := HashPassword(newPassword)
	if err != nil {
		return err
	}

	tag, err := pool.Exec(ctx, "UPDATE users SET hashed_password = $1 WHERE email = $2", hashed, email)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return ErrUserNotFound
	}
	return nil
}

// UpdateUserSettings updates user timezone, journal reminder settings.
func UpdateUserSettings(ctx context.Context, pool *pgxpool.Pool, userID int, update models.UserSettingsUpdate) (*models.User, error) {
	// Build update query dynamically based on which fields are provided
	var sets []string
	var args []interface{}
	argID := 1

	if update.Timezone != nil {
		sets = append(sets, fmt.Sprintf("timezone = $%d", argID))
		args = append(args, *update.Timezone)
		argID++
	}
	if update.JournalReminderActive != nil {
		sets = append(sets, fmt.Sprintf("journal_reminder_active = $%d", argID))
		args = append(args, *update.JournalReminderActive)
		argID++
	}
	if update.JournalReminderTime != nil {
		sets = append(sets, fmt.Sprintf("journal_reminder_time = $%d", argID))
		args = append(args, *update.JournalReminderTime)
		argID++
		// Reset last_journal_reminder_date so reminder can trigger today
		sets = append(sets, "last_journal_reminder_date = NULL")
	}

	if len(sets) == 0 {
		// No updates requested, fetch current user
		return GetUserByID(ctx, pool, userID)
	}

	args = append(args, userID)
	query := fmt.Sprintf(`
		UPDATE users 
		SET %s 
		WHERE id = $%d 
		RETURNING id, uuid, email, username, hashed_password, role, is_active, 
		          created_at, timezone, journal_reminder_active, 
		          COALESCE(to_char(journal_reminder_time, 'HH24:MI:SS'), '22:00:00'),
		          last_journal_reminder_date
	`, strings.Join(sets, ", "), argID)

	var u models.User
	var roleStr string
	err := pool.QueryRow(ctx, query, args...).Scan(
		&u.ID, &u.UUID, &u.Email, &u.Username, &u.HashedPassword, &roleStr,
		&u.IsActive, &u.CreatedAt, &u.Timezone, &u.JournalReminderActive,
		&u.JournalReminderTime, &u.LastJournalReminderDate,
	)
	if err != nil {
		return nil, err
	}
	u.Role = models.UserRole(roleStr)
	return &u, nil
}

// GetUserByID queries a user by their integer primary key.
func GetUserByID(ctx context.Context, pool *pgxpool.Pool, id int) (*models.User, error) {
	query := `
		SELECT id, uuid, email, username, hashed_password, role, is_active, 
		       created_at, timezone, journal_reminder_active, 
		       COALESCE(to_char(journal_reminder_time, 'HH24:MI:SS'), '22:00:00'),
		       last_journal_reminder_date
		FROM users
		WHERE id = $1
		LIMIT 1
	`
	var u models.User
	var roleStr string
	err := pool.QueryRow(ctx, query, id).Scan(
		&u.ID, &u.UUID, &u.Email, &u.Username, &u.HashedPassword, &roleStr,
		&u.IsActive, &u.CreatedAt, &u.Timezone, &u.JournalReminderActive,
		&u.JournalReminderTime, &u.LastJournalReminderDate,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	u.Role = models.UserRole(roleStr)
	return &u, nil
}

// DeleteUser deletes a user by email.
func DeleteUser(ctx context.Context, pool *pgxpool.Pool, email string) error {
	tag, err := pool.Exec(ctx, "DELETE FROM users WHERE email = $1", email)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return ErrUserNotFound
	}
	return nil
}
