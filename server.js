const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8080;
const STATIC_DIR = path.join(__dirname, 'website');

const mimeTypes = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.pdf': 'application/pdf',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
};

http.createServer((req, res) => {
  const urlPath = req.url.split('?')[0]; // strip query strings
  let filePath = path.join(STATIC_DIR, urlPath === '/' ? 'index.html' : urlPath);

  fs.readFile(filePath, (err, data) => {
    if (err) {
      // SPA fallback — serve index.html for missing routes
      fs.readFile(path.join(STATIC_DIR, 'index.html'), (e, fallback) => {
        if (e) { res.writeHead(500); res.end('Server Error'); return; }
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(fallback);
      });
    } else {
      const ext = path.extname(filePath);
      res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'application/octet-stream' });
      res.end(data);
    }
  });
}).listen(PORT, () => console.log(`Serving /website on port ${PORT}`));
```

2. **Change the Startup command** in Azure Stack Settings to:
```
node server.js
```

3. Your project structure should look like:
```
/
├── server.js          ← new file
├── package-lock.json
├── website/
│   ├── index.html
│   ├── demo.html
│   ├── demos.html
│   ├── reimbursement-demo.html
│   ├── Himanshu_Suri_CV.pdf
│   └── ...
├── CV Himanshu Suri (1).pdf
└── index.html
