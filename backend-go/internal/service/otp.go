package service

import (
	"context"
	"crypto/rand"
	"fmt"
	"math/big"
	"time"

	"github.com/redis/go-redis/v9"
)

// OTPPurpose mirrors FastAPI's OTPPurpose enum.
type OTPPurpose string

const (
	OTPLogin         OTPPurpose = "login"
	OTPPasswordReset OTPPurpose = "password_reset"
	OTPRegister      OTPPurpose = "register"
)

const (
	otpPrefix = "otp"
	otpTTL    = 600 * time.Second // 10 minutes
)

// GenerateOTP generates a cryptographically secure 6-digit numeric string.
func GenerateOTP() (string, error) {
	n, err := rand.Int(rand.Reader, big.NewInt(900000))
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("%06d", n.Int64()+100000), nil
}

// OTPKey builds the Redis key: "otp:{purpose}:{email}".
func OTPKey(purpose OTPPurpose, email string) string {
	return fmt.Sprintf("%s:%s:%s", otpPrefix, purpose, email)
}

// SaveOTP stores an OTP in Redis with a 10 minute expiration.
func SaveOTP(ctx context.Context, rdb *redis.Client, purpose OTPPurpose, email, code string) error {
	return rdb.Set(ctx, OTPKey(purpose, email), code, otpTTL).Err()
}

// GetOTP retrieves the stored OTP from Redis. Returns empty string if not found or expired.
func GetOTP(ctx context.Context, rdb *redis.Client, purpose OTPPurpose, email string) (string, error) {
	val, err := rdb.Get(ctx, OTPKey(purpose, email)).Result()
	if err == redis.Nil {
		return "", nil // Not found or expired
	}
	if err != nil {
		return "", err
	}
	return val, nil
}

// DeleteOTP removes the OTP from Redis once verified.
func DeleteOTP(ctx context.Context, rdb *redis.Client, purpose OTPPurpose, email string) error {
	return rdb.Del(ctx, OTPKey(purpose, email)).Err()
}
