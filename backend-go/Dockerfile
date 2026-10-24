# ── Stage 1: build ───────────────────────────────────────────────────────────
# Use the official Go image just for building. The final image won't have Go.
FROM golang:1.23-alpine AS builder

# Install git (needed by `go get` for some modules)
RUN apk add --no-cache git

WORKDIR /build

# Copy dependency files first so Docker caches this layer.
# The layer is only invalidated when go.mod / go.sum change.
COPY go.mod go.sum ./
RUN go mod download

# Copy the rest of the source and build a static binary.
COPY . .
RUN CGO_ENABLED=0 GOOS=linux \
    go build -ldflags="-s -w" -o /app ./cmd/server

# ── Stage 2: run ─────────────────────────────────────────────────────────────
# Alpine gives us a tiny ~5MB runtime with /bin/sh and wget for healthchecks.
FROM alpine:3.20

RUN apk add --no-cache ca-certificates tzdata

# Copy the static binary from the builder stage
COPY --from=builder /app /app

EXPOSE 8000

ENTRYPOINT ["/app"]
