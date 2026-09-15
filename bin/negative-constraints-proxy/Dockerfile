FROM golang:1.26.3-alpine AS build
WORKDIR /src
COPY go.mod main.go ./
RUN go build -o /out/proxy .

FROM gcr.io/distroless/static-debian12
COPY --from=build /out/proxy /proxy
EXPOSE 8080
ENTRYPOINT ["/proxy"]
