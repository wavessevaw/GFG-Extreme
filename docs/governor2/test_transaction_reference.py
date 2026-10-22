import unittest
from transaction_reference import Coordinator, Phase

class ProtocolTest(unittest.TestCase):
    def setUp(self):
        self.c = Coordinator()
        self.args = dict(axis='tdp', value=14, observed=15, epoch=1, now=0,
                         timeout=20, fresh=True, healthy=True, owned=True)
    def test_one_owner_and_ack(self):
        cmd = self.c.propose(**self.args)
        self.assertIsNone(self.c.propose(**{**self.args, 'axis':'gpu'}))
        self.assertFalse(self.c.applied(cmd.token+1,14))
        self.assertTrue(self.c.applied(cmd.token,14))
        self.assertFalse(self.c.commit(epoch=1,now=10,complete_evidence=False,fresh=True,healthy=True,owned=True))
        self.assertTrue(self.c.commit(epoch=1,now=10,complete_evidence=True,fresh=True,healthy=True,owned=True))
    def test_timeout_restore_must_be_acknowledged(self):
        cmd=self.c.propose(**self.args)
        restore=self.c.observe(epoch=1,now=21,fresh=True,healthy=True)
        self.assertTrue(restore.restore)
        self.assertFalse(self.c.applied(cmd.token,14))
        self.assertFalse(self.c.restored(restore.token,14))
        self.assertIsNone(self.c.propose(**self.args))
        self.assertTrue(self.c.restored(restore.token,15))
    def test_user_override_never_restored_over(self):
        self.c.propose(**self.args)
        self.assertIsNone(self.c.observe(epoch=1,now=1,fresh=True,healthy=True,external_change=True))
        self.assertEqual(self.c.phase,Phase.USER)
        self.assertIsNone(self.c.propose(**self.args))
    def test_stale_or_new_context_cancels(self):
        for epoch,fresh in [(2,True),(1,False)]:
            c=Coordinator();cmd=c.propose(**self.args);c.applied(cmd.token,14)
            self.assertTrue(c.observe(epoch=epoch,now=1,fresh=fresh,healthy=True).restore)
    def test_failed_readback_retains_restore_intent(self):
        cmd=self.c.propose(**self.args)
        self.assertFalse(self.c.applied(cmd.token,13))
        self.assertEqual(self.c.phase,Phase.RESTORE)
    def test_unknown_data_cannot_start(self):
        for key in ['fresh','healthy','owned']:
            self.assertIsNone(self.c.propose(**{**self.args,key:False}))

if __name__=='__main__':unittest.main()
