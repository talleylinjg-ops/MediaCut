import assert from 'node:assert/strict';

// ---- R2 桩 ----
const store = new Map();
function toBytes(body) {
  if (body instanceof Uint8Array) return body;
  if (body instanceof ArrayBuffer) return new Uint8Array(body);
  return new TextEncoder().encode(String(body));
}
const r2 = {
  async get(key, opts) {
    const rec = store.get(key);
    if (!rec) return null;
    const obj = {
      body: rec.bytes,
      size: rec.bytes.length,
      httpEtag: '"r2-' + key + '"',
      customMetadata: rec.customMetadata || {},
      httpMetadata: rec.httpMetadata || {},
      range: undefined,
      writeHttpMetadata(h) {
        const ct = rec.httpMetadata && rec.httpMetadata.contentType;
        if (ct) h.set('content-type', ct);
      }
    };
    if (opts && opts.range) {
      const len = Math.min(4, rec.bytes.length);
      obj.range = { offset: 0, length: len };
      obj.body = rec.bytes.slice(0, len);
    }
    return obj;
  },
  async put(key, body, opts) {
    const buf = body && typeof body.arrayBuffer === 'function' ? await body.arrayBuffer() : body;
    store.set(key, {
      bytes: toBytes(buf),
      customMetadata: (opts && opts.customMetadata) || {},
      httpMetadata: (opts && opts.httpMetadata) || {}
    });
    return {};
  }
};

const env = {
  ORIGIN: 'https://origin.example',
  MIRROR_WRITE: '1',
  REVALIDATE_HTML: '1',
  STATIC: r2
};

// ---- CF Cache 桩 ----
const cacheStore = new Map();
globalThis.caches = {
  default: {
    async match(req) {
      const u = typeof req === 'string' ? req : req.url;
      const r = cacheStore.get(u);
      return r ? r.clone() : undefined;
    },
    async put(req, resp) {
      const u = typeof req === 'string' ? req : req.url;
      cacheStore.set(u, resp.clone());
    }
  }
};

// ---- 源站桩 ----
const origin = {
  indexBody: '<!doctype html><title>MediaCut</title>',
  indexEtag: '"origin-index-v1"',
  indexCacheControl: 'no-cache, must-revalidate',
  assetBody: 'console.log(1)',
  assetHeaders: {
    'content-type': 'text/plain; charset=utf-8',
    etag: '"origin-tmp-v1"',
    'accept-ranges': 'bytes',
    'x-origin-only': 'keep-me'
  },
  fail: false,
  conditionalGot: []
};
const realFetch = globalThis.fetch;
globalThis.fetch = async (url, init) => {
  if (origin.fail) throw new Error('origin down');
  const u = new URL(String(url));
  const headers = new Headers((init && init.headers) || {});
  if (u.pathname === '/tmp.txt') {
    return new Response(origin.assetBody, { status: 200, headers: origin.assetHeaders });
  }
  if (u.pathname.startsWith('/api/')) {
    return new Response('{"ok":true}', { status: 200, headers: { 'content-type': 'application/json', 'x-frame-options': 'DENY' } });
  }
  const inm = headers.get('if-none-match');
  origin.conditionalGot.push(inm);
  if (inm === origin.indexEtag) {
    return new Response(null, {
      status: 304,
      headers: { etag: origin.indexEtag, 'cache-control': origin.indexCacheControl }
    });
  }
  return new Response(origin.indexBody, {
    status: 200,
    headers: {
      'content-type': 'text/html; charset=utf-8',
      'cache-control': origin.indexCacheControl,
      etag: origin.indexEtag,
      'last-modified': 'Sat, 26 Sep 2026 16:11:39 GMT',
      'accept-ranges': 'bytes'
    }
  });
};

const { default: worker } = await import('../src/index.js');

function call(path, init, overrides) {
  const pending = [];
  const ctx = { waitUntil: (p) => pending.push(p) };
  const req = new Request('https://edge.example' + path, init);
  return worker.fetch(req, { ...env, ...(overrides || {}) }, ctx).then(async (resp) => {
    await Promise.all(pending);
    return resp;
  });
}

// A. HTML 首次请求：源站 200 → 镜像并原样回放源站响应头
let r = await call('/');
assert.equal(r.headers.get('x-served-from'), 'origin-mirrored');
assert.equal(r.headers.get('content-type'), 'text/html; charset=utf-8');
assert.equal(r.headers.get('cache-control'), origin.indexCacheControl);
assert.equal(r.headers.get('etag'), origin.indexEtag);
assert.equal(r.headers.get('last-modified'), 'Sat, 26 Sep 2026 16:11:39 GMT');
assert.equal(r.headers.get('x-frame-options'), null, '不应注入源站没有的头');
assert.equal(await r.text(), origin.indexBody);
assert.ok(store.has('index.html'), 'HTML 应写入 R2 快照');

// B. HTML 二次请求：带 If-None-Match，源站 304 → 返回快照且头部一致
r = await call('/');
assert.equal(origin.conditionalGot.at(-1), origin.indexEtag, '应携带源站 etag 做条件请求');
assert.equal(r.headers.get('x-served-from'), 'r2-static');
assert.equal(r.headers.get('cache-control'), origin.indexCacheControl);
assert.equal(r.headers.get('etag'), origin.indexEtag);
assert.equal(await r.text(), origin.indexBody);

// C. SPA 路由（无扩展名）同样走 HTML 校验并返回同一页面
r = await call('/portal/docs');
assert.equal(await r.text(), origin.indexBody);
assert.equal(r.headers.get('etag'), origin.indexEtag);

// D. 源站不可达 → 回退到快照，内容不变
origin.fail = true;
r = await call('/');
assert.equal(r.headers.get('x-served-from'), 'r2-static');
assert.equal(await r.text(), origin.indexBody);
origin.fail = false;

// E. 静态资源未命中 → 回源镜像，保留源站自定义头
assert.equal(store.has('tmp.txt'), false);
r = await call('/tmp.txt');
assert.equal(r.headers.get('x-served-from'), 'origin-mirrored');
assert.equal(r.headers.get('x-origin-only'), 'keep-me');
assert.equal(await r.text(), origin.assetBody);
assert.ok(store.has('tmp.txt'));

// F. 静态资源 R2 命中 → 原样回放源站响应头
cacheStore.clear();
r = await call('/tmp.txt');
assert.equal(r.headers.get('x-served-from'), 'r2-static');
assert.equal(r.headers.get('content-type'), 'text/plain; charset=utf-8');
assert.equal(r.headers.get('etag'), '"origin-tmp-v1"');
assert.equal(r.headers.get('x-origin-only'), 'keep-me');
assert.equal(await r.text(), origin.assetBody);

// G. 预置资源（无源站头）→ 按扩展名兜底 content-type，并按 _headers 规范补齐安全头
store.set('assets/index-abc.js', { bytes: toBytes('console.log(2)'), customMetadata: {}, httpMetadata: {} });
cacheStore.clear();
r = await call('/assets/index-abc.js');
assert.equal(r.headers.get('content-type'), 'text/javascript; charset=utf-8');
assert.equal(r.headers.get('x-frame-options'), 'SAMEORIGIN', '快照路径应补齐 _headers 安全头');
assert.equal(r.headers.get('x-content-type-options'), 'nosniff');
assert.equal(r.headers.get('accept-ranges'), 'bytes');

// H. Range 请求 → 206 且带 content-range
origin.fail = false;
r = await call('/tmp.txt', { headers: { range: 'bytes=0-3' } });
assert.equal(r.status, 206);
assert.match(r.headers.get('content-range'), /^bytes 0-3\//);

// I. 动态路径原样直通源站（含源站自己的头，不新增）
r = await call('/api/v1/tasks/1');
assert.equal(r.headers.get('x-served-from'), 'origin');
assert.equal(r.headers.get('x-frame-options'), 'DENY', '应保留源站自己的头');
assert.equal(r.headers.get('x-content-type-options'), null, '不应额外注入');

// I2. Swagger 页面（/api-docs）回源直通，/docs 走 SPA 快照
r = await call('/api-docs');
assert.equal(r.headers.get('x-served-from'), 'origin');
r = await call('/docs', null, { REVALIDATE_HTML: '0' });
assert.equal(r.headers.get('x-served-from'), 'r2-static');
assert.equal(await r.text(), origin.indexBody);

// J. 关闭 HTML 校验时直接返回快照
r = await call('/', null, { REVALIDATE_HTML: '0' });
assert.equal(r.headers.get('x-served-from'), 'r2-static');
assert.equal(await r.text(), origin.indexBody);

// J2. 快照缺少 cache-control 时，HTML 兜底为源站同款 no-cache
store.set('page.html', { bytes: toBytes('<!doctype html><p>snap</p>'), customMetadata: {}, httpMetadata: {} });
cacheStore.clear();
r = await call('/page.html', null, { REVALIDATE_HTML: '0' });
assert.equal(r.headers.get('x-served-from'), 'r2-static');
assert.equal(r.headers.get('content-type'), 'text/html; charset=utf-8');
assert.equal(r.headers.get('cache-control'), 'no-cache, must-revalidate');

// K. 非 GET/HEAD 直通源站
r = await call('/webhook/hook', { method: 'POST', body: 'x' });
assert.equal(r.headers.get('x-served-from'), 'origin');

// L. 无扩展名的真实文件（如 CNAME）→ 按静态资源返回，不回退到页面
store.set('CNAME', { bytes: toBytes('didimedia.com'), customMetadata: {}, httpMetadata: {} });
cacheStore.clear();
r = await call('/CNAME');
assert.equal(r.headers.get('x-served-from'), 'r2-static');
assert.equal(await r.text(), 'didimedia.com');

globalThis.fetch = realFetch;
console.log('边缘一致性校验全部通过（14 项）');
