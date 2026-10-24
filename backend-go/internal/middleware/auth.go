package middleware

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sadguruchenu/thoughtsgo/internal/models"
	"github.com/sadguruchenu/thoughtsgo/internal/service"
)

type contextKey string

const userContextKey = contextKey("authenticated_user")

// RespondJSON is a helper to write JSON error or success responses.
func RespondJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

// ErrorResponse matches FastAPI's standard {"detail": "..."} format.
type ErrorResponse struct {
	Detail string `json:"detail"`
}

// RespondError writes a standard FastAPI-compatible {"detail": "..."} JSON error.
func RespondError(w http.ResponseWriter, status int, detail string) {
	RespondJSON(w, status, ErrorResponse{Detail: detail})
}

// RequireAuth extracts and validates the Bearer JWT token from the Authorization header,
// queries the user from Postgres, and injects the User into the request context.
func RequireAuth(secretKey string, pool *pgxpool.Pool) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			authHeader := r.Header.Get("Authorization")
			if authHeader == "" {
				RespondError(w, http.StatusUnauthorized, "Not authenticated")
				return
			}

			parts := strings.SplitN(authHeader, " ", 2)
			if len(parts) != 2 || !strings.EqualFold(parts[0], "bearer") {
				RespondError(w, http.StatusUnauthorized, "Invalid token")
				return
			}

			tokenString := parts[1]
			claims, err := service.VerifyToken(secretKey, tokenString)
			if err != nil {
				if err == service.ErrTokenExpired {
					RespondError(w, http.StatusUnauthorized, "Signature has expired")
					return
				}
				RespondError(w, http.StatusUnauthorized, "Invalid token")
				return
			}

			email, ok := claims["sub"].(string)
			if !ok || email == "" {
				RespondError(w, http.StatusUnauthorized, "Invalid token payload")
				return
			}

			user, err := service.GetUserByEmail(r.Context(), pool, email)
			if err != nil {
				RespondError(w, http.StatusInternalServerError, "Database error")
				return
			}
			if user == nil {
				RespondError(w, http.StatusUnauthorized, "User not found")
				return
			}

			ctx := context.WithValue(r.Context(), userContextKey, user)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// RequireAdmin verifies that the authenticated user in context has the ADMIN role.
func RequireAdmin(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		user := UserFromContext(r.Context())
		if user == nil || user.Role != models.RoleAdmin {
			RespondError(w, http.StatusForbidden, "Admin access required")
			return
		}
		next.ServeHTTP(w, r)
	})
}

// UserFromContext retrieves the authenticated User injected by RequireAuth.
func UserFromContext(ctx context.Context) *models.User {
	u, _ := ctx.Value(userContextKey).(*models.User)
	return u
}
