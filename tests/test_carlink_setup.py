"""Public commands install official CarLink directly, without an older receiver."""
import contextlib
import io
import json
from unittest.mock import patch

import carlink_setup as public
import carlink_trial as legacy
import carlink_permissions as permissions
import oshan_x7 as core
from test_oshan_x7 import DeviceFixture, FakeADB


class CarLinkADB(FakeADB):
    def __init__(self, receiver=False):
        super().__init__(receiver=receiver)
        self.packages[core.RECEIVER].update(version_code=10007, version_name="1.0.7")
        self.paths[core.RECEIVER] = "/data/app/com.carlink.app-example==/base.apk"
        self.hashes[self.paths[core.RECEIVER]] = core.PROFILE["receiver"]["sha256"]
        self.permission_owner = None
        self.receiver_uid = 10080
        self.grants = {p: False for p in permissions.RUNTIME}
        self.ops = {op: "default" for op in permissions.APPOPS}
        self.secure = {"enabled_accessibility_services": "null", "accessibility_enabled": "0"}
        self.whitelisted = False
        self.fail_permission = False
        self.ghost_receivers = set()

    def respond(self, words, root):
        if words[:5] == ['pm','list','packages','--user','0'] and words[-1] in self.ghost_receivers:
            return ''
        if words == ["cat", "/data/system/packages.xml"] and root:
            item = '' if self.permission_owner is None else (
                '<item name="com.andrerinas.openheadunit.permission.NAVIGATION_UPDATE" '
                'package="' + self.permission_owner + '"/>')
            return '<packages><permissions>' + item + '</permissions></packages>'
        if words == ["dumpsys", "package", core.RECEIVER]:
            requested = '\n'.join(permissions.RUNTIME)
            grants = '\n'.join(p + ': granted=' + str(v).lower() for p,v in self.grants.items())
            return (super().respond(words, root) + f'\nuserId={self.receiver_uid}\npkgFlags=[ HAS_CODE ]\n'
                    + 'requested permissions:\n' + requested + '\ninstall permissions:\nruntime permissions:\n' + grants)
        if words[:2] == ["appops", "get"] and root:
            return words[-1] + ': ' + self.ops[words[-1]]
        if words[:2] == ["appops", "set"] and root:
            self.mutate('appop:' + words[-2], lambda: self.ops.update({words[-2]: words[-1]}))
            return ''
        if words[:2] in (["pm", "grant"], ["pm", "revoke"]) and root:
            def change():
                if not self.fail_permission: self.grants[words[-1]] = words[1] == 'grant'
            self.mutate(words[1] + ':' + words[-1], change)
            return ''
        if words[:3] == ['settings','--user','0'] and root:
            if words[3] == 'get': return self.secure.get(words[-1], 'null')
            if words[3] == 'put':
                self.mutate('setting:' + words[-2], lambda: self.secure.update({words[-2]: words[-1]}))
            elif words[3] == 'delete':
                self.mutate('setting:' + words[-1], lambda: self.secure.update({words[-1]: 'null'}))
            return ''
        if words[:3] == ['dumpsys','deviceidle','whitelist'] and root:
            if words[-1].startswith('='): return str(self.whitelisted).lower()
            self.mutate('battery', lambda: setattr(self, 'whitelisted', words[-1].startswith('+')))
            return ''
        if words == ['dumpsys','activity','services',core.RECEIVER]:
            return ('* ServiceRecord{abc u0 '+permissions.SERVICE+'}\n'
                    'permission=android.permission.BIND_ACCESSIBILITY_SERVICE\n'
                    'app=ProcessRecord{abc 1234:com.carlink.app/u0a80}\n'
                    'requested=true received=true hasBound=true\n'
                    '* Client AppBindRecord{abc ProcessRecord{abc 999:system/1000}}\n')
        return super().respond(words, root)


class PublicSetupTests(DeviceFixture):
    def setUp(self):
        super().setUp()
        self.config = public.configuration(core)
        self.config.__enter__()
        self.addCleanup(self.config.__exit__, None, None, None)

    def command(self, car, command, *extra):
        output = io.StringIO()
        with patch.object(core, "ADB", return_value=car), contextlib.redirect_stdout(output):
            code = core.main([command, "--state-dir", str(self.state), "--json", *extra])
        return code, json.loads(output.getvalue())

    def test_public_setup_installs_carlink_from_factory_and_restores_factory(self):
        car = CarLinkADB()
        code, result = self.command(car, "setup", "--reboot-check")
        self.assertEqual(0, code, result)
        self.assertEqual("carlink", result["launcher"]["build"])
        self.assertTrue(result["android_reboot_verified"])
        self.assertTrue(car.packages["com.carlink.app"]["installed"])
        self.assertNotIn("com.andrerinas.headunitrevived", car.packages)
        journal = core.load_backup(core.backup_path(car, self.state), car)
        self.assertFalse(journal["original"]["receiver"]["installed"])
        before = car.writes[:]
        self.assertEqual(0, self.command(car, "setup", "--reboot-check")[0])
        self.assertEqual(before, car.writes)
        self.assertEqual(0, self.command(car, "restore")[0])
        self.assertFalse(car.launcher_updated)
        self.assertFalse(car.packages["com.carlink.app"]["installed"])
        self.assertEqual(0, car.packages[core.CARAUTO]["enabled"])
        self.assertEqual(-1, car.layout)
        before = car.writes[:]
        self.assertEqual(0, self.command(car, "restore")[0])
        self.assertEqual(before, car.writes)

    def test_permissions_are_automatic_before_first_app_launch_and_preserve_other_services(self):
        car = CarLinkADB()
        car.secure.update(enabled_accessibility_services='another.app/.Service',accessibility_enabled='1')
        self.assertEqual(0, self.command(car, "setup", "--reboot-check")[0])
        self.assertTrue(all(car.grants.values()))
        self.assertTrue(all(x == 'allow' for x in car.ops.values()))
        self.assertLess(car.writes.index('setting:enabled_accessibility_services'),car.writes.index('launch'))
        self.assertIn('another.app/.Service',car.secure['enabled_accessibility_services'])
        car.secure['enabled_accessibility_services'] += ':third.app/.Service'
        self.assertEqual(0,self.command(car,'restore')[0])
        self.assertEqual('another.app/.Service:third.app/.Service',car.secure['enabled_accessibility_services'])
        self.assertEqual('1',car.secure['accessibility_enabled'])

    def test_public_setup_crash_recovers_with_same_engine(self):
        car = CarLinkADB()
        def crash(name):
            if name == "home" and car.launcher_updated:
                car.log_output += '\n11-02 01:00:00 E AndroidRuntime: Process: com.chinatsp.launcher, PID: 1234'
        car.on_write = crash
        code, result = self.command(car, "setup")
        self.assertEqual(2, code)
        self.assertEqual("restored", result["recovery"]["status"])
        self.assertFalse(car.launcher_updated)
        self.assertFalse(car.packages[core.RECEIVER]["installed"])

    def test_conflicting_permission_or_unknown_carlink_blocks_all_writes(self):
        for kind in ("permission", "hash", "uid"):
            car = CarLinkADB(receiver=kind != "permission")
            if kind == "permission": car.permission_owner = "another.receiver"
            if kind == "hash": car.hashes[car.paths[core.RECEIVER]] = "a" * 64
            if kind == "uid": car.receiver_uid = 1000
            self.assertEqual(2, self.command(car, "setup")[0])
            self.assertEqual([], car.writes)

    def test_preexisting_official_app_is_kept_by_restore(self):
        car = CarLinkADB(receiver=True)
        self.assertEqual(0, self.command(car, "setup")[0])
        self.assertEqual(0, self.command(car, "restore")[0])
        self.assertTrue(car.packages[core.RECEIVER]["installed"])
        self.assertNotIn("uninstall", car.writes)

    def test_profile_pins_match_official_app_and_tested_launcher(self):
        self.assertEqual(legacy.BASE_PIN["sha256"], core.PROFILE["receiver"]["sha256"])
        self.assertEqual(legacy.LAUNCHER_PIN["sha256"], core.PROFILE["launcher"]["update"]["sha256"])
        self.assertEqual("com.carlink.app", core.RECEIVER)
        original=json.loads(core.PROFILE_PATH.read_text())
        self.assertEqual(original['properties'],core.PROFILE['properties'])
        self.assertEqual(original['required_packages'],core.PROFILE['required_packages'])
        for key in ('sha256','bytes','uid','version_code','home','path'):
            self.assertEqual(original['launcher'][key],core.PROFILE['launcher'][key])

    def test_retained_competitor_data_is_not_an_active_receiver(self):
        car=CarLinkADB()
        name='com.andrerinas.headunitrevived'
        car.packages[name]={'installed':True,'enabled':0}
        car.ghost_receivers.add(name)
        code,result=self.command(car,'setup')
        self.assertEqual(0,code,result)

    def test_enabled_competitor_blocks_setup_before_any_writes(self):
        car=CarLinkADB()
        car.packages['com.shihab.diplay']={'installed':True,'enabled':0}
        self.assertEqual(2,self.command(car,'setup')[0])
        self.assertEqual([],car.writes)

    def test_failed_grant_cannot_report_success_and_restores_owned_changes(self):
        car=CarLinkADB();car.fail_permission=True
        code,result=self.command(car,'setup')
        self.assertEqual(2,code)
        self.assertEqual('permissions',result['failed_stage'])
        self.assertEqual('restored',result['recovery']['status'])
        self.assertNotIn('launch',car.writes)
        self.assertFalse(car.packages[core.RECEIVER]['installed'])

    def test_unchanged_preexisting_permissions_are_not_revoked(self):
        car=CarLinkADB(receiver=True)
        car.grants[permissions.RUNTIME[0]]=True
        car.ops['SYSTEM_ALERT_WINDOW']='allow'
        car.whitelisted=True
        self.assertEqual(0,self.command(car,'setup')[0])
        self.assertEqual(0,self.command(car,'restore')[0])
        self.assertTrue(car.grants[permissions.RUNTIME[0]])
        self.assertEqual('allow',car.ops['SYSTEM_ALERT_WINDOW'])
        self.assertTrue(car.whitelisted)

    def test_root_loss_does_not_block_owned_launcher_rollback(self):
        car=CarLinkADB()
        self.assertEqual(0,self.command(car,'setup')[0])
        car.root=False
        code,result=self.command(car,'restore')
        self.assertEqual(2,code)
        self.assertFalse(car.launcher_updated)
        self.assertIn('restore_permissions',result['recovery']['errors'])
        self.assertTrue(car.packages[core.RECEIVER]['installed'])
        car.root=True
        self.assertEqual(0,self.command(car,'restore')[0])

    def test_service_name_in_dump_without_system_binding_is_not_success(self):
        car=CarLinkADB()
        original=car.respond
        def missing_binding(words,root):
            if words==['dumpsys','activity','services',core.RECEIVER]:
                return '* ServiceRecord{abc u0 '+permissions.SERVICE+'}\napp=null\n'
            return original(words,root)
        car.respond=missing_binding
        code,result=self.command(car,'setup')
        self.assertEqual(2,code)
        self.assertEqual('permissions',result['failed_stage'])
        self.assertNotIn('launch',car.writes)
