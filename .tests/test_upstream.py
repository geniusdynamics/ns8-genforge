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

    def test_major_versions_are_separate_from_routine_updates(self):
        r = self.compare('15.20-alpine3.24', ['15.20-alpine3.24', '15.21-alpine3.24', '18.7-alpine3.24'])
        self.assertEqual((r['status'], r['latest'], r['latest_major']), ('update_available', '15.21-alpine3.24', '18.7-alpine3.24'))
        r = self.compare('15.21', ['15.21', '18.7'])
        self.assertEqual((r['status'], r['latest'], r['latest_major']), ('major_available', '15.21', '18.7'))
        self.assertIn('migration', r['reason'])
        r = self.compare('18.7', ['18.7', '17.12'])
        self.assertEqual((r['status'], r['latest_major']), ('current', None))

    def test_scheme_change_and_missing_tag_are_not_major_upgrades(self):
        r = self.compare('0.6.25', ['0.6.24', '0.6.25', '2021.12.16'])
        self.assertEqual((r['status'], r['latest_major']), ('current', None))
        r = self.compare('0.6.25', ['0.6.24', '1.0.0'])
        self.assertEqual(r['status'], 'unknown')
        self.assertIn('not found', r['reason'])
        r = self.compare('2025.12.6', ['2025.12.6', '2026.8.5'])
        self.assertEqual((r['status'], r['latest_major']), ('major_available', '2026.8.5'))

    def test_major_release_mapping(self):
        cfg = {'github': 'o/r', 'versions': {'1.0.0': '8.10.2'}}
        get = lambda *args: {'tag_name': 'v9.0.1'}
        self.assertEqual(u.release_check(cfg, '1.0.0', get, None)['status'], 'major_available')

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

    def test_dockerhub_registry_pagination_is_complete_only_at_end(self):
        responses = [({'token': 't'}, {}),
                     ({'tags': ['1.2.0']}, {'Link': '</v2/example/app/tags/list?last=1.2.0&n=10000>; rel="next"'}),
                     ({'tags': ['1.1.0']}, {})]
        with patch.object(u, 'get_json', side_effect=responses):
            self.assertEqual(u.registry_tags(('docker.io', 'example/app')), result(['1.2.0', '1.1.0']))

    def test_docker_hub_credentials_only_reach_the_token_service(self):
        calls = []
        def get(url, headers=None):
            calls.append((url, headers or {}))
            return ({'token': 'bearer'}, {}) if url.startswith('https://auth.docker.io/') else ({'tags': ['1.0.0']}, {})
        env = {'DOCKER_HUB_USERNAME': 'bot', 'DOCKER_HUB_ACCESS_TOKEN': 'pat-secret'}
        with patch.dict(u.os.environ, env), patch.object(u, 'get_json', side_effect=get):
            r = u.registry_tags(('docker.io', 'library/postgres'))
        self.assertTrue(r['complete'])
        self.assertTrue(calls[0][1]['Authorization'].startswith('Basic '))
        self.assertEqual(calls[1][1]['Authorization'], 'Bearer bearer')
        self.assertTrue(calls[1][0].startswith('https://registry-1.docker.io/v2/library/postgres/tags/list'))
        self.assertNotIn('pat-secret', str(r))

    def test_docker_hub_without_credentials_is_anonymous(self):
        calls = []
        def get(url, headers=None):
            calls.append(headers)
            return ({'token': 't'}, {}) if 'auth.docker.io' in url else ({'tags': []}, {})
        with patch.dict(u.os.environ, {}, clear=True), patch.object(u, 'get_json', side_effect=get):
            u.registry_tags(('docker.io', 'library/redis'))
        self.assertIsNone(calls[0])

    def test_lscr_uses_ghcr_api_and_links(self):
        image = u.image_ref('lscr.io/linuxserver/calibre-web:0.6.24')
        self.assertEqual(image['registry'], 'lscr.io')
        self.assertTrue(image['url'].startswith('https://github.com/linuxserver/pkgs/container/'))
        urls = []
        def get(url, headers=None):
            urls.append(url)
            return ({'token': 't'}, {}) if '/token?' in url else ({'tags': ['0.6.24']}, {})
        with patch.object(u, 'get_json', side_effect=get):
            self.assertTrue(u.registry_tags(('lscr.io', 'linuxserver/calibre-web'))['complete'])
        self.assertTrue(all(x.startswith('https://ghcr.io/') for x in urls))

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
            self.assertEqual(app['upstream_check']['dependency_updates'], 0)

    def test_dependency_updates_are_counted_apart_from_the_application(self):
        apps = [{'id': 'app'}]
        raw = [{'id': 'app', 'versions': [{'tag': '1.0.0', 'labels': {'org.nethserver.images': 'example/app:2.0.0 postgres:15.20 redis:7.4.1'}}]}]
        tags = {('docker.io', 'example/app'): result(['2.0.0']), ('docker.io', 'library/postgres'): result(['15.20', '18.7']),
                ('docker.io', 'library/redis'): result(['7.4.1', '7.4.2'])}
        with patch.object(u, 'registry_tags', side_effect=lambda key: tags[key]):
            u.enrich(apps, raw, {}, lambda *args: None, None, shown_version)
        check = apps[0]['upstream_check']
        self.assertEqual((check['status'], check['dependency_updates'], check['dependency_majors']), ('current', 1, 1))

    def test_offline_build_makes_no_requests(self):
        apps = [{'id': 'app'}]
        raw = [{'id': 'app', 'versions': [{'tag': '1.0.0', 'labels': {'org.nethserver.images': 'example/app:1.0.0'}}]}]
        with patch.object(u, 'get_json', side_effect=AssertionError('network called')):
            u.enrich(apps, raw, {}, lambda *args: self.fail('github called'), None, shown_version, offline=True)
        self.assertEqual(apps[0]['upstream_check']['status'], 'unknown')


if __name__ == '__main__':
    unittest.main()
