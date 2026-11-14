import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
import json
import subprocess
import tempfile
from unittest.mock import patch
import upstream as u
from buildsite import shown_version


def result(tags, complete=True):
    return {'tags': tags, 'complete': complete, 'reason': None}


class Versions(unittest.TestCase):
    def compare(self, current, tags, complete=True):
        return u.compare_image(u.image_ref('docker.io/example/app:' + current), result(tags, complete))

    def test_numeric_order_and_variants(self):
        r = self.compare('v1.9.0-alpine', ['v1.10.0-alpine', 'v2.0.0-apache', 'v3.0.0-rc.1', 'latest'])
        self.assertEqual((r['latest'], r['status']), ('v1.10.0-alpine', 'update_available'))

    def test_numeric_container_build_suffix_is_ordered(self):
        r = u.compare_image(u.image_ref('netboxcommunity/netbox:v4.7.5-5.1.2'), result(['v4.7.5-5.1.3', 'v4.7.5-alpine', 'v4.7.5-5.1.2']))
        self.assertEqual((r['latest'], r['status']), ('v4.7.5-5.1.3', 'update_available'))

    def test_current_requires_complete_scan_and_existing_tag(self):
        self.assertEqual(self.compare('1.2.0', ['1.2.0'])['status'], 'current')
        self.assertEqual(self.compare('1.2.0', ['1.2.0'], False)['status'], 'unknown')
        self.assertEqual(self.compare('1.2.0', ['1.1.0'])['status'], 'unknown')
        self.assertEqual(self.compare('1.2.0', ['1.3.0'], False)['status'], 'update_available')

    def test_mutable_and_nonstandard_tags_are_unknown(self):
        for tag in ['latest', 'main', 'alpine', '1.3.0-rc.1', '1.3.0-1', '1.3.0-1.2', '2.026.37g', '2024.10.22-7ca5933']:
            with self.subTest(tag=tag):
                self.assertEqual(self.compare(tag, ['99.0.0'])['status'], 'unknown')

    def test_digest_preserved_and_not_claimed_checked(self):
        image = u.image_ref('redis:7.4-alpine@sha256:abc')
        self.assertEqual(image['repository'], 'library/redis')
        self.assertEqual(image['digest'], 'sha256:abc')
        self.assertIn('digest changes are not checked', u.compare_image(image, result(['7.4-alpine']))['reason'])

    def test_custom_build_not_compared_as_upstream(self):
        image = u.image_ref('ghcr.io/geniusdynamics/suitecrm-app:1.0.0')
        self.assertEqual(u.compare_image(image, result(['1.1.0']))['status'], 'unknown')

    def test_primary_does_not_pick_first_database(self):
        images = [u.image_ref('postgres:18.0'), u.image_ref('netboxcommunity/netbox:v4.7.5-5.1.2')]
        self.assertEqual(u.main_image(images, 'netbox', {})['repository'], 'netboxcommunity/netbox')
        self.assertEqual(u.main_image(images, 'netbox', {'image': 'docker.io/netboxcommunity/netbox'})['tag'], 'v4.7.5-5.1.2')

    def test_version_mapping_only_for_exact_module_release(self):
        cfg = {'github': 'SuiteCRM/SuiteCRM-Core', 'versions': {'1.0.0': '8.10.2'}}
        get = lambda *args: {'tag_name': 'v8.11.0', 'html_url': 'https://github.com/SuiteCRM/SuiteCRM-Core/releases/tag/v8.11.0'}
        self.assertEqual(u.release_check(cfg, '1.0.0', get, None)['status'], 'update_available')
        self.assertEqual(u.release_check(cfg, '1.1.0', get, None)['status'], 'unknown')
        self.assertIsNone(u.release_check({'github': 'https://evil.invalid'}, '1.0.0', get, None))

    def test_registry_unavailable_and_unsupported(self):
        with patch.object(u, 'get_json', side_effect=TimeoutError):
            r = u.registry_tags(('docker.io', 'example/app'))
            self.assertFalse(r['complete'])
            self.assertEqual(r['tags'], [])
        self.assertFalse(u.registry_tags(('quay.io', 'example/app'))['complete'])

    def test_dockerhub_pagination_is_complete_only_at_end(self):
        responses = [({'results': [{'name': '1.2.0'}], 'next': 'https://hub.docker.com/v2/repositories/example/app/tags?page=2'}, {}),
                     ({'results': [{'name': '1.1.0'}], 'next': None}, {})]
        with patch.object(u, 'get_json', side_effect=responses):
            self.assertEqual(u.registry_tags(('docker.io', 'example/app')), result(['1.2.0', '1.1.0']))

    def test_cli_offline_and_enrichment_failure_preserve_repository(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            raw = [{'id': 'app', 'versions': [{'tag': '1.0.0', 'labels': {'org.nethserver.images': 'example/app:1.0.0'}}]}]
            (p / 'repodata.json').write_text(json.dumps(raw))
            before = (p / 'repodata.json').read_bytes()
            (p / 'repos.json').write_text('[]')
            (p / 'site.json').write_text('{"org":"geniusdynamics"}')
            for config in ['{}', 'invalid JSON']:
                (p / 'upstream.json').write_text(config)
                subprocess.run([sys.executable, str(root / 'buildsite.py'), '--org-repos', 'repos.json'], cwd=p, check=True, capture_output=True)
                catalog = json.loads((p / 'catalog.json').read_text())
                self.assertEqual(catalog['apps'][0]['id'], 'app')
                self.assertIn('score', catalog['apps'][0])
                self.assertEqual((p / 'repodata.json').read_bytes(), before)
                if config == '{}':
                    self.assertEqual(catalog['apps'][0]['upstream_check']['status'], 'unknown')

    def test_ghcr_pagination_and_auth_stays_on_registry(self):
        calls = []
        def get(url, headers=None):
            calls.append((url, headers))
            if '/token?' in url:
                return {'token': 'secret'}, {}
            return {'tags': ['1.0.0']}, {'Link': '<https://evil.invalid/tags>; rel="next"'}
        with patch.object(u, 'get_json', side_effect=get):
            r = u.registry_tags(('ghcr.io', 'org/app'))
        self.assertEqual(len(calls), 2)
        self.assertFalse(r['complete'])
        self.assertNotIn('secret', str(r))

    def test_enrichment_selects_stable_and_deduplicates_dependencies(self):
        apps = [{'id': 'one'}, {'id': 'two'}]
        raw = [{'id': n, 'versions': [{'tag': '2.0.0-testing.1', 'labels': {'org.nethserver.images': 'example/app:99.0.0'}},
                                    {'tag': '1.0.0', 'labels': {'org.nethserver.images': 'example/app:1.0.0'}}]} for n in ['one', 'two']]
        with patch.object(u, 'registry_tags', return_value=result(['1.0.0', '1.1.0'])) as lookup:
            u.enrich(apps, raw, {n: {'image': 'docker.io/example/app'} for n in ['one', 'two']}, lambda *args: None, None, shown_version)
        self.assertEqual(lookup.call_count, 1)
        for app in apps:
            self.assertEqual(app['upstream_check']['module_version'], '1.0.0')
            self.assertEqual(app['upstream_check']['status'], 'update_available')

    def test_offline_build_makes_no_requests(self):
        apps = [{'id': 'app'}]
        raw = [{'id': 'app', 'versions': [{'tag': '1.0.0', 'labels': {'org.nethserver.images': 'example/app:1.0.0'}}]}]
        with patch.object(u, 'get_json', side_effect=AssertionError('network called')):
            u.enrich(apps, raw, {}, lambda *args: self.fail('github called'), None, shown_version, offline=True)
        self.assertEqual(apps[0]['upstream_check']['status'], 'unknown')


if __name__ == '__main__':
    unittest.main()
