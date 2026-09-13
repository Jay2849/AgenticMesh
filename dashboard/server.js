const { createServer } = require("http");
const { parse } = require("url");
const next = require("next");
const { Server } = require("socket.io");
const Redis = require("ioredis");

const dev = process.env.NODE_ENV !== "production";
const hostname = "0.0.0.0";
const port = parseInt(process.env.PORT || "3000", 10);
const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  const server = createServer((req, res) => {
    const parsedUrl = parse(req.url, true);
    handle(req, res, parsedUrl);
  });

  const io = new Server(server, {
    cors: {
      origin: "*",
    },
  });

  // Setup Redis Pub/Sub
  const redisUrl = process.env.UPSTASH_REDIS_URL || "redis://redis:6379/0";
  
  try {
    const redis = new Redis(redisUrl);
    
    redis.subscribe("rca-results", "remediation-status", (err, count) => {
      if (err) {
        console.error("Failed to subscribe: %s", err.message);
      } else {
        console.log(`Subscribed to ${count} Redis channels.`);
      }
    });

    redis.on("message", (channel, message) => {
      console.log(`Received message from ${channel}`);
      try {
        const data = JSON.parse(message);
        if (channel === "rca-results") {
          io.emit("incident", data);
        } else if (channel === "remediation-status") {
          io.emit("remediation", data);
        }
      } catch (e) {
        console.error("Error parsing message", e);
      }
    });
  } catch (e) {
    console.error("Redis connection failed", e);
  }

  // Handle client connections
  io.on("connection", (socket) => {
    console.log("Client connected");
    socket.on("disconnect", () => {
      console.log("Client disconnected");
    });
  });

  server.listen(port, () => {
    console.log(`> Ready on http://${hostname}:${port}`);
  });
});
