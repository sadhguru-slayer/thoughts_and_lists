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
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -ldflags="-s -w" -o /app ./cmd/server

# ── Stage 2: run ─────────────────────────────────────────────────────────────
# Scratch is an empty base image — the final container is just our binary.
# This makes the image ~10 MB vs ~300 MB for a python:slim image.
FROM scratch

# Copy the static binary from the builder stage
COPY --from=builder /app /app

# ca-certificates are needed for TLS connections (SMTP, Redis TLS, etc.)
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

EXPOSE 8001

# Run the binary directly — no shell needed
ENTRYPOINT ["/app"]
