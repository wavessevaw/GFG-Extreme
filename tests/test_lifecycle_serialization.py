import threading
import unittest
import helpers
from gfg_plugin.service import Service


class LifecycleSerializationTest(unittest.TestCase):
    def test_stop_drains_tick_and_blocks_later_writes(self):
        service = Service.__new__(Service)
        service._lifecycle_lock = threading.RLock()
        service._stopped = False
        service.snapshot = {'stopped': True}
        entered, release, stop_requested = (threading.Event() for _ in range(3))
        writes = []
        def tick():
            entered.set()
            self.assertTrue(release.wait(2))
            writes.append('tick')
            return {}
        service._tick = tick
        service._stop = lambda: writes.append('restore')
        worker = threading.Thread(target=service.tick)
        worker.start()
        self.assertTrue(entered.wait(2))
        def stop():
            stop_requested.set()
            service.stop()
        stopper = threading.Thread(target=stop)
        stopper.start()
        self.assertTrue(stop_requested.wait(2))
        release.set()
        worker.join(2)
        stopper.join(2)
        self.assertFalse(worker.is_alive() or stopper.is_alive())
        self.assertEqual(writes, ['tick', 'restore'])
        self.assertEqual(service.tick(), service.snapshot)
        service.stop()
        self.assertEqual(writes, ['tick', 'restore'])
