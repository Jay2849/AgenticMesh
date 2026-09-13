FROM golang:1.22-alpine AS builder

WORKDIR /app
COPY go.mod go.sum* ./
RUN go mod download

COPY . .
RUN go mod tidy
RUN go build -o ingestion-daemon main.go

FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/ingestion-daemon .

EXPOSE 8080
CMD ["./ingestion-daemon"]
