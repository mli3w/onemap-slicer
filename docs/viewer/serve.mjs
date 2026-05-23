#!/usr/bin/env node
// Zero-dependency dev server for the OneMap viewer.
//
// Serves files from this directory and reverse-proxies /omapi/* and /maps/*
// to www.onemap.gov.sg, adding permissive CORS headers and rewriting any
// absolute upstream URLs in JSON bodies so child tile fetches stay on the
// proxy instead of hitting CORS directly.
//
// Run:  node serve.mjs   (or  PORT=9000 node serve.mjs)
import http from 'node:http';
import https from 'node:https';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const PORT = Number(process.env.PORT) || 8000;
const UPSTREAM_HOST = 'www.onemap.gov.sg';
const ROOT = path.dirname(fileURLToPath(import.meta.url));

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'application/javascript',
  '.mjs':  'application/javascript',
  '.css':  'text/css',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.svg':  'image/svg+xml',
  '.json': 'application/json',
  '.ico':  'image/x-icon',
};

function proxy(req, res) {
  const upstream = https.request({
    host: UPSTREAM_HOST,
    path: req.url,
    method: req.method,
    headers: {
      'user-agent': 'onemap-viewer-proxy/1.0',
      'accept': req.headers.accept || '*/*',
      // Identity encoding so we can rewrite JSON bodies without un-gzipping.
      'accept-encoding': 'identity',
    },
  }, (up) => {
    const headers = { ...up.headers };
    headers['access-control-allow-origin'] = '*';
    headers['access-control-allow-headers'] = '*';
    delete headers['content-security-policy'];
    delete headers['x-frame-options'];

    const ct = up.headers['content-type'] || '';
    const isJson = ct.includes('json') || req.url.endsWith('.json');

    if (isJson) {
      const chunks = [];
      up.on('data', c => chunks.push(c));
      up.on('end', () => {
        let body = Buffer.concat(chunks).toString('utf8');
        // Make absolute upstream URLs same-origin so Cesium walks the proxy.
        body = body.split('https://www.onemap.gov.sg/').join('/');
        headers['content-length'] = Buffer.byteLength(body);
        res.writeHead(up.statusCode, headers);
        res.end(body);
      });
    } else {
      res.writeHead(up.statusCode, headers);
      up.pipe(res);
    }
  });
  upstream.on('error', (e) => {
    res.writeHead(502);
    res.end('proxy error: ' + e.message);
  });
  req.pipe(upstream);
}

function serveStatic(req, res) {
  const url = req.url === '/' ? '/index.html' : req.url.split('?')[0];
  const filePath = path.join(ROOT, decodeURIComponent(url));
  if (!filePath.startsWith(ROOT)) { res.writeHead(403); res.end('forbidden'); return; }
  fs.readFile(filePath, (err, data) => {
    if (err) { res.writeHead(404); res.end('not found'); return; }
    res.writeHead(200, {
      'content-type': MIME[path.extname(filePath)] || 'application/octet-stream',
    });
    res.end(data);
  });
}

http.createServer((req, res) => {
  if (req.url.startsWith('/omapi/') || req.url.startsWith('/maps/')) return proxy(req, res);
  serveStatic(req, res);
}).listen(PORT, () => {
  console.log(`OneMap viewer:  http://localhost:${PORT}/`);
  console.log(`Proxying /omapi/* and /maps/* → https://${UPSTREAM_HOST}`);
});
