# syntax=docker/dockerfile:1

# Stage 1: Build the Go application
FROM golang:1.23-alpine AS builder

WORKDIR /build

# Download dependencies separately to improve layer caching
COPY go.mod go.sum ./

RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

# Copy application source
COPY . .

# Compile with limited parallelism to reduce peak memory usage
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 \
    GOOS=linux \
    go build -p 1 -ldflags="-s -w" -o /app ./cmd/server

# Stage 2: Minimal runtime image
FROM alpine:3.20

RUN apk add --no-cache ca-certificates tzdata

WORKDIR /

COPY --from=builder /app /app

EXPOSE 8000

ENTRYPOINT ["/app"]
