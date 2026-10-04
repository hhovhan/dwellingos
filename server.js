const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const root = path.join(__dirname, 'public');
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json' };

http.createServer((req, res) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;
  if (pathname === '/api/health' || pathname === '/api/operator') {
    if (pathname === '/api/operator' && req.method !== 'POST') return res.writeHead(405).end('Method not allowed');
    if (pathname === '/api/health' && req.method !== 'GET') return res.writeHead(405).end('Method not allowed');
    let body = '';
    req.on('data', chunk => {
      body += chunk;
      if (body.length > 100000) req.destroy();
    });
    req.on('end', () => {
      let payload;
      try { payload = pathname === '/api/health' ? {action:'health'} : JSON.parse(body); }
      catch { res.writeHead(400, {'Content-Type':'application/json'}).end(JSON.stringify({error:'Invalid JSON'})); return; }
      const child = spawn('python3', [path.join(__dirname, 'scripts/operator_service.py')], {cwd:__dirname});
      let output = '';
      child.stdout.on('data', chunk => { output += chunk; });
      child.stderr.on('data', chunk => { process.stderr.write(chunk); });
      child.on('error', () => res.writeHead(500, {'Content-Type':'application/json'}).end(JSON.stringify({error:'Operator service unavailable'})));
      child.on('close', code => {
        if (res.writableEnded) return;
        res.writeHead(code === 0 ? 200 : 400, {'Content-Type':'application/json'});
        res.end(output || JSON.stringify({error:'Operator service failed'}));
      });
      child.stdin.end(JSON.stringify(payload));
    });
    return;
  }
  const relative = pathname === '/' ? 'index.html' : pathname.replace(/^\//, '');
  const target = path.normalize(path.join(root, relative));
  if (!target.startsWith(root)) return res.writeHead(403).end('Forbidden');
  fs.readFile(target, (error, content) => {
    if (error) return res.writeHead(error.code === 'ENOENT' ? 404 : 500).end('Not found');
    res.writeHead(200, { 'Content-Type': types[path.extname(target)] || 'application/octet-stream' });
    res.end(content);
  });
}).listen(4173, '127.0.0.1', () => console.log('DwellingOS: http://127.0.0.1:4173'));
