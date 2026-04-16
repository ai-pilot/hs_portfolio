const http = require("http");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const PORT = process.env.PORT || 8080;
const API_PORT = process.env.API_PORT || 8000;

/* ============================================================
 * Background backend bootstrap (Azure Linux only)
 * ============================================================
 * Azure Web App runs `npm start` → `node server.js`. To keep Python
 * deps working without relying on a separate startup.sh sitting next
 * to us on disk (which can get dropped by Oryx builds), we shell out
 * to bash here, detached, and let Node bind PORT immediately so the
 * Azure health probe is happy.
 *
 * Skipped on non-Azure / non-Linux so local dev is unaffected.
 */
function bootstrapBackend() {
    if (process.platform !== "linux") return;
    if (!process.env.WEBSITE_INSTANCE_ID && !process.env.WEBSITE_SITE_NAME) return;

    const script = `
        set +e
        LOG_FILE="/home/LogFiles/chatbot-bootstrap.log"
        mkdir -p /home/LogFiles
        {
            echo "=== [bg] bootstrap started at $(date) ==="
            VENV_DIR="/home/site/venv"
            BACKEND_DIR="/home/site/wwwroot/Chat Bot/backend"

            if ! python3 -m pip --version > /dev/null 2>&1; then
                echo "[bg] installing python3-pip + python3-venv via apt-get..."
                apt-get update -qq && apt-get install -y -qq python3-pip python3-venv
            fi

            if [ ! -d "$VENV_DIR" ]; then
                echo "[bg] creating venv (first-boot only)..."
                python3 -m venv "$VENV_DIR"
            fi

            source "$VENV_DIR/bin/activate"
            pip install --upgrade pip
            pip install -r "$BACKEND_DIR/requirements.txt" --prefer-binary

            echo "=== [bg] starting uvicorn at $(date) ==="
            cd "$BACKEND_DIR"
            PYTHONPATH=. exec python -m uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT}
        } >> "$LOG_FILE" 2>&1
    `;

    const child = spawn("bash", ["-c", script], {
        detached: true,
        stdio: "ignore",
    });
    child.on("error", (err) => {
        console.log("bootstrap spawn error:", err.message);
    });
    child.unref();
    console.log("Backend bootstrap launched in background (logs: /home/LogFiles/chatbot-bootstrap.log)");
}

bootstrapBackend();

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
