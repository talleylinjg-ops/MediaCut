/**
 * MediaCut 边缘前置层（Cloudflare Worker）
 *
 * 目标（对齐 liangdu 的分层）：
 *   1. 静态资源优先命中 CF Cache → R2，命中即返回 `x-served-from: r2-static`，不回源
 *   2. HTML（SPA）与静态资源全部由 R2 提供，前台浏览不依赖后端容器
 *   3. R2 未命中时回源一次，并把可缓存内容写入 R2（`x-served-from: origin-mirrored`）
 *   4. 仅动态路径回源：/api/、/static/、/docs、/redoc、/openapi.json、/health
 *
 * 绑定与变量（见 wrangler.toml）：
 *   STATIC        R2 绑定
 *   ORIGIN        后端源站地址，例如 https://didimedia.com
 *   MIRROR_WRITE  "1" 时把回源命中的静态内容写入 R2
 *
 * 请求头回执：x-served-from = cache | r2-static | origin-mirrored | origin
 */

const ORIGIN_EXACT = new Set(['/openapi.json', '/health']);
const ORIGIN_PREFIXES = ['/api/', '/static/', '/docs', '/redoc'];

const MIME = {
  html: 'text/html; charset=utf-8',
  js: 'text/javascript; charset=utf-8',
  mjs: 'text/javascript; charset=utf-8',
  css: 'text/css; charset=utf-8',
  json: 'application/json; charset=utf-8',
  txt: 'text/plain; charset=utf-8',
  xml: 'application/xml; charset=utf-8',
  svg: 'image/svg+xml',
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  webp: 'image/webp',
  gif: 'image/gif',
  ico: 'image/x-icon',
  woff: 'font/woff',
  woff2: 'font/woff2',
  ttf: 'font/ttf',
  eot: 'application/vnd.ms-fontobject',
  webmanifest: 'application/manifest+json',
  map: 'application/json; charset=utf-8'
};

const STATIC_CONTENT_TYPE = /^(text\/|image\/|font\/|application\/(javascript|json|xml|manifest|font|x-javascript))/;

/** @param {string} path */
function isOriginPath(path) {
  if (ORIGIN_EXACT.has(path)) return true;
  return ORIGIN_PREFIXES.some((prefix) => path.startsWith(prefix));
}

/** @param {string} path */
function hasExtension(path) {
  return /\.[A-Za-z0-9]{1,8}$/.test(path);
}

/** @param {string} path */
function keyFor(path) {
  let key = path.replace(/^\/+/, '');
  if (key === '' || key.endsWith('/')) key += 'index.html';
  return key;
}

/** @param {string} key */
function mimeFor(key) {
  const dot = key.lastIndexOf('.');
  const ext = dot >= 0 ? key.slice(dot + 1).toLowerCase() : '';
  return MIME[ext] || 'application/octet-stream';
}

/** @param {string} key */
function cacheControlFor(key) {
  if (key.startsWith('assets/')) return 'public, max-age=31536000, immutable';
  if (key.endsWith('index.html')) return 'no-store';
  return 'public, max-age=3600';
}

/** @param {string} key */
function isCacheable(key) {
  return !key.endsWith('index.html');
}

/**
 * @param {Headers} headers
 * @returns {Headers}
 */
function applySecurityHeaders(headers) {
  headers.set('x-content-type-options', 'nosniff');
  headers.set('x-frame-options', 'SAMEORIGIN');
  headers.set('referrer-policy', 'strict-origin-when-cross-origin');
  headers.set('permissions-policy', 'geolocation=(), microphone=(), camera=()');
  return headers;
}

/**
 * @param {Request} request
 * @param {any} env
 * @returns {Promise<Response>}
 */
async function proxyToOrigin(request, env) {
  const url = new URL(request.url);
  const target = new URL(url.pathname + url.search, env.ORIGIN);
  const method = request.method.toUpperCase();
  const resp = await fetch(target.toString(), {
    method: request.method,
    headers: request.headers,
    body: method === 'GET' || method === 'HEAD' ? null : request.body,
    redirect: 'manual'
  });
  const out = new Response(resp.body, resp);
  applySecurityHeaders(out.headers);
  out.headers.set('x-served-from', 'origin');
  return out;
}

/**
 * R2 未命中时回源，并把静态内容写入 R2。
 *
 * @param {Request} request
 * @param {any} env
 * @param {{ waitUntil: (p: Promise<unknown>) => void }} ctx
 * @param {string} key
 * @returns {Promise<Response>}
 */
async function mirrorFromOrigin(request, env, ctx, key) {
  const resp = await proxyToOrigin(request, env);
  const type = resp.headers.get('content-type') || '';
  const shouldMirror =
    request.method === 'GET' &&
    resp.status === 200 &&
    env.MIRROR_WRITE === '1' &&
    STATIC_CONTENT_TYPE.test(type);

  if (shouldMirror) {
    const toStore = resp.clone();
    ctx.waitUntil(env.STATIC.put(key, toStore.body, { httpMetadata: { contentType: type } }));
    const out = new Response(resp.body, resp);
    applySecurityHeaders(out.headers);
    out.headers.set('x-served-from', 'origin-mirrored');
    return out;
  }
  return resp;
}

export default {
  /**
   * @param {Request} request
   * @param {any} env
   * @param {{ waitUntil: (p: Promise<unknown>) => void }} ctx
   * @returns {Promise<Response>}
   */
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    let path;
    try {
      path = decodeURIComponent(url.pathname);
    } catch {
      path = url.pathname;
    }

    if (isOriginPath(path)) {
      return proxyToOrigin(request, env);
    }
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      return proxyToOrigin(request, env);
    }

    if (request.method === 'GET') {
      const hit = await caches.default.match(request);
      if (hit) {
        const out = new Response(hit.body, hit);
        applySecurityHeaders(out.headers);
        out.headers.set('x-served-from', 'cache');
        return out;
      }
    }

    const key = keyFor(path);
    let stored = await env.STATIC.get(key);
    let servedKey = key;
    if (!stored && !hasExtension(path)) {
      stored = await env.STATIC.get('index.html');
      servedKey = 'index.html';
    }

    if (stored) {
      const headers = new Headers();
      stored.writeHttpMetadata(headers);
      headers.set('etag', stored.httpEtag);
      const currentType = headers.get('content-type') || '';
      if (!currentType || currentType === 'application/octet-stream') {
        headers.set('content-type', mimeFor(servedKey));
      }
      headers.set('cache-control', cacheControlFor(servedKey));
      applySecurityHeaders(headers);
      headers.set('x-served-from', 'r2-static');

      const body = request.method === 'HEAD' ? null : stored.body;
      const resp = new Response(body, { headers });
      if (request.method === 'GET' && isCacheable(servedKey)) {
        ctx.waitUntil(caches.default.put(request, resp.clone()));
      }
      return resp;
    }

    return mirrorFromOrigin(request, env, ctx, key);
  }
};
