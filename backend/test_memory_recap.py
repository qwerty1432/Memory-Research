"""Unit tests for memory phase recap filtering (no running server required)."""
import unittest
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import User, Session as StudySession
from app.memory_manager import create_memory_candidate, get_memory_recap


class MemoryRecapTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()

    def _add_user(self, condition_id: str):
        uid = uuid.uuid4()
        u = User(
            user_id=uid,
            username=f"u{uid.hex[:10]}",
            password_hash="x",
            condition_id=condition_id,
        )
        self.db.add(u)
        self.db.commit()
        return uid

    def _add_session(self, user_id):
        sid = uuid.uuid4()
        s = StudySession(session_id=sid, user_id=user_id)
        self.db.add(s)
        self.db.commit()
        return sid

    def test_create_memory_candidate_sets_phase(self):
        uid = self._add_user("SESSION_AUTO")
        sid = self._add_session(uid)
        m = create_memory_candidate(uid, sid, "hello", self.db, is_active=True, phase=2)
        self.assertEqual(m.phase, 2)

    def test_session_recap_exact_phase_only(self):
        uid = self._add_user("SESSION_AUTO")
        sid = self._add_session(uid)
        create_memory_candidate(uid, sid, "p1", self.db, is_active=True, phase=1)
        create_memory_candidate(uid, sid, "p2", self.db, is_active=True, phase=2)
        r1 = get_memory_recap(uid, sid, 1, "SESSION_AUTO", self.db)
        self.assertEqual([x.text for x in r1], ["p1"])
        r2 = get_memory_recap(uid, sid, 2, "SESSION_AUTO", self.db)
        self.assertEqual([x.text for x in r2], ["p2"])

    def test_session_recap_excludes_null_phase(self):
        uid = self._add_user("SESSION_AUTO")
        sid = self._add_session(uid)
        create_memory_candidate(uid, sid, "legacy", self.db, is_active=True, phase=None)
        r = get_memory_recap(uid, sid, 1, "SESSION_AUTO", self.db)
        self.assertEqual(r, [])

    def test_persistent_recap_cumulative(self):
        uid = self._add_user("PERSISTENT_AUTO")
        sid = self._add_session(uid)
        create_memory_candidate(uid, sid, "a", self.db, is_active=True, phase=1)
        create_memory_candidate(uid, sid, "b", self.db, is_active=True, phase=2)
        r1 = get_memory_recap(uid, sid, 1, "PERSISTENT_AUTO", self.db)
        self.assertEqual(sorted([x.text for x in r1]), ["a"])
        r2 = get_memory_recap(uid, sid, 2, "PERSISTENT_AUTO", self.db)
        self.assertEqual(sorted([x.text for x in r2]), ["a", "b"])

    def test_persistent_recap_includes_legacy_null_phase(self):
        uid = self._add_user("PERSISTENT_USER")
        sid = self._add_session(uid)
        create_memory_candidate(uid, sid, "old", self.db, is_active=True, phase=None)
        r = get_memory_recap(uid, sid, 1, "PERSISTENT_USER", self.db)
        self.assertEqual([x.text for x in r], ["old"])


if __name__ == "__main__":
    unittest.main()
