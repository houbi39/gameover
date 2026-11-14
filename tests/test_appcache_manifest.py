import tempfile
import unittest
from pathlib import Path

from scripts.update_appcache_manifests import (
    manifest_digest,
    parse_cache_entries,
    update_manifest_text,
)


class AppCacheManifestTests(unittest.TestCase):
    def test_parses_cache_entries_and_ignores_query_strings(self):
        text = 'CACHE MANIFEST\nCACHE:\nasset.js?v=4\n../img.jpg\nNETWORK:\n*\n'
        self.assertEqual(parse_cache_entries(text), ['asset.js?v=4', '../img.jpg'])

    def test_manifest_digest_changes_when_cached_asset_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'asset.js').write_text('old')
            manifest = root / 'cache.manifest'
            text = 'CACHE MANIFEST\nCACHE:\nasset.js?v=4\n'
            first = manifest_digest(root, manifest, text)
            (root / 'asset.js').write_text('new')
            second = manifest_digest(root, manifest, text)
            self.assertNotEqual(first, second)

    def test_manifest_digest_changes_when_public_cache_url_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index.html').write_text('same page')
            manifest = root / 'cache.manifest'
            old = 'CACHE MANIFEST\nCACHE:\nindex.html\n'
            clean = 'CACHE MANIFEST\nCACHE:\n./\n'
            self.assertNotEqual(
                manifest_digest(root, manifest, old),
                manifest_digest(root, manifest, clean),
            )

    def test_manifest_version_is_updated_deterministically(self):
        old = 'CACHE MANIFEST\n# old version\nCACHE:\nasset.js\n'
        updated = update_manifest_text(old, 'a' * 64)
        self.assertIn('# GAMEOVER-CACHE-VERSION: ' + 'a' * 64, updated)
        self.assertEqual(update_manifest_text(updated, 'a' * 64), updated)

    def test_header_is_first_line_even_if_old_manifest_has_comment_before_it(self):
        old = '# old leading comment\nCACHE MANIFEST \nCACHE:\nasset.js\n'
        updated = update_manifest_text(old, 'b' * 64)
        self.assertEqual(updated.splitlines()[0], 'CACHE MANIFEST')
        self.assertIn('# old leading comment', updated)

    def test_all_cache_update_pages_activate_new_cache_and_report_errors(self):
        pages = [
            '505/cache.html', '672/index.html', '672goldhen/index.html',
            '900goldhen/cache.html', '900v3/cache.html',
            'g2all/cache505.html', 'g2all/cache700.html', 'g2all/cache900.html',
            'g2all/cachecss.html', 'g2all/cacheslopkit.html',
        ]
        root = Path(__file__).resolve().parents[1]
        for page in pages:
            with self.subTest(page=page):
                source = (root / page).read_text(encoding='utf-8')
                self.assertIn('swapCache()', source)
                self.assertIn('applicationCache.onerror', source)

    def test_672_goldhen_does_not_mark_failed_cache_as_installed(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / '672goldhen/index.html').read_text(encoding='utf-8')
        error_handler = source.split('window.applicationCache.onerror=', 1)[1].split(';', 1)[0]
        self.assertNotIn('cached672="yes"', error_handler)

    def test_directory_route_resolves_to_index_html_for_cloudflare_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index.html').write_text('landing page')
            manifest = root / 'cache.manifest'
            text = 'CACHE MANIFEST\nCACHE:\n./\n'
            self.assertEqual(len(manifest_digest(root, manifest, text)), 64)

    def test_extensionless_html_route_resolves_to_html_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'webactivator.html').write_text('activation page')
            manifest = root / 'cache.manifest'
            text = 'CACHE MANIFEST\nCACHE:\nwebactivator\n'
            self.assertEqual(len(manifest_digest(root, manifest, text)), 64)

    def test_manifests_use_cloudflare_clean_urls_for_html_cache_entries(self):
        root = Path(__file__).resolve().parents[1]
        for manifest in root.rglob('*.manifest'):
            with self.subTest(manifest=manifest.relative_to(root)):
                entries = parse_cache_entries(manifest.read_text(encoding='utf-8'))
                self.assertFalse(
                    [entry for entry in entries if entry.lower().endswith('.html')],
                    f'{manifest.relative_to(root)} contains HTML URLs that Cloudflare redirects',
                )

    def test_query_path_must_exist_after_query_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'asset.js').write_text('ok')
            manifest = root / 'cache.manifest'
            text = 'CACHE MANIFEST\nCACHE:\nasset.js?v=4\n'
            self.assertEqual(len(manifest_digest(root, manifest, text)), 64)


if __name__ == '__main__':
    unittest.main()
