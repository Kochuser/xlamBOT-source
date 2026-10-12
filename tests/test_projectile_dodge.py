"""Visual trajectories must survive camera motion and all movement guards."""

import math
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import cv2
import numpy as np

from projectile_dodge import ProjectileDodge, components, CAMERA_SIZE
from play import Play


class ProjectileDodgeTests(unittest.TestCase):
    def setUp(self):
        texture = np.random.default_rng(19).integers(
            20, 145, (720, 1280), dtype=np.uint8
        )
        self.background = np.repeat(texture[:, :, None], 3, axis=2)
        self.player = (640.0, 380.0)

    def frame(self, shot=(740, 380), pan=(0, 0)):
        frame = np.roll(self.background, (pan[1], pan[0]), axis=(0, 1)).copy()
        if shot is not None:
            cv2.circle(
                frame, (shot[0] + pan[0], shot[1] + pan[1]), 6, (255, 30, 100), -1
            )
        return frame

    def approaching(self):
        dodge = ProjectileDodge()
        for i in range(3):
            dodge.observe(
                self.frame((752 - 16 * i, 380)), 10 + i * 0.08, self.player, []
            )
        self.assertEqual(len(dodge.threats), 1)
        return dodge

    def test_incoming_shot_avoids_collision_and_keeps_heading(self):
        dodge = self.approaching()
        base = (100.0, 0.0)
        result = dodge.choose(base, self.player, 15, 130, 10.17, lambda v: True)
        self.assertTrue(dodge.active)
        self.assertGreater(abs(result[1]), 50)
        chosen = tuple(v * 130 / math.hypot(*result) for v in result)
        self.assertGreater(
            dodge.clearance(dodge.threats, self.player, 15, chosen),
            dodge.clearance(dodge.threats, self.player, 15, (130, 0)) + 5,
        )
        self.assertEqual(
            dodge.choose(base, self.player, 15, 130, 10.18, lambda v: True), result
        )

    def test_receding_shot_does_not_override(self):
        dodge = ProjectileDodge()
        for i in range(3):
            dodge.observe(
                self.frame((730 + 16 * i, 380)), 10 + i * 0.08, self.player, []
            )
        base = (-100.0, 0.0)
        self.assertEqual(
            dodge.choose(base, self.player, 15, 130, 10.17, lambda v: True), base
        )
        self.assertFalse(dodge.active)

    def test_fast_projectile_can_associate_inside_the_supported_speed_bound(self):
        dodge = ProjectileDodge()
        for i in range(3):
            dodge.observe(self.frame((942-96*i,380)),10+i*.08,self.player,[])
        self.assertEqual(len(dodge.threats),1)
        self.assertAlmostEqual(dodge.threats[0]['vx'],-1200,delta=25)

    def test_urgent_pair_reacts_before_third_frame_to_a_close_fast_impact(self):
        dodge = ProjectileDodge()
        for i in range(2):
            dodge.observe(self.frame((942-96*i,380)),10+i*.08,self.player,[],body=15)
        self.assertEqual(len(dodge.threats),1)
        self.assertEqual(dodge.threats[0]['confirmation'],'urgent_pair')
        self.assertEqual(dodge.threats[0]['hits'],2)
        dodge.choose((100,0),self.player,15,130,10.08,lambda v:True)
        self.assertTrue(dodge.active)

    def test_two_frame_miss_receding_shot_and_uncertain_camera_are_not_urgent(self):
        for case in ('miss','receding','camera','no_body'):
            dodge=ProjectileDodge()
            for i in range(2):
                x=846+96*i if case=='receding' else 942-96*i
                y=480 if case=='miss' else 380
                if case=='camera':
                    with patch('projectile_dodge.cv2.phaseCorrelate',return_value=((0.,0.),.6)):
                        dodge.observe(self.frame((x,y)),10+i*.08,self.player,[],body=15)
                else:dodge.observe(self.frame((x,y)),10+i*.08,self.player,[],body=None if case=='no_body' else 15)
            self.assertFalse(dodge.threats,case)

    def test_jump_beyond_speed_limit_does_not_confirm_a_fast_pair(self):
        dodge=ProjectileDodge()
        for i,x in enumerate((930,720)):
            dodge.observe(self.frame((x,380)),10+i*.08,self.player,[],body=15)
        self.assertFalse(dodge.threats)
        self.assertEqual(dodge.tracks[0]['hits'],1)

    def test_growing_effect_and_invalid_camera_response_cannot_create_urgent_pair(self):
        dodge=ProjectileDodge()
        for i,radius in enumerate((5.,8.)):
            with patch('projectile_dodge.components',return_value=[(942.-96*i,380.,radius)]):
                dodge.observe(self.frame(None),10+i*.08,self.player,[],body=15)
        self.assertFalse(dodge.threats)
        dodge=ProjectileDodge()
        for i in range(2):
            with patch('projectile_dodge.cv2.phaseCorrelate',return_value=((0.,0.),float('inf'))):
                dodge.observe(self.frame((942-96*i,380)),10+i*.08,self.player,[],body=15)
        self.assertFalse(dodge.threats);self.assertFalse(dodge.camera_ok)

    def test_urgent_pair_keeps_original_timestamp_and_expires_after_gap(self):
        dodge=ProjectileDodge()
        for i in range(2):dodge.observe(self.frame((942-96*i,380)),10+i*.08,self.player,[],body=15)
        stamp=dodge.stamp
        dodge.observe(self.frame((840,380)),10.09,self.player,[],body=15)
        self.assertEqual(dodge.snapshot()['observed_at'],stamp)
        self.assertEqual(dodge.choose((100,0),self.player,15,130,10.24,lambda v:True),(100,0))
        dodge.observe(self.frame((710,380)),11,self.player,[],body=15)
        self.assertFalse(dodge.threats)

    def test_collision_free_crossfire_escape_outranks_preference(self):
        dodge=ProjectileDodge();dodge.stamp=10.
        dodge.threats=[
            dict(x=-88.56297325499007,y=68.2235156500987,vx=-186.30828659859108,vy=-306.0696052731995,r=5.),
            dict(x=-105.98341049395839,y=27.53089876090573,vx=382.63951790149906,vy=-10.570577108815655,r=5.)]
        safe=lambda v:abs(v[1])<1e-6 and abs(v[0])>.9
        chosen=dodge.choose((100,100),(0,0),20,100,10.,safe)
        self.assertLess(chosen[0],0)
        velocity=tuple(x*100/math.hypot(*chosen) for x in chosen)
        self.assertGreater(dodge.clearance(dodge.threats,(0,0),20,velocity),0)

    def test_heading_hold_cannot_keep_collision_when_free_escape_exists(self):
        dodge=ProjectileDodge();dodge.stamp=10.;dodge.heading=(1.,0.);dodge.heading_at=9.9
        dodge.threats=[
            dict(x=-88.56297325499007,y=68.2235156500987,vx=-186.30828659859108,vy=-306.0696052731995,r=5.),
            dict(x=-105.98341049395839,y=27.53089876090573,vx=382.63951790149906,vy=-10.570577108815655,r=5.)]
        chosen=dodge.choose((100,100),(0,0),20,100,10.,lambda v:abs(v[1])<1e-6 and abs(v[0])>.9)
        self.assertLess(chosen[0],0)

    def test_stopping_avoids_crossing_shot_when_moving_routes_are_blocked(self):
        dodge=ProjectileDodge();dodge.stamp=10.
        dodge.threats=[dict(x=700.,y=310.,vx=0.,vy=200.,r=5.)]
        chosen=dodge.choose((100,0),self.player,20,130,10.,lambda v:math.hypot(*v)<1e-6)
        self.assertEqual(chosen,(0.,0.));self.assertTrue(dodge.active)
        self.assertGreater(dodge.clearance(dodge.threats,self.player,20,(0,0)),0)
        self.assertEqual(dodge.snapshot()['plan']['reason'],'hold_position')

    def test_camera_pan_does_not_turn_stationary_effect_into_projectile(self):
        dodge = ProjectileDodge()
        for i in range(4):
            dodge.observe(
                self.frame((730, 380), (16 * i, 0)),
                10 + i * 0.08,
                (640 + 16 * i, 380),
                [],
            )
        self.assertTrue(dodge.camera_ok)
        self.assertFalse(dodge.threats)

    def test_projectile_velocity_is_corrected_for_camera_pan(self):
        dodge = ProjectileDodge()
        for i in range(3):
            dodge.observe(
                self.frame((752 - 16 * i, 380), (8 * i, 0)),
                10 + i * 0.08,
                (640 + 8 * i, 380),
                [],
            )
        self.assertEqual(len(dodge.threats), 1)
        self.assertAlmostEqual(dodge.threats[0]["vx"], -200.0, delta=15)

    def test_ui_healthbars_and_character_boxes_are_excluded(self):
        frame = self.frame(None)
        for pos in [(730, 380), (900, 30), (1100, 630), (90, 650)]:
            cv2.circle(frame, pos, 6, (255, 30, 100), -1)
        self.assertFalse(components(frame, self.player, [[710, 390, 750, 420]]))

    def test_old_duplicate_gap_and_resolution_change_discard_predictions(self):
        for kind in ("duplicate", "old", "gap", "size"):
            dodge = self.approaching()
            frame = self.frame((704, 380))
            stamp = {"duplicate": 10.16, "old": 10.0, "gap": 11.0, "size": 10.24}[kind]
            if kind == "size":
                frame = cv2.resize(frame, (640, 360))
            dodge.observe(frame, stamp, self.player, [])
            self.assertFalse(dodge.threats, kind)
        dodge = self.approaching()
        base = (100.0, 0.0)
        self.assertEqual(
            dodge.choose(base, self.player, 15, 130, 10.4, lambda v: True), base
        )
        self.assertFalse(dodge.active)

    def test_blocked_escape_and_missing_frame_keep_original_decision(self):
        dodge = self.approaching()
        base = (100.0, 0.0)
        self.assertEqual(
            dodge.choose(base, self.player, 15, 130, 10.17, lambda v: False), base
        )
        self.assertFalse(dodge.active)
        dodge.observe(None, 10.24, self.player, [])
        self.assertFalse(dodge.tracks)
        self.assertIsNone(dodge.heading)

    def test_ambiguous_crossing_does_not_assign_identity(self):
        dodge = ProjectileDodge()
        dodge.stamp = 10.0
        dodge.gray = cv2.cvtColor(
            cv2.resize(self.background, CAMERA_SIZE, interpolation=cv2.INTER_AREA),
            cv2.COLOR_RGB2GRAY,
        ).astype(np.float32)
        dodge.tracks = [
            dict(x=x, y=380, r=5.0, vx=0.0, vy=0.0, hits=1) for x in (720, 744)
        ]
        with patch("projectile_dodge.components", return_value=[(732.0, 380.0, 5.0)]):
            dodge.observe(self.background, 10.08, self.player, [])
        self.assertEqual(dodge.tracks[0]["hits"], 1)
        self.assertFalse(dodge.threats)

    def test_60_fps_accumulates_motion_without_renewing_cached_timestamps(self):
        dodge = ProjectileDodge()
        for i in range(5):
            dodge.observe(
                self.frame((760 - round(200 * i / 60), 380)),
                10 + i / 60,
                self.player,
                [],
            )
        self.assertEqual(len(dodge.threats), 1)
        original = dodge.stamp
        dodge.observe(self.frame((743, 380)), 10 + 5 / 60, self.player, [])
        self.assertEqual(dodge.stamp, original)
        self.assertEqual(dodge.snapshot()["observed_at"], original)
        self.assertEqual(len(dodge.threats), 1)
        self.assertEqual(
            dodge.choose(
                (100, 0), self.player, 15, 130, original + 0.2, lambda v: True
            ),
            (100, 0),
        )

    def test_no_candidates_skip_camera_work_and_discard_previous_shots(self):
        dodge = self.approaching()
        with patch("projectile_dodge.cv2.phaseCorrelate") as camera:
            dodge.observe(self.frame(None), 10.24, self.player, [])
        camera.assert_not_called()
        self.assertFalse(dodge.threats)
        self.assertFalse(dodge.tracks)
        self.assertIsNone(dodge.gray)

    def play(self):
        play = Play.__new__(Play)
        play.projectile_dodge = self.approaching()
        play.projectile_dodge_enabled = True
        play.window_controller = SimpleNamespace(
            scale_factor=1.0, width_ratio=1.0, height_ratio=1.0
        )
        play.TILE_SIZE = 54
        play.gas_avoidance = True
        play.gas_detection_ok = True
        play.gas_mask = np.zeros((720, 1280), np.uint8)
        play.gas_reach = 3.0
        play.gas_sensitivity = 0.05
        play.gas_direction_share = lambda *a: 0.0
        return play

    def test_integration_rejects_long_wall_path_and_unavailable_gas(self):
        play = self.play()
        data = dict(player=[[625, 355, 655, 433]], wall=[])
        play.is_path_blocked = Mock(return_value=True)
        self.assertEqual(play.dodge_movement((100, 0), data, 10.17), (100, 0))
        self.assertTrue(
            any(
                call.kwargs.get("distance", 0) > 50
                for call in play.is_path_blocked.call_args_list
            )
        )
        play.gas_detection_ok = False
        play.is_path_blocked.reset_mock()
        self.assertEqual(play.dodge_movement((100, 0), data, 10.17), (100, 0))
        play.is_path_blocked.assert_not_called()

    def test_integration_does_not_dodge_into_gas(self):
        play = self.play()
        data = dict(player=[[625, 355, 655, 433]], wall=[])
        play.gas_mask[:305, :] = 255
        play.is_path_blocked = lambda *a, **k: False
        result = play.dodge_movement((100, 0), data, 10.17)
        self.assertTrue(play.projectile_dodge.active)
        self.assertGreater(result[1], 0)

    def test_integrated_stop_releases_movement_without_sending_touch(self):
        play=self.play();data=dict(player=[[625,355,655,433]],wall=[])
        center,_=play.get_player_hit_circle(data['player'][0])
        play.projectile_dodge.threats=[dict(x=center[0]+60,y=center[1]-70,vx=0.,vy=200.,r=5.)]
        play.is_path_blocked=lambda b,v,w,**kw:math.hypot(*v)>1e-6
        chosen=play.dodge_movement((100,0),data,10.17)
        self.assertEqual(chosen,(0.,0.));self.assertTrue(play.projectile_dodge.active)
        play.window_controller.move=Mock();play.window_controller.release_movement=Mock()
        play.do_movement(chosen)
        play.window_controller.release_movement.assert_called_once()
        play.window_controller.move.assert_not_called()

    def test_stop_candidate_is_rejected_on_current_gas_terrain(self):
        play=self.play();data=dict(player=[[625,355,655,433]],wall=[])
        center,_=play.get_player_hit_circle(data['player'][0])
        play.projectile_dodge.threats=[dict(x=center[0]+60,y=center[1]-70,vx=0.,vy=200.,r=5.)]
        play.is_path_blocked=lambda b,v,w,**kw:math.hypot(*v)>1e-6
        play.gas_mask[340:450,620:665]=255
        self.assertEqual(play.dodge_movement((100,0),data,10.17),(100,0))
        self.assertFalse(play.projectile_dodge.active)

    def test_confirmed_shot_never_overrides_gas_escape_or_disabled_setting(self):
        play = self.play()
        play.projectile_dodge.active = True
        self.assertEqual(
            play.dodge_movement((-100, 0), {}, 10.17, escaping=True), (-100, 0)
        )
        self.assertFalse(play.projectile_dodge.active)
        play.projectile_dodge_enabled = False
        self.assertEqual(play.dodge_movement((-100, 0), {}, 10.17), (-100, 0))

    def test_menu_stale_frame_and_respawn_release_input_and_discard_tracks(self):
        for state in ("stale", "lobby", "respawn"):
            play = self.play()
            play.window_controller.frame_is_fresh = lambda stamp: state != "stale"
            play.window_controller.release_all_inputs = Mock()
            play.clear_gas_state = Mock()
            play.persistent_data = {"time_since_holding_attack": 123}
            main = SimpleNamespace(
                thinking=None,
                current_frame_time=10.16,
                get_latest_state=lambda: "lobby" if state == "lobby" else "match",
            )
            with patch("battle_perception.respawning", return_value=True):
                play.main(self.frame(), "stu", main)
            play.window_controller.release_all_inputs.assert_called_once()
            self.assertFalse(play.projectile_dodge.tracks, state)
            self.assertFalse(play.projectile_dodge.threats, state)
            self.assertIsNone(play.projectile_dodge.stamp, state)

    def test_legacy_profile_can_disable_dodge_without_losing_other_settings(self):
        import tempfile
        from pathlib import Path
        import utils
        import device_profiles

        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            (home / "cfg").mkdir()
            (home / "cfg/bot_config.toml").write_text(
                'target_trophies = 987\ncurrent_playstyle = "survivor.xlambot"\n',
                encoding="utf8",
            )
            with patch.object(utils, "PROJECT_ROOT", home), patch.object(
                utils, "DATA_ROOT", home
            ):
                device_profiles.ensure_profile("dodge-qa")
                self.assertTrue(
                    device_profiles.read_settings("dodge-qa")["bot_config"][
                        "projectile_dodge"
                    ]
                )
                with self.assertRaises(ValueError):
                    device_profiles.update_settings(
                        "dodge-qa", "bot_config", {"projectile_dodge": "false"}
                    )
                device_profiles.update_settings(
                    "dodge-qa", "bot_config", {"projectile_dodge": False}
                )
                saved = device_profiles.read_settings("dodge-qa")["bot_config"]
                self.assertFalse(saved["projectile_dodge"])
                self.assertEqual(saved["target_trophies"], 987)


if __name__ == "__main__":
    unittest.main()
