package auth

import (
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"

	"github.com/sadguruchenu/thoughtsgo/internal/config"
	"github.com/sadguruchenu/thoughtsgo/internal/middleware"
	"github.com/sadguruchenu/thoughtsgo/internal/models"
	"github.com/sadguruchenu/thoughtsgo/internal/service"
)

type Handler struct {
	cfg   *config.Config
	pool  *pgxpool.Pool
	rdb   *redis.Client
	email *service.EmailService
}

func NewHandler(cfg *config.Config, pool *pgxpool.Pool, rdb *redis.Client, email *service.EmailService) *Handler {
	return &Handler{
		cfg:   cfg,
		pool:  pool,
		rdb:   rdb,
		email: email,
	}
}

// Router returns a chi.Router configured with all 13 auth endpoints.
func (h *Handler) Router() chi.Router {
	r := chi.NewRouter()

	// Public routes
	r.Post("/token", h.Token)
	r.Post("/request-register-otp", h.RequestRegisterOTP)
	r.Post("/verify-register-otp", h.VerifyRegisterOTP)
	r.Post("/register", h.Register)
	r.Post("/refresh-token", h.RefreshToken)
	r.Post("/request-otp", h.RequestOTP)
	r.Post("/verify-otp", h.VerifyOTP)
	r.Post("/request-password-reset", h.RequestPasswordReset)
	r.Post("/verify-reset-otp", h.VerifyResetOTP)
	r.Post("/reset-password", h.ResetPassword)

	// Protected routes (RequireAuth)
	r.Group(func(pr chi.Router) {
		pr.Use(middleware.RequireAuth(h.cfg.SecretKey, h.pool))

		pr.Get("/me", h.GetMe)
		pr.Patch("/me/settings", h.UpdateSettings)

		// Admin-only route
		pr.With(middleware.RequireAdmin).Delete("/delete-user", h.DeleteUser)
	})

	return r
}

// 1. POST /token (OAuth2 Password Request Form)
func (h *Handler) Token(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseForm(); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid form data")
		return
	}

	username := r.FormValue("username")
	password := r.FormValue("password")

	user, err := service.GetUserByEmail(r.Context(), h.pool, username)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Database error")
		return
	}
	if user == nil {
		middleware.RespondError(w, http.StatusBadRequest, "User not exist, please register")
		return
	}

	if !service.CheckPassword(password, user.HashedPassword) {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid Credentials")
		return
	}

	accessToken, err := service.CreateAccessToken(h.cfg.SecretKey, user.Email, user.Role)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to create token")
		return
	}

	refreshToken, err := service.CreateRefreshToken(h.cfg.SecretKey, user.Email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to create refresh token")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, models.TokenResponse{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		TokenType:    "bearer",
	})
}

// 2. POST /request-register-otp
func (h *Handler) RequestRegisterOTP(w http.ResponseWriter, r *http.Request) {
	var req models.OTPRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	user, err := service.GetUserByEmail(r.Context(), h.pool, req.Email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Database error")
		return
	}
	if user != nil {
		middleware.RespondError(w, http.StatusBadRequest, "User with the email: "+req.Email+" already exists")
		return
	}

	otp, err := service.GenerateOTP()
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to generate OTP")
		return
	}

	if err := service.SaveOTP(r.Context(), h.rdb, service.OTPRegister, req.Email, otp); err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to save OTP")
		return
	}

	h.email.SendOTPEmail(req.Email, otp, service.OTPRegister)
	middleware.RespondJSON(w, http.StatusOK, map[string]string{"message": "Registration OTP sent"})
}

// 3. POST /verify-register-otp
func (h *Handler) VerifyRegisterOTP(w http.ResponseWriter, r *http.Request) {
	var req models.OTPVerify
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	user, err := service.GetUserByEmail(r.Context(), h.pool, req.Email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Database error")
		return
	}
	if user != nil {
		middleware.RespondError(w, http.StatusBadRequest, "User with the email: "+req.Email+" already exists")
		return
	}

	stored, err := service.GetOTP(r.Context(), h.rdb, service.OTPRegister, req.Email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to check OTP")
		return
	}
	if stored == "" {
		middleware.RespondError(w, http.StatusBadRequest, "OTP Expired or Not Requested")
		return
	}
	if stored != req.OTP {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid OTP")
		return
	}

	_ = service.DeleteOTP(r.Context(), h.rdb, service.OTPRegister, req.Email)

	registerToken, err := service.CreateScopedToken(h.cfg.SecretKey, req.Email, "register_verify", 10*time.Minute, "")
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to create register token")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, map[string]string{"register_token": registerToken})
}

// 4. POST /register
func (h *Handler) Register(w http.ResponseWriter, r *http.Request) {
	authHeader := r.Header.Get("Authorization")
	parts := strings.SplitN(authHeader, " ", 2)
	if len(parts) != 2 || !strings.EqualFold(parts[0], "bearer") {
		middleware.RespondError(w, http.StatusUnauthorized, "Not authenticated")
		return
	}

	claims, err := service.VerifyToken(h.cfg.SecretKey, parts[1])
	if err != nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	if scope, _ := claims["scope"].(string); scope != "register_verify" {
		middleware.RespondError(w, http.StatusForbidden, "Invalid token scope")
		return
	}

	email, _ := claims["sub"].(string)
	if email == "" {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid token")
		return
	}

	userExists, err := service.GetUserByEmail(r.Context(), h.pool, email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Database error")
		return
	}
	if userExists != nil {
		middleware.RespondError(w, http.StatusBadRequest, "User already exists")
		return
	}

	var payload models.RegisterPasswordRequest
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	newUser, err := service.CreateUser(r.Context(), h.pool, email, payload.Password, payload.Role)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to create user: "+err.Error())
		return
	}

	accessToken, err := service.CreateAccessToken(h.cfg.SecretKey, newUser.Email, newUser.Role)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to create access token")
		return
	}

	refreshToken, err := service.CreateRefreshToken(h.cfg.SecretKey, newUser.Email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to create refresh token")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, models.RegisterResponse{
		Message:      "User registered successfully",
		User:         newUser.ToUserOut(),
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		TokenType:    "bearer",
	})
}

// 5. POST /refresh-token
func (h *Handler) RefreshToken(w http.ResponseWriter, r *http.Request) {
	refreshToken := r.Header.Get("Refresh-Token")
	if refreshToken == "" {
		middleware.RespondError(w, http.StatusUnauthorized, "Refresh-Token header missing")
		return
	}

	claims, err := service.VerifyToken(h.cfg.SecretKey, refreshToken)
	if err != nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	email, _ := claims["sub"].(string)
	if email == "" {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	user, err := service.GetUserByEmail(r.Context(), h.pool, email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Database error")
		return
	}
	if user == nil {
		middleware.RespondError(w, http.StatusBadRequest, "User not exist, please register")
		return
	}

	newAccessToken, err := service.CreateAccessToken(h.cfg.SecretKey, user.Email, user.Role)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to create access token")
		return
	}

	newRefreshToken, err := service.CreateRefreshToken(h.cfg.SecretKey, user.Email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to create refresh token")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, models.TokenResponse{
		AccessToken:  newAccessToken,
		RefreshToken: newRefreshToken,
		TokenType:    "bearer",
	})
}

// 6. POST /request-otp (Login OTP)
func (h *Handler) RequestOTP(w http.ResponseWriter, r *http.Request) {
	var req models.OTPRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	user, err := service.GetUserByEmail(r.Context(), h.pool, req.Email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Database error")
		return
	}
	if user == nil {
		middleware.RespondError(w, http.StatusBadRequest, "User not found, please register")
		return
	}

	otp, err := service.GenerateOTP()
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to generate OTP")
		return
	}

	if err := service.SaveOTP(r.Context(), h.rdb, service.OTPLogin, user.Email, otp); err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to save OTP")
		return
	}

	h.email.SendOTPEmail(user.Email, otp, service.OTPLogin)
	middleware.RespondJSON(w, http.StatusOK, map[string]string{"message": "OTP sent to your email successfully"})
}

// 7. POST /verify-otp (Login OTP verify)
func (h *Handler) VerifyOTP(w http.ResponseWriter, r *http.Request) {
	var req models.OTPVerify
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	user, err := service.GetUserByEmail(r.Context(), h.pool, req.Email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Database error")
		return
	}
	if user == nil {
		middleware.RespondError(w, http.StatusBadRequest, "User not found")
		return
	}

	stored, err := service.GetOTP(r.Context(), h.rdb, service.OTPLogin, user.Email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to check OTP")
		return
	}
	if stored == "" {
		middleware.RespondError(w, http.StatusBadRequest, "OTP Expired or Not Requested")
		return
	}
	if stored != req.OTP {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid OTP")
		return
	}

	_ = service.DeleteOTP(r.Context(), h.rdb, service.OTPLogin, user.Email)

	accessToken, err := service.CreateAccessToken(h.cfg.SecretKey, user.Email, user.Role)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to create access token")
		return
	}

	refreshToken, err := service.CreateRefreshToken(h.cfg.SecretKey, user.Email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to create refresh token")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, models.TokenResponse{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		TokenType:    "bearer",
	})
}

// 8. POST /request-password-reset
func (h *Handler) RequestPasswordReset(w http.ResponseWriter, r *http.Request) {
	var req models.OTPRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	user, err := service.GetUserByEmail(r.Context(), h.pool, req.Email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Database error")
		return
	}
	if user == nil {
		middleware.RespondError(w, http.StatusBadRequest, "User not found")
		return
	}

	otp, err := service.GenerateOTP()
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to generate OTP")
		return
	}

	if err := service.SaveOTP(r.Context(), h.rdb, service.OTPPasswordReset, user.Email, otp); err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to save OTP")
		return
	}

	h.email.SendOTPEmail(user.Email, otp, service.OTPPasswordReset)
	middleware.RespondJSON(w, http.StatusOK, map[string]string{"message": "Password reset OTP sent"})
}

// 9. POST /verify-reset-otp
func (h *Handler) VerifyResetOTP(w http.ResponseWriter, r *http.Request) {
	var req models.OTPVerify
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	user, err := service.GetUserByEmail(r.Context(), h.pool, req.Email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Database error")
		return
	}
	if user == nil {
		middleware.RespondError(w, http.StatusBadRequest, "User not found")
		return
	}

	stored, err := service.GetOTP(r.Context(), h.rdb, service.OTPPasswordReset, user.Email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to check OTP")
		return
	}
	if stored == "" {
		middleware.RespondError(w, http.StatusBadRequest, "OTP Expired or Not Requested")
		return
	}
	if stored != req.OTP {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid OTP")
		return
	}

	_ = service.DeleteOTP(r.Context(), h.rdb, service.OTPPasswordReset, user.Email)

	resetToken, err := service.CreateScopedToken(h.cfg.SecretKey, user.Email, "password_reset", 10*time.Minute, user.Role)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to create reset token")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, map[string]string{"reset_token": resetToken})
}

// 10. POST /reset-password
func (h *Handler) ResetPassword(w http.ResponseWriter, r *http.Request) {
	authHeader := r.Header.Get("Authorization")
	parts := strings.SplitN(authHeader, " ", 2)
	if len(parts) != 2 || !strings.EqualFold(parts[0], "bearer") {
		middleware.RespondError(w, http.StatusUnauthorized, "Not authenticated")
		return
	}

	claims, err := service.VerifyToken(h.cfg.SecretKey, parts[1])
	if err != nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Invalid token")
		return
	}

	if scope, _ := claims["scope"].(string); scope != "password_reset" {
		middleware.RespondError(w, http.StatusForbidden, "Invalid token scope")
		return
	}

	email, _ := claims["sub"].(string)
	if email == "" {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid token")
		return
	}

	var req models.ResetPasswordRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	if err := service.UpdatePassword(r.Context(), h.pool, email, req.NewPassword); err != nil {
		if err == service.ErrUserNotFound {
			middleware.RespondError(w, http.StatusBadRequest, "User not found")
			return
		}
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to update password")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, map[string]string{"message": "Password reset successful"})
}

// 11. GET /me
func (h *Handler) GetMe(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Not authenticated")
		return
	}
	middleware.RespondJSON(w, http.StatusOK, user.ToUserOut())
}

// 12. PATCH /me/settings
func (h *Handler) UpdateSettings(w http.ResponseWriter, r *http.Request) {
	user := middleware.UserFromContext(r.Context())
	if user == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Not authenticated")
		return
	}

	var payload models.UserSettingsUpdate
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		middleware.RespondError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	updatedUser, err := service.UpdateUserSettings(r.Context(), h.pool, user.ID, payload)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to update settings: "+err.Error())
		return
	}

	middleware.RespondJSON(w, http.StatusOK, updatedUser.ToUserOut())
}

// 13. DELETE /delete-user (Admin Only)
func (h *Handler) DeleteUser(w http.ResponseWriter, r *http.Request) {
	admin := middleware.UserFromContext(r.Context())
	if admin == nil {
		middleware.RespondError(w, http.StatusUnauthorized, "Not authenticated")
		return
	}

	email := r.URL.Query().Get("email")
	if email == "" {
		middleware.RespondError(w, http.StatusBadRequest, "email query parameter is required")
		return
	}

	targetUser, err := service.GetUserByEmail(r.Context(), h.pool, email)
	if err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Database error")
		return
	}
	if targetUser == nil {
		middleware.RespondError(w, http.StatusNotFound, "User not found with mail "+email)
		return
	}

	if targetUser.ID == admin.ID {
		middleware.RespondError(w, http.StatusBadRequest, "You cannot delete your own admin account")
		return
	}

	if err := service.DeleteUser(r.Context(), h.pool, email); err != nil {
		middleware.RespondError(w, http.StatusInternalServerError, "Failed to delete user")
		return
	}

	middleware.RespondJSON(w, http.StatusOK, map[string]string{"message": "Deleted user with Email:" + email})
}
