"""Public commands install official CarLink directly, without an older receiver."""
import contextlib
import io
import json
from unittest.mock import Mock, patch

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

    def test_status_requires_current_configuration_before_phone_handoff(self):
        for change in ('layout', 'carauto', 'launcher', 'grant', 'none'):
            with self.subTest(change=change):
                self.state = self.state / change
                car = CarLinkADB()
                self.assertEqual(0, self.command(car, 'setup', '--reboot-check')[0])
                if change == 'layout': car.layout = 2
                if change == 'carauto': car.packages[core.CARAUTO]['enabled'] = 0
                if change == 'launcher':
                    car.launcher_updated = False
                    car.paths[core.PROFILE['launcher']['package']] = core.PROFILE['launcher']['path']
                if change == 'grant': car.grants[permissions.RUNTIME[0]] = False
                before = car.writes[:]
                code, result = self.command(car, 'status')
                self.assertEqual(0, code)
                self.assertEqual(change == 'none', result['configured'])
                self.assertEqual('phone_handoff' if change == 'none' else
                                 'inspect_configuration_drift', result['next_action'])
                self.assertEqual(before, car.writes)

    def test_permission_pause_after_reboot_resumes_without_another_reboot(self):
        car = CarLinkADB()
        def prompt(name):
            if name == 'reboot': car.permission_prompt = True
        car.on_write = prompt
        code, result = self.command(car, 'setup', '--reboot-check')
        self.assertEqual(3, code)
        self.assertEqual('inspect_permission_prompt', result['next_action'])
        self.assertEqual(1, car.writes.count('reboot'))
        car.on_write, car.permission_prompt = None, False
        code, result = self.command(car, 'setup', '--reboot-check')
        self.assertEqual(0, code, result)
        self.assertTrue(result['android_reboot_verified'])
        self.assertEqual(1, car.writes.count('reboot'))
        before = car.writes[:]
        self.assertEqual(0, self.command(car, 'setup', '--reboot-check')[0])
        self.assertEqual(before, car.writes)

    def test_absent_carlink_restore_cleans_global_access_and_keeps_other_services(self):
        car = CarLinkADB()
        self.assertEqual(0, self.command(car, 'setup')[0])
        car.packages[core.RECEIVER]['installed'] = False
        car.secure['enabled_accessibility_services'] += ':another.app/.Service'
        before = len(car.commands)
        code, result = self.command(car, 'restore')
        self.assertEqual(0, code, result)
        self.assertEqual('restored', result['status'])
        self.assertFalse(car.launcher_updated)
        self.assertFalse(car.whitelisted)
        self.assertEqual('another.app/.Service', car.secure['enabled_accessibility_services'])
        self.assertEqual('1', car.secure['accessibility_enabled'])
        commands = str(car.commands[before:])
        self.assertNotIn('pm revoke', commands)
        self.assertNotIn('appops set', commands)
        self.assertNotIn('uninstall', car.writes)
        writes = car.writes[:]
        self.assertEqual(0, self.command(car, 'restore')[0])
        self.assertEqual(writes, car.writes)

    def test_uncertain_receiver_removal_can_finish_restore(self):
        car = CarLinkADB()
        self.assertEqual(0, self.command(car, 'setup')[0])
        car.fail_at, car.fail_after_effect = 'uninstall', True
        self.assertEqual(2, self.command(car, 'restore')[0])
        car.disconnected, car.fail_at = False, None
        self.assertEqual(0, self.command(car, 'restore')[0])
        self.assertEqual(1, car.writes.count('uninstall'))

    def test_unknown_replacement_keeps_permission_settings_untouched(self):
        car = CarLinkADB()
        self.assertEqual(0, self.command(car, 'setup')[0])
        car.hashes[car.paths[core.RECEIVER]] = 'a' * 64
        original_services = car.secure.copy()
        code, result = self.command(car, 'restore')
        self.assertEqual(2, code)
        self.assertFalse(car.launcher_updated)
        self.assertEqual(original_services, car.secure)
        self.assertTrue(car.packages[core.RECEIVER]['installed'])

    def test_no_effect_permission_commands_are_not_marked_verified(self):
        for failure in ('grant', 'appop', 'battery', 'service'):
            with self.subTest(failure=failure):
                self.state = self.state / failure
                car = CarLinkADB()
                respond = car.respond
                def no_effect(words, root):
                    if ((failure == 'grant' and words[:2] == ['pm', 'grant']) or
                        (failure == 'appop' and words[:2] == ['appops', 'set']) or
                        (failure == 'battery' and words[-1] == '+' + core.RECEIVER) or
                        (failure == 'service' and words[:4] == ['settings', '--user', '0', 'put'])):
                        return ''
                    return respond(words, root)
                car.respond = no_effect
                code, result = self.command(car, 'setup')
                self.assertEqual(2, code)
                self.assertEqual('permissions', result['failed_stage'])
                journal = permissions.load(core, car, self.state)
                name = {'grant': 'grant:' + permissions.RUNTIME[0],
                        'appop': 'appop:' + permissions.APPOPS[0],
                        'battery': 'battery', 'service': 'usb_auto_confirm'}[failure]
                entry = next(x for x in journal['operations'] if x['name'] == name)
                self.assertFalse(entry['complete'])
                self.assertNotIn('verified_at', entry)

    def test_failed_permission_restore_is_not_marked_verified(self):
        car = CarLinkADB()
        self.assertEqual(0, self.command(car, 'setup')[0])
        respond = car.respond
        car.respond = lambda words, root: '' if words[:2] == ['pm', 'revoke'] else respond(words, root)
        self.assertEqual(2, self.command(car, 'restore')[0])
        journal = permissions.load(core, car, self.state)
        entry = next(x for x in journal['operations'] if x['name'].startswith('restore:grant:'))
        self.assertFalse(entry['complete'])
        self.assertTrue(car.packages[core.RECEIVER]['installed'])
        car.respond = respond
        self.assertEqual(0, self.command(car, 'restore')[0])

    def legacy_record(self, car):
        legacy.journal_path(core, car, self.state).write_text('{}')
        instance = Mock()
        instance.pin = legacy.BASE_PIN
        instance.load.return_value = {'restored': False, 'phase': 'trial_ready', 'primary_receiver': 'carlink'}
        instance.inspect.return_value = ({}, core.receiver_state(car))
        return instance

    def test_legacy_status_adapter_uses_current_configuration(self):
        car = CarLinkADB()
        self.assertEqual(0, self.command(car, 'setup', '--reboot-check')[0])
        instance = self.legacy_record(car)
        car.layout = 2
        before = car.writes[:]
        with patch.object(legacy, 'Trial', return_value=instance), patch.object(legacy, 'run', return_value={
                'primary_receiver': 'carlink', 'trial_eligible': True,
                'carlink_launcher_reboot_verified': True, 'next_action': 'phone_handoff'}):
            code, result = self.command(car, 'status')
        self.assertEqual(0, code, result)
        self.assertFalse(result['configured'])
        self.assertEqual('inspect_configuration_drift', result['next_action'])
        self.assertEqual(before, car.writes)

    def test_legacy_status_requires_permission_reboot_record(self):
        car = CarLinkADB()
        self.assertEqual(0, self.command(car, 'setup')[0])
        instance = self.legacy_record(car)
        with patch.object(legacy, 'Trial', return_value=instance), patch.object(legacy, 'run', side_effect=lambda *a: {
                'primary_receiver': 'carlink', 'trial_eligible': True,
                'carlink_launcher_reboot_verified': True, 'next_action': 'phone_handoff'}):
            code, result = self.command(car, 'status')
            self.assertEqual(0, code, result)
            self.assertTrue(result['configured'])
            self.assertFalse(result['android_reboot_verified'])
            self.assertEqual('rerun_setup_with_reboot_check', result['next_action'])
            journal = permissions.load(core, car, self.state)
            journal['android_reboot_verified'] = True
            core.write_json(permissions.path(core, car, self.state), journal)
            code, result = self.command(car, 'status')
            self.assertEqual(0, code, result)
            self.assertEqual('phone_handoff', result['next_action'])

    def test_legacy_setup_adapter_reboot_and_permission_pause(self):
        car = CarLinkADB()
        self.assertEqual(0, self.command(car, 'setup')[0])
        instance = self.legacy_record(car)
        with patch.object(legacy, 'Trial', return_value=instance):
            code, result = self.command(car, 'setup')
            self.assertEqual(0, code, result)
            self.assertEqual('rerun_setup_with_reboot_check', result['next_action'])
            def prompt(name):
                if name == 'reboot': car.permission_prompt = True
            car.on_write = prompt
            code, result = self.command(car, 'setup', '--reboot-check')
            self.assertEqual(3, code, result)
            self.assertEqual('inspect_permission_prompt', result['next_action'])
            car.on_write, car.permission_prompt = None, False
            code, result = self.command(car, 'setup', '--reboot-check')
            self.assertEqual(0, code, result)
            self.assertTrue(result['android_reboot_verified'])
            self.assertEqual(1, car.writes.count('reboot'))

    def test_recorded_reboot_request_observes_changed_boot_without_resending(self):
        car = CarLinkADB()
        self.assertEqual(0, self.command(car, 'setup')[0])
        path = core.backup_path(car, self.state)
        journal = core.load_backup(path, car)
        journal['reboot_from_boot_id'] = car.boot_id
        core.write_json(path, journal)
        car.boot_id = '33333333-3333-4333-8333-333333333333'
        result = core.reboot_check(car, path, journal)
        self.assertTrue(result['android_reboot_verified'])
        self.assertNotIn('reboot', car.writes)
        self.assertEqual(car.boot_id, core.load_backup(path, car)['observed_reboot_boot_id'])

    def test_recorded_reboot_without_new_boot_fails_without_resending(self):
        car = CarLinkADB()
        self.assertEqual(0, self.command(car, 'setup')[0])
        path = core.backup_path(car, self.state)
        journal = core.load_backup(path, car)
        journal['reboot_from_boot_id'] = car.boot_id
        with self.assertRaises(core.SetupError): core.reboot_check(car, path, journal)
        self.assertNotIn('reboot', car.writes)
        self.assertNotIn('observed_reboot_boot_id', journal)

    def test_corrupt_reboot_identity_refuses_setup_before_writes(self):
        car = CarLinkADB()
        self.assertEqual(0, self.command(car, 'setup')[0])
        path = core.backup_path(car, self.state)
        journal = core.load_backup(path, car)
        journal['reboot_from_boot_id'] = 'not a boot ID'
        core.write_json(path, journal)
        before = car.writes[:]
        self.assertEqual(2, self.command(car, 'setup', '--reboot-check')[0])
        self.assertEqual(before, car.writes)
