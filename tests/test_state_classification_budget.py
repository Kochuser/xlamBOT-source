import threading,time,unittest
from unittest.mock import patch,Mock
import numpy as np
import test_runtime_consistency as runtime_fixture
StaleFrameError=runtime_fixture.StaleFrameError


class ClassificationBudgetTests(unittest.TestCase):
    def bot(self):
        bot=runtime_fixture.RuntimeConsistencyTests().bot()
        bot._state_classification_lock=threading.Lock()
        bot.window_controller.frame_is_fresh=lambda *args:True
        return bot

    def test_busy_background_defers_owner_without_wait_or_reclassification(self):
        bot=self.bot();frame=np.zeros((4,4,3),np.uint8)
        with bot._state_classification_lock:
            with patch('state_finder.get_action_state') as recognize:
                with self.assertRaises(StaleFrameError):bot.observe_action_frame(frame,time.time())
        recognize.assert_not_called()
        bot.window_controller.release_all_inputs.assert_not_called()

    def test_busy_owner_skips_background_and_devices_remain_independent(self):
        first,second=self.bot(),self.bot();frame=np.zeros((4,4,3),np.uint8)
        recognize=Mock(return_value='lobby')
        with first._state_classification_lock,patch.dict(runtime_fixture.BotInstance._classify_frame.__globals__,{'get_state':recognize}):
            self.assertIsNone(first._classify_frame(frame,time.time()))
            self.assertEqual(second._classify_frame(frame,time.time()),'lobby')
        recognize.assert_called_once()
        self.assertEqual(first.observations.snapshot().frame_time,0)

    def test_real_racing_classifiers_never_overlap_on_one_device(self):
        bot=self.bot();frame=np.zeros((4,4,3),np.uint8);entered=threading.Event();release=threading.Event()
        def recognize(frame):
            entered.set();self.assertTrue(release.wait(2));return 'lobby'
        with patch.dict(runtime_fixture.BotInstance._classify_frame.__globals__,{'get_state':recognize}),patch('state_finder.get_action_state',return_value='lobby') as action:
            worker=threading.Thread(target=bot._classify_frame,args=(frame,time.time()))
            worker.start();self.assertTrue(entered.wait(2))
            with self.assertRaises(StaleFrameError):bot.observe_action_frame(frame,time.time())
            action.assert_not_called();release.set();worker.join(2);self.assertFalse(worker.is_alive())
            self.assertEqual(bot.observe_action_frame(frame,time.time()).state,'lobby')
        action.assert_called_once()

    def test_action_keeps_capture_time_when_newer_same_screen_exists(self):
        bot=self.bot();stamp=time.time();frame=np.zeros((4,4,3),np.uint8)
        def recognize(frame):bot.set_latest_state('lobby',stamp+.1);return 'lobby'
        with patch('state_finder.get_action_state',side_effect=recognize):ticket=bot.observe_action_frame(frame,stamp)
        self.assertEqual(ticket.frame_time,stamp)
        self.assertEqual(bot.observations.snapshot().frame_time,stamp+.1)
        self.assertEqual(ticket.epoch,bot.observations.snapshot().epoch)

    def test_recognition_expiry_rejects_action_and_releases_classification_lock(self):
        bot=self.bot();fresh=[True];bot.window_controller.frame_is_fresh=lambda *args:fresh[0]
        def recognize(frame):fresh[0]=False;return 'lobby'
        with patch('state_finder.get_action_state',side_effect=recognize):
            with self.assertRaises(StaleFrameError):bot.observe_action_frame(np.zeros((4,4,3),np.uint8),time.time())
        self.assertEqual(bot.observations.snapshot().frame_time,0)
        self.assertTrue(bot._state_classification_lock.acquire(False));bot._state_classification_lock.release()

    def test_old_decision_cannot_borrow_age_from_a_newer_same_state(self):
        controller=runtime_fixture.RuntimeConsistencyTests().controller();old=time.time()-2
        controller.observations.publish('lobby',time.time())
        from runtime_observation import Observation
        ticket=Observation('lobby',old,controller.observations.snapshot().epoch)
        controller.frame_is_fresh=lambda stamp=None:stamp is None or time.time()-stamp<.75
        with controller.decision_scope(ticket,allow_menu_transitions=True):
            with self.assertRaises(StaleFrameError):controller._check_decision()

    def test_background_retains_full_classifier_instead_of_action_classifier(self):
        bot=self.bot();frame=np.zeros((4,4,3),np.uint8)
        full=Mock(return_value='unknown')
        with patch.dict(runtime_fixture.BotInstance._classify_frame.__globals__,{'get_state':full}),patch('state_finder.get_action_state') as action:
            self.assertEqual(bot._classify_frame(frame,time.time()),'unknown')
        full.assert_called_once_with(frame);action.assert_not_called()

    def test_menu_owner_retains_priority_between_consecutive_screenshots(self):
        bot=self.bot();frame=np.zeros((4,4,3),np.uint8);owner=threading.get_ident()
        bot.window_controller.input_owner=owner
        bot.window_controller._decision=(owner,bot.observations.snapshot(),True)
        full=Mock(return_value='lobby')
        with patch.dict(runtime_fixture.BotInstance._classify_frame.__globals__,{'get_state':full}),patch('state_finder.get_action_state',side_effect=['brawler_selection','brawler_detail']) as action:
            first=bot.observe_action_frame(frame,time.time())
            self.assertIsNone(bot._classify_frame(frame,time.time()))
            second=bot.observe_action_frame(frame,time.time())
        self.assertEqual((first.state,second.state),('brawler_selection','brawler_detail'))
        self.assertGreater(second.epoch,first.epoch)
        self.assertEqual(action.call_count,2);full.assert_not_called()

    def test_background_resumes_after_menu_scope_and_remains_active_in_battle(self):
        bot=self.bot();frame=np.zeros((4,4,3),np.uint8);owner=threading.get_ident()
        bot.window_controller.input_owner=owner
        full=Mock(return_value='match')
        with patch.dict(runtime_fixture.BotInstance._classify_frame.__globals__,{'get_state':full}):
            bot.window_controller._decision=(owner,bot.observations.snapshot(),False)
            self.assertEqual(bot._classify_frame(frame,time.time()),'match')
            bot.window_controller._decision=None
            self.assertEqual(bot._classify_frame(frame,time.time()),'match')
        self.assertEqual(full.call_count,2)

    def test_non_owner_scope_cannot_suppress_background_observations(self):
        bot=self.bot();frame=np.zeros((4,4,3),np.uint8);owner=threading.get_ident()
        bot.window_controller.input_owner=owner
        bot.window_controller._decision=(owner+1,bot.observations.snapshot(),True)
        full=Mock(return_value='lobby')
        with patch.dict(runtime_fixture.BotInstance._classify_frame.__globals__,{'get_state':full}):
            self.assertEqual(bot._classify_frame(frame,time.time()),'lobby')
        full.assert_called_once()
