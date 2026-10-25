# syntax=docker/dockerfile:1

FROM golang:1.23-alpine AS builder

WORKDIR /build

COPY go.mod go.sum ./

RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

COPY . .

RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux \
    go build -v -ldflags="-s -w" -o /app ./cmd/server

FROM alpine:3.20

RUN apk add --no-cache ca-certificates tzdata

COPY --from=builder /app /app

EXPOSE 8000

ENTRYPOINT ["/app"]
