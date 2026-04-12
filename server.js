const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = process.env.PORT || 8080;
const API_PORT = process.env.API_PORT || 8000;

const mimeTypes = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".pdf": "application/pdf",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf"
};

const server = http.createServer((req, res) => {
    // Proxy /api/* requests to Python backend
    if (req.url.startsWith("/api/")) {
        const options = {
            hostname: "127.0.0.1",
            port: API_PORT,
            path: req.url,
            method: req.method,
            headers: { ...req.headers, host: `127.0.0.1:${API_PORT}` },
        };

        const proxy = http.request(options, (proxyRes) => {
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res, { end: true });
        });

        proxy.on("error", () => {
            res.writeHead(502, { "Content-Type": "application/json" });
            res.end('{"detail":"Chatbot backend unavailable"}');
        });

        req.pipe(proxy, { end: true });
        return;
    }

    // Serve static files
    let filePath = req.url === "/" ? "/index.html" : req.url.split("?")[0];
    filePath = path.join(__dirname, filePath);
    const ext = path.extname(filePath).toLowerCase();
    const contentType = mimeTypes[ext] || "application/octet-stream";
    fs.readFile(filePath, (err, content) => {
        if (err) {
            if (err.code === "ENOENT") {
                res.writeHead(404, { "Content-Type": "text/plain" });
                res.end("404 Not Found");
            } else {
                res.writeHead(500);
                res.end("Server Error");
            }
        } else {
            res.writeHead(200, { "Content-Type": contentType });
            res.end(content);
        }
    });
});

server.listen(PORT, () => {
    console.log("Server running on port " + PORT);
});
