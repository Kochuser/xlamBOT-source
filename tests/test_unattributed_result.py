import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from test_runtime_consistency import StageManager, TrophyObserver, MatchResult
from trophy_observer import ParsedGameResult, GameMode
from utils import config_scope


class UnattributedResultTests(unittest.TestCase):
    def test_confirmed_outcome_round_trips_without_brawler_measurements(self):
        with tempfile.TemporaryDirectory() as folder, config_scope(folder):
            observer = TrophyObserver()
            observer.current_trophies = 500
            observer.current_wins = 7
            observer.win_streak = 3
            observer.send_results_to_api = Mock()
            outcome = ParsedGameResult(GameMode.TRIO_SHOWDOWN, MatchResult.VICTORY, 0)
            observer.record_unattributed_result(outcome, {'name': 'classic', 'gamemodes': ['trio_showdown']})
            row = observer.match_history[-1]
            self.assertEqual(row['result'], 'victory')
            self.assertEqual(row['brawler_name'], '')
            self.assertEqual(row['trophy_source'], 'unknown')
            for key in ('current_trophies', 'trophy_delta', 'new_winstreak'):
                self.assertIsNone(row[key])
            self.assertEqual((observer.current_trophies, observer.current_wins, observer.win_streak), (500, 7, 3))
            self.assertEqual(observer.match_counter, 1)
            restored = TrophyObserver()
            self.assertEqual(restored.match_history[-1]['result'], 'victory')
            self.assertEqual(restored.match_history[-1]['brawler_name'], '')
            self.assertEqual(restored.match_history[-1]['trophy_delta'], '')

    def test_fast_unknown_brawler_results_record_once_and_rearm_for_next_battle(self):
        manager = StageManager.__new__(StageManager)
        manager.window_controller = Mock()
        manager.runtime_control = None
        manager.play_again_on_win = False
        manager.time_since_last_stat_change = time.time()
        manager.playstyle_info = {}
        manager.current_brawler = lambda: None
        manager.brawlers_pick_data = [{'brawler': 'shelly', 'type': 'trophies', 'trophies': 400}]
        manager.Trophy_observer = Mock()
        manager.Trophy_observer.parse_game_result.return_value = SimpleNamespace(result=MatchResult.DEFEAT)
        manager._sleep_interruptible = lambda *args: False
        def finish():
            with patch('stage_manager.get_state', side_effect=['end_defeat', 'lobby']), patch('stage_manager.is_underdog', return_value=False), patch('stage_manager.save_brawler_data') as save:
                manager.end_game()
            save.assert_not_called()
        finish(); finish()
        self.assertEqual(manager.Trophy_observer.record_unattributed_result.call_count, 1)
        manager.observe_match(); manager.observe_match(); finish()
        self.assertEqual(manager.Trophy_observer.record_unattributed_result.call_count, 2)
        manager.Trophy_observer.add_trophies.assert_not_called()
        manager.Trophy_observer.add_win.assert_not_called()
        self.assertEqual(manager.brawlers_pick_data[0]['trophies'], 400)

    def test_unmatched_known_name_does_not_change_configured_brawler_statistics(self):
        manager = StageManager.__new__(StageManager)
        manager.window_controller = Mock()
        manager.runtime_control = None
        manager.play_again_on_win = False
        manager.playstyle_info = {}
        manager.current_brawler = lambda: 'gus'
        manager.brawlers_pick_data = [{'brawler': 'shelly', 'type': 'trophies', 'trophies': 400}]
        manager.Trophy_observer = Mock()
        manager.Trophy_observer.parse_game_result.return_value = SimpleNamespace(result=MatchResult.DEFEAT)
        manager._sleep_interruptible = lambda *args: False
        with patch('stage_manager.get_state', side_effect=['end_defeat', 'lobby']), patch('stage_manager.is_underdog', return_value=False), patch('stage_manager.save_brawler_data') as save:
            manager.end_game()
        manager.Trophy_observer.record_unattributed_result.assert_called_once()
        manager.Trophy_observer.add_trophies.assert_not_called()
        save.assert_not_called()
