"""Exercise generated repodata and the NS8 minimum-from upgrade selection contract."""
import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

import semver

ROOT = Path(__file__).resolve().parents[1]
POLICY = (ROOT / 'pins.yml').read_text()


class UpgradePins(unittest.TestCase):
    def generate(self, latest='5.1.0', policy=POLICY, fail=None, labels=None, extra_tags=()):
        tags = list(dict.fromkeys([latest, '4.2.0', '5.0.0', *extra_tags]))
        labels = labels or {}
        class Inspect:
            def __init__(self, argv, **kwargs):
                ref = argv[-1].removeprefix('docker://')
                name = ref.rsplit('/', 1)[-1].split(':')[0]
                tag = ref.rsplit(':', 1)[1] if ':' in ref.rsplit('/', 1)[-1] else None
                if fail == (name, tag):
                    raise RuntimeError('Simulated registry failure')
                image_labels = {'org.nethserver.min-core': '3.0.0', 'sentinel': 'kept', **labels.get(tag, {})}
                self.stdout = io.StringIO(json.dumps({'RepoTags': tags} if tag is None else {'Labels': image_labels}))
            def __enter__(self): return self
            def __exit__(self, *args): pass
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            if policy is not None:
                (work / 'pins.yml').write_text(policy)
            for name in ['erpnext', 'unrelated']:
                module = work / name
                module.mkdir()
                (module / 'metadata.json').write_text(json.dumps({'source': 'ghcr.io/geniusdynamics/' + name}))
                (module / 'logo.png').write_bytes(b'\x89PNG\r\n\x1a\n')
            original = '[{"sentinel":"previous publication"}]'
            (work / 'repodata.json').write_text(original)
            before = Path.cwd()
            try:
                os.chdir(work)
                with patch('subprocess.Popen', Inspect), patch('sys.argv', ['createrepo.py']), contextlib.redirect_stderr(io.StringIO()):
                    try:
                        runpy.run_path(str(ROOT / 'createrepo.py'), run_name='__main__')
                    except BaseException:
                        self.assertEqual((work / 'repodata.json').read_text(), original)
                        raise
                return {m['id']: m for m in json.loads((work / 'repodata.json').read_text())}
            finally:
                os.chdir(before)

    def next_version(self, module, installed, testing=False):
        # NS8 list_updates examines descending targets and enforces min-from.
        current = semver.VersionInfo.parse(installed)
        for v in sorted(module['versions'], key=lambda v: semver.VersionInfo.parse(v['tag']), reverse=True):
            target = semver.VersionInfo.parse(v['tag'])
            floor = semver.VersionInfo.parse(v['labels'].get('org.nethserver.min-from', '0.0.0'))
            if target > current and current >= floor and (testing or not target.prerelease):
                return v['tag']
        return None

    def test_checkpoints_and_floors_are_generated(self):
        modules = self.generate()
        versions = {v['tag']: v for v in modules['erpnext']['versions']}
        self.assertEqual(set(versions), {'4.2.0', '5.0.0', '5.1.0'})
        self.assertNotIn('org.nethserver.min-from', versions['4.2.0']['labels'])
        self.assertEqual(versions['5.0.0']['labels']['org.nethserver.min-from'], '4.2.0')
        self.assertEqual(versions['5.1.0']['labels']['org.nethserver.min-from'], '5.0.0')
        self.assertEqual(versions['5.1.0']['labels']['sentinel'], 'kept')
        self.assertEqual([v['tag'] for v in modules['unrelated']['versions']], ['5.1.0'])
        self.assertNotIn('org.nethserver.min-from', modules['unrelated']['versions'][0]['labels'])

    def test_upgrade_boundaries_and_no_downgrades(self):
        m = self.generate()['erpnext']
        for old in ['0.0.1-alpha.1', '1.0.0', '3.3.1', '4.0.1', '4.1.0', '4.2.0-rc.1']:
            with self.subTest(old=old): self.assertEqual(self.next_version(m, old), '4.2.0')
        for old in ['4.2.0', '4.2.1', '4.9.9', '5.0.0-rc.1']:
            with self.subTest(old=old): self.assertEqual(self.next_version(m, old), '5.0.0')
        self.assertEqual(self.next_version(m, '5.0.0'), '5.1.0')
        self.assertIsNone(self.next_version(m, '5.1.0'))
        self.assertIsNone(self.next_version(m, '6.0.0'))

    def test_future_versions_and_testing_keep_both_checkpoints(self):
        m = self.generate(latest='6.0.0', extra_tags=('7.0.0-beta.1',))['erpnext']
        for testing in [False, True]:
            self.assertEqual(self.next_version(m, '4.1.0', testing), '4.2.0')
            self.assertEqual(self.next_version(m, '4.2.0', testing), '5.0.0')
        self.assertEqual(self.next_version(m, '5.0.0'), '6.0.0')
        self.assertEqual(self.next_version(m, '5.0.0', True), '7.0.0-beta.1')

    def test_existing_stricter_image_restrictions_are_preserved(self):
        m = self.generate(latest='6.1.0', labels={'6.1.0': {'org.nethserver.min-from': '6.0.0'}})['erpnext']
        v = next(v for v in m['versions'] if v['tag'] == '6.1.0')
        self.assertEqual(v['labels']['org.nethserver.min-from'], '6.0.0')

    def test_checkpoint_is_not_duplicated_when_latest(self):
        m = self.generate(latest='5.0.0')['erpnext']
        self.assertEqual([v['tag'] for v in m['versions']].count('5.0.0'), 1)

    def test_missing_checkpoints_abort_without_overwriting_metadata(self):
        for tag in ['4.2.0', '5.0.0', None]:
            with self.subTest(tag=tag), self.assertRaises(SystemExit):
                self.generate(fail=('erpnext', tag))

    def test_invalid_policy_aborts_without_overwriting_metadata(self):
        for policy in [None, '[]', 'false', 'erpnext: nope', 'erpnext: [{match: ">5.0.0", min_from: nope}]', 'erpnext: [{min_from: "5.0.0"}]', 'erpnext: [{match: nonsense, min_from: "5.0.0"}]']:
            with self.subTest(policy=policy), self.assertRaises(SystemExit): self.generate(policy=policy)

    def test_legacy_remove_and_pin_rules_still_work(self):
        policy = 'erpnext:\n  - {match: ">=5.0.0", remove: true}\n  - {tag: "4.2.0", prepend: false}\n'
        m = self.generate(policy=policy)['erpnext']
        self.assertEqual([v['tag'] for v in m['versions']], ['4.2.0'])


if __name__ == '__main__':
    unittest.main()
