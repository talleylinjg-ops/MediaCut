/**
 * MediaCut 边缘前置层（Cloudflare Worker）
 *
 * 目标：边缘对外提供的静态页面与源站完全一致（内容逐字节相同、响应头原样回放）。
 *
 * 分层：
 *   1. 动态路径直接回源：/api/、/static/、/api-docs、/api-redoc、/openapi.json、/health
 *   2. HTML 页面（/、/ 无扩展名路由、*.html）：
 *        REVALIDATE_HTML=1 时对源站做条件请求（If-None-Match）——
 *          源站 304 → 返回 R2 快照；源站 200 → 更新 R2 快照并返回源站版本；
 *          源站不可达 → 返回 R2 快照。保证页面始终与源站一致，且源站宕机仍可访问。
 *        REVALIDATE_HTML=0 时直接返回 R2 快照（当前部署默认，纯边缘快照）。
 *   3. 其它静态资源：CF Cache → R2；R2 未命中回源，并把「响应体 + 源站响应头」写入 R2。
 *      支持 Range 请求。
 *
 * 关键原则：不注入、不覆盖源站响应头。R2 快照会保存镜像时刻的源站响应头并原样回放；
 * 只有快照缺失响应头时才按扩展名兜底 content-type。
 *
 * 绑定与变量（见 wrangler.toml）：
 *   STATIC          R2 绑定
 *   ORIGIN          后端源站地址，例如 https://didimedia.com
 *   MIRROR_WRITE    "1" 时把回源命中的静态内容写入 R2
 *   REVALIDATE_HTML "1" 时对 HTML 页面做条件校验（默认行为，可关闭）
 *
 * 请求头回执：x-served-from = cache | r2-static | origin-mirrored | origin
 */

const ORIGIN_EXACT = new Set(['/openapi.json', '/health']);
const ORIGIN_PREFIXES = ['/api/', '/static/', '/api-docs', '/api-redoc'];

// 逐跳头与 Cloudflare 自行管理的头，不能/无需回放
const NON_REPLAYABLE = new Set([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
  'content-encoding',
  'content-length',
  'server',
  'date',
  'expect-ct',
  'report-to',
  'nel',
  'alt-svc',
  'cf-ray',
  'cf-cache-status'
]);

const MIME = {
  html: 'text/html; charset=utf-8',
  js: 'text/javascript; charset=utf-8',
  mjs: 'text/javascript; charset=utf-8',
  css: 'text/css; charset=utf-8',
  json: 'application/json; charset=utf-8',
  txt: 'text/plain; charset=utf-8',
  xml: 'application/xml',
  svg: 'image/svg+xml',
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  webp: 'image/webp',
  gif: 'image/gif',
  ico: 'image/vnd.microsoft.icon',
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

/** HTML 页面（含 SPA 回退）与普通静态资源的区分 */
function resolveKey(path) {
  const key = keyFor(path);
  if (key.endsWith('.html')) return { key, isHtml: true, spaFallback: false };
  if (!hasExtension(path)) return { key, isHtml: false, spaFallback: true };
  return { key, isHtml: false, spaFallback: false };
}

/** @param {Headers} headers */
function captureHeaders(headers) {
  const out = {};
  headers.forEach((value, name) => {
    const key = name.toLowerCase();
    if (NON_REPLAYABLE.has(key)) return;
    out[key] = value;
  });
  return out;
}

/**
 * 由快照元数据构造响应头：优先原样回放源站响应头，缺失时才兜底。
 *
 * @param {Record<string, string>|null} stored
 * @param {string} key
 */
function buildHeaders(stored, key) {
  const headers = new Headers();
  if (stored) {
    for (const [name, value] of Object.entries(stored)) headers.set(name, value);
  }
  if (!headers.has('content-type')) headers.set('content-type', mimeFor(key));
  if (!headers.has('accept-ranges')) headers.set('accept-ranges', 'bytes');
  // 与源站对 HTML 的处理保持一致，避免边缘/浏览器缓存住旧页面
  if (key.endsWith('.html') && !headers.has('cache-control')) {
    headers.set('cache-control', 'no-cache, must-revalidate');
  }
  return headers;
}

/** @param {any} object R2 对象 */
function storedHeadersOf(object) {
  const raw = object && object.customMetadata && object.customMetadata.headers;
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch {
    return null;
  }
}

/**
 * @param {Request} request
 * @param {any} env
 * @param {{ waitUntil: (p: Promise<unknown>) => void }} ctx
 * @param {string} key
 */
async function writeSnapshot(env, ctx, key, body, contentType, headers) {
  if (env.MIRROR_WRITE !== '1') return;
  const options = {
    httpMetadata: { contentType: contentType || mimeFor(key) },
    customMetadata: { headers: JSON.stringify(headers) }
  };
  ctx.waitUntil(env.STATIC.put(key, body, options));
}

/**
 * 直通源站：响应头与响应体均不修改。
 *
 * @param {Request} request
 * @param {any} env
 * @param {string} [marker]
 */
async function proxyToOrigin(request, env, marker) {
  const url = new URL(request.url);
  const target = new URL(url.pathname + url.search, env.ORIGIN);
  const method = request.method.toUpperCase();
  const resp = await fetch(target.toString(), {
    method: request.method,
    headers: request.headers,
    body: method === 'GET' || method === 'HEAD' ? null : request.body,
    redirect: 'manual'
  });
  const out = new Response(resp.body, {
    status: resp.status,
    statusText: resp.statusText,
    headers: resp.headers
  });
  out.headers.set('x-served-from', marker || 'origin');
  return out;
}

/** @param {any} object R2 对象 */
function serveSnapshot(request, object, key, marker) {
  const headers = buildHeaders(storedHeadersOf(object), key);
  let status = 200;
  if (object.range) {
    const start = object.range.offset;
    const end = object.range.offset + object.range.length - 1;
    headers.set('content-range', `bytes ${start}-${end}/${object.size}`);
    status = 206;
  }
  const body = request.method === 'HEAD' ? null : object.body;
  const resp = new Response(body, { status, headers });
  resp.headers.set('x-served-from', marker);
  return resp;
}

/**
 * HTML 页面：条件请求校验，保证与源站一致。
 *
 * @param {Request} request
 * @param {any} env
 * @param {{ waitUntil: (p: Promise<unknown>) => void }} ctx
 * @param {string} key
 * @param {string} path
 */
async function serveHtml(request, env, ctx, key, path) {
  const snapshot = await env.STATIC.get(key);
  const stored = storedHeadersOf(snapshot);

  if (request.method === 'HEAD' || env.REVALIDATE_HTML !== '1') {
    if (snapshot) return serveSnapshot(request, snapshot, key, 'r2-static');
    return mirrorFallback(request, env, ctx, key, path);
  }

  const url = new URL(request.url);
  const target = new URL(url.pathname + url.search, env.ORIGIN);
  const reqHeaders = new Headers();
  if (stored && stored.etag) reqHeaders.set('if-none-match', stored.etag);
  else if (snapshot && snapshot.httpEtag) reqHeaders.set('if-none-match', snapshot.httpEtag);

  let resp = null;
  try {
    resp = await fetch(target.toString(), {
      method: 'GET',
      headers: reqHeaders,
      redirect: 'manual'
    });
  } catch {
    resp = null;
  }

  if (resp && resp.status === 304 && snapshot) {
    return serveSnapshot(request, snapshot, key, 'r2-static');
  }

  if (resp && resp.status === 200) {
    const type = resp.headers.get('content-type') || '';
    if (STATIC_CONTENT_TYPE.test(type)) {
      const buf = await resp.arrayBuffer();
      const headers = captureHeaders(resp.headers);
      await writeSnapshot(env, ctx, key, buf, type, headers);
      const out = new Response(buf, { status: 200, headers: buildHeaders(headers, key) });
      out.headers.set('x-served-from', 'origin-mirrored');
      return out;
    }
    return passthrough(resp);
  }

  if (resp) return passthrough(resp);
  if (snapshot) return serveSnapshot(request, snapshot, key, 'r2-static');
  return new Response('origin unavailable', { status: 502 });
}

/**
 * 静态资源：CF Cache → R2 → 回源镜像。
 *
 * @param {Request} request
 * @param {any} env
 * @param {{ waitUntil: (p: Promise<unknown>) => void }} ctx
 * @param {string} key
 * @param {string} path
 */
async function serveAsset(request, env, ctx, key, path) {
  const wantsRange = request.headers.has('range');

  if (request.method === 'GET' && !wantsRange) {
    const hit = await caches.default.match(request);
    if (hit) {
      const out = new Response(hit.body, {
        status: hit.status,
        statusText: hit.statusText,
        headers: hit.headers
      });
      out.headers.set('x-served-from', 'cache');
      return out;
    }
  }

  const options = wantsRange ? { range: request.headers } : undefined;
  const object = await env.STATIC.get(key, options);

  if (object) {
    const resp = serveSnapshot(request, object, key, 'r2-static');
    const cacheControl = resp.headers.get('cache-control') || '';
    if (
      request.method === 'GET' &&
      !object.range &&
      !/no-store|private/i.test(cacheControl)
    ) {
      ctx.waitUntil(caches.default.put(request, resp.clone()));
    }
    return resp;
  }

  return mirrorFallback(request, env, ctx, key, path);
}

/**
 * R2 未命中时回源：原样返回源站响应，并在可镜像时把「响应体 + 响应头」写入 R2。
 *
 * @param {Request} request
 * @param {any} env
 * @param {{ waitUntil: (p: Promise<unknown>) => void }} ctx
 * @param {string} key
 * @param {string} path
 */
async function mirrorFallback(request, env, ctx, key, path) {
  const url = new URL(request.url);
  const target = new URL(url.pathname + url.search, env.ORIGIN);
  let resp;
  try {
    resp = await fetch(target.toString(), {
      method: request.method,
      headers: request.headers,
      body: request.method === 'GET' || request.method === 'HEAD' ? null : request.body,
      redirect: 'manual'
    });
  } catch {
    return new Response('origin unavailable', { status: 502 });
  }

  const type = resp.headers.get('content-type') || '';
  const shouldMirror =
    request.method === 'GET' &&
    resp.status === 200 &&
    env.MIRROR_WRITE === '1' &&
    STATIC_CONTENT_TYPE.test(type);

  if (!shouldMirror) return passthrough(resp);

  const buf = await resp.arrayBuffer();
  const headers = captureHeaders(resp.headers);
  await writeSnapshot(env, ctx, key, buf, type, headers);
  const out = new Response(buf, { status: 200, headers: buildHeaders(headers, key) });
  out.headers.set('x-served-from', 'origin-mirrored');
  return out;
}

/** @param {Response} resp */
function passthrough(resp) {
  return new Response(resp.body, {
    status: resp.status,
    statusText: resp.statusText,
    headers: resp.headers
  });
}

const FILE_RE = /^\/files\/([0-9a-f]{32})\/([A-Za-z0-9._-]+)$/;

async function hmacHex(secret, message) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    enc.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(message));
  return [...new Uint8Array(sig)]
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
    .slice(0, 32);
}

async function serveFile(url, env, path) {
  const m = FILE_RE.exec(path);
  if (!m) return new Response('not found', { status: 404 });
  const [, taskId, filename] = m;

  const secret = env.FILE_SIGN_SECRET;
  if (!secret) return new Response('files not configured', { status: 503 });

  const exp = Number(url.searchParams.get('exp') || 0);
  const sig = url.searchParams.get('sig') || '';
  if (!Number.isFinite(exp) || exp <= Date.now() / 1000) {
    return new Response('link expired', { status: 403 });
  }
  const expected = await hmacHex(secret, `results/${taskId}/${filename}:${exp}`);
  if (expected.length !== sig.length || expected !== sig) {
    return new Response('invalid signature', { status: 403 });
  }

  const obj = await env.R2RESULTS.get(`results/${taskId}/${filename}`);
  if (!obj) return new Response('result expired', { status: 404 });

  const headers = new Headers();
  headers.set('Content-Type', mimeFor(filename));
  headers.set('Content-Length', String(obj.size));
  headers.set('Cache-Control', 'private, max-age=300');
  headers.set('x-served-from', 'r2-results');
  return new Response(obj.body, { headers });
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

    if (path.startsWith('/files/')) return serveFile(url, env, path);
    if (isOriginPath(path)) return proxyToOrigin(request, env);
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      return proxyToOrigin(request, env);
    }

    const { key, isHtml, spaFallback } = resolveKey(path);
    if (isHtml) return serveHtml(request, env, ctx, key, path);
    if (spaFallback) {
      const exact = await env.STATIC.get(key);
      if (exact) return serveAsset(request, env, ctx, key, path);
      return serveHtml(request, env, ctx, 'index.html', path);
    }
    return serveAsset(request, env, ctx, key, path);
  }
};
