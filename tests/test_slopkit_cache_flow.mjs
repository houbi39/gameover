import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync(new URL('../g2all/cacheslopkit.html', import.meta.url), 'utf8');
const manifest = fs.readFileSync(new URL('../g2all/slopkit.manifest', import.meta.url), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/i)?.[1];
assert.ok(script, 'Slopkit cache page must contain its cache controller');

test('the cache manifest tracks the cache controller page so this fix is downloadable', () => {
  const cacheSection = manifest.split('CACHE:')[1]?.split(/\n(?:NETWORK|FALLBACK):/)[0] ?? '';
  assert.match(cacheSection, /(?:^|\n)cacheslopkit\.html(?:\n|$)/);
});

function createCachePage(status = 0) {
  const listeners = new Map();
  const cache = {
    status,
    UPDATEREADY: 4,
    swapCalls: 0,
    addEventListener(name, callback) {
      listeners.set(name, callback);
    },
    swapCache() { this.swapCalls += 1; },
    emit(name, event = {}) { listeners.get(name)?.(event); },
  };
  const window = {
    applicationCache: cache,
    msgs: { innerHTML: '' },
    location: { replacements: [], replace(url) { this.replacements.push(url); } },
  };
  const document = { getElementById(id) { return id === 'msgs' ? window.msgs : null; } };
  vm.runInNewContext(script, { window, document, Math });
  return { cache, window };
}

test('first successful cache install returns to the host automatically', () => {
  const { cache, window } = createCachePage();
  cache.emit('cached');
  assert.deepEqual(window.location.replacements, ['index.html']);
});

test('an already-current cache handles noupdate instead of asking to reopen the browser', () => {
  const { cache, window } = createCachePage();
  cache.emit('noupdate');
  assert.deepEqual(window.location.replacements, ['index.html']);
});

test('a ready cache update is swapped before returning to the host', () => {
  const { cache, window } = createCachePage();
  cache.emit('updateready');
  assert.equal(cache.swapCalls, 1);
  assert.deepEqual(window.location.replacements, ['index.html']);
});

test('a cache already marked update-ready is activated during page startup', () => {
  const { cache, window } = createCachePage(4);
  assert.equal(cache.swapCalls, 1);
  assert.deepEqual(window.location.replacements, ['index.html']);
});

test('cache errors remain visible and do not redirect into an endless loop', () => {
  const { cache, window } = createCachePage();
  cache.emit('error');
  assert.deepEqual(window.location.replacements, []);
  assert.match(window.msgs.innerHTML, /تعذّر تحديث التخزين المؤقت/);
});

test('successful cache events cannot trigger duplicate redirects', () => {
  const { cache, window } = createCachePage();
  cache.emit('cached');
  cache.emit('noupdate');
  assert.deepEqual(window.location.replacements, ['index.html']);
});
