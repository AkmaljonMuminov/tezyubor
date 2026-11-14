"""Hamyon store shartnomasi: xotira va PostgreSQL BIR XIL natija berishi kerak. Pul harakati atomikligi va parallel
holatlar shu yerda tekshiriladi (PostgreSQL qismi CI'da, TEST_DATABASE_URL bilan)."""
import os
import threading
import unittest
import uuid

try:
    import psycopg  # noqa: F401
    import psycopg_pool  # noqa: F401

    from app.db import Database
    from app.modules.auth.pg_stores import PgUserStore
    from app.modules.wallet.pg_store import PgWalletStore

    HAVE = True
except ImportError:  # pragma: no cover
    HAVE = False

from app.errors import (
    CardUnavailable,
    DailyLimitExceeded,
    InsufficientFunds,
    TransferExpired,
    TransferNotFound,
    TransferNotPending,
)
from app.modules.auth.stores import MemoryUserStore
from app.modules.wallet.models import Card, Transfer
from app.modules.wallet.store import MemoryWalletStore

URL = os.environ.get("TEST_DATABASE_URL", "")
DAY = 86_400.0


def mk_card(user_id, n, balance=0):
    return Card(
        id=str(uuid.uuid4()), user_id=user_id, pan_index=f"idx-{n}-{uuid.uuid4().hex[:8]}", bin6="860012",
        last4=f"{n:04d}", brand="uzcard", holder_name="ALI VALI", exp_month=12, exp_year=2099, balance=balance,
        is_default=False, status="active", created_at=float(n),
    )


def mk_transfer(src: Card, dst: Card, amount=100_000, fee=0, key=None, created=100.0, expires=10_000.0):
    return Transfer(
        id=str(uuid.uuid4()), user_id=src.user_id, to_user_id=dst.user_id, from_card_id=src.id, to_card_id=dst.id,
        amount=amount, fee=fee, status="pending", idempotency_key=key or uuid.uuid4().hex, request_hash="h",
        receiver_last4=dst.last4, receiver_name_masked="A* V*", created_at=created, expires_at=expires,
    )


class WalletStoreContract:
    def make(self):  # -> (wallet_store, user_store)
        raise NotImplementedError

    def setUp(self):
        self.w, self.users = self.make()
        self.u1 = self.users.create("998901111111").id
        self.u2 = self.users.create("998902222222").id

    def funded(self, balance=1_000_000):
        a = self.w.add_card(mk_card(self.u1, 1), balance, 1.0)
        b = self.w.add_card(mk_card(self.u2, 2), balance, 1.0)
        return a, b

    def exe(self, t, now=200.0, user=None, limit=10**12):
        return self.w.execute_transfer(t.id, user or t.user_id, now, now - DAY, limit)

    # --- kartalar ---
    def test_card_add_list_default_and_ledger_bonus(self):
        c1 = self.w.add_card(mk_card(self.u1, 1), 5_000, 1.0)
        c2 = self.w.add_card(mk_card(self.u1, 2), 5_000, 2.0)
        self.assertEqual((c1.balance, c1.is_default, c2.is_default), (5_000, True, False))
        self.assertEqual(self.w.ledger_sum(c1.id), 5_000)
        self.assertEqual([c.id for c in self.w.list_cards(self.u1)], [c1.id, c2.id])
        self.assertTrue(self.w.set_default(c2.id, self.u1))
        self.assertEqual([c.id for c in self.w.list_cards(self.u1)], [c2.id, c1.id])
        self.assertFalse(self.w.set_default(c1.id, self.u2))  # begonaniki
        self.assertEqual(self.w.get_card(c1.id).holder_name, "ALI VALI")
        self.assertIsNone(self.w.get_card("not-a-uuid"))

    def test_duplicate_index_rejected_and_reactivation_without_bonus(self):
        c = mk_card(self.u1, 1)
        saved = self.w.add_card(c, 5_000, 1.0)
        dup = mk_card(self.u2, 9)
        dup.pan_index = c.pan_index
        with self.assertRaises(CardUnavailable):
            self.w.add_card(dup, 5_000, 1.0)
        self.assertTrue(self.w.soft_delete_card(saved.id, self.u1))
        self.assertFalse(self.w.soft_delete_card(saved.id, self.u1))
        self.assertIsNone(self.w.find_active_by_index(c.pan_index))
        with self.assertRaises(CardUnavailable):
            self.w.add_card(dup, 5_000, 1.0)  # boshqa odam o'chirilgan kartani ola olmaydi
        again = mk_card(self.u1, 1)
        again.pan_index = c.pan_index
        back = self.w.add_card(again, 5_000, 5.0)
        self.assertEqual((back.id, back.balance, back.status), (saved.id, 5_000, "active"))
        self.assertEqual(self.w.ledger_sum(saved.id), 5_000)

    def test_delete_default_promotes_next(self):
        c1 = self.w.add_card(mk_card(self.u1, 1), 0, 1.0)
        c2 = self.w.add_card(mk_card(self.u1, 2), 0, 2.0)
        self.assertTrue(self.w.soft_delete_card(c1.id, self.u1))
        left = self.w.list_cards(self.u1)
        self.assertEqual([(c.id, c.is_default) for c in left], [(c2.id, True)])
        self.assertFalse(self.w.soft_delete_card(c2.id, self.u2))

    def test_lookup_window(self):
        for _ in range(3):
            self.assertTrue(self.w.allow_lookup(self.u1, 100.0, 60, 3))
        self.assertFalse(self.w.allow_lookup(self.u1, 120.0, 60, 3))
        self.assertTrue(self.w.allow_lookup(self.u2, 120.0, 60, 3))  # boshqa foydalanuvchi mustaqil
        self.assertTrue(self.w.allow_lookup(self.u1, 161.0, 60, 3))

    # --- o'tkazmalar ---
    def test_create_is_idempotent_per_user_and_key(self):
        a, b = self.funded()
        t1 = mk_transfer(a, b, key="same-key-123")
        t2 = mk_transfer(a, b, key="same-key-123")
        first = self.w.create_transfer(t1)
        second = self.w.create_transfer(t2)
        self.assertEqual(first.id, second.id)
        self.assertEqual(self.w.get_transfer_by_key(self.u1, "same-key-123").id, first.id)
        self.assertIsNone(self.w.get_transfer_by_key(self.u2, "same-key-123"))
        self.assertIsNone(self.w.get_transfer("not-a-uuid"))

    def test_execute_moves_money_and_writes_ledger(self):
        a, b = self.funded()
        t = self.w.create_transfer(mk_transfer(a, b, amount=300_000, fee=3_000))
        done = self.exe(t)
        self.assertEqual((done.status, done.completed_at), ("completed", 200.0))
        self.assertTrue(done.receipt_no.startswith("TZ-"))
        self.assertEqual(self.w.get_card(a.id).balance, 1_000_000 - 303_000)
        self.assertEqual(self.w.get_card(b.id).balance, 1_300_000)
        self.assertEqual(self.w.ledger_sum(a.id), 697_000)
        self.assertEqual(self.w.ledger_sum(b.id), 1_300_000)
        self.assertEqual(self.exe(t, now=300.0).receipt_no, done.receipt_no)  # qayta chaqirish — o'sha natija, qayta yechilmaydi
        self.assertEqual(self.w.get_card(a.id).balance, 697_000)

    def test_execute_only_by_owner(self):
        a, b = self.funded()
        t = self.w.create_transfer(mk_transfer(a, b))
        with self.assertRaises(TransferNotFound):
            self.exe(t, user=self.u2)
        with self.assertRaises(TransferNotFound):
            self.w.execute_transfer("not-a-uuid", self.u1, 1.0, 0.0, 10**9)

    def test_insufficient_marks_failed_and_persists(self):
        a, b = self.funded(balance=100_000)
        t = self.w.create_transfer(mk_transfer(a, b, amount=100_000, fee=1))
        with self.assertRaises(InsufficientFunds):
            self.exe(t)
        self.assertEqual(self.w.get_transfer(t.id).status, "failed")  # xato ko'tarilsa ham holat saqlangan
        self.assertEqual(self.w.get_transfer(t.id).failure_reason, "insufficient_funds")
        self.assertEqual(self.w.get_card(a.id).balance, 100_000)
        with self.assertRaises(TransferNotPending):
            self.exe(t)

    def test_expired_marks_expired_and_persists(self):
        a, b = self.funded()
        t = self.w.create_transfer(mk_transfer(a, b, expires=150.0))
        with self.assertRaises(TransferExpired):
            self.exe(t, now=200.0)
        self.assertEqual(self.w.get_transfer(t.id).status, "expired")
        self.assertEqual(self.w.get_card(a.id).balance, 1_000_000)

    def test_deleted_card_fails_transfer(self):
        a, b = self.funded()
        t = self.w.create_transfer(mk_transfer(a, b))
        self.w.soft_delete_card(b.id, self.u2)
        with self.assertRaises(CardUnavailable):
            self.exe(t)
        self.assertEqual(self.w.get_transfer(t.id).status, "failed")
        self.assertEqual(self.w.get_card(a.id).balance, 1_000_000)

    def test_daily_limit_keeps_pending_and_window_slides(self):
        a, b = self.funded(balance=2_000_000)
        far = 10**12  # tasdiqlash muddati cheksiz — bu testda faqat kunlik limit tekshiriladi
        t1 = self.w.create_transfer(mk_transfer(a, b, amount=600_000, expires=far))
        t2 = self.w.create_transfer(mk_transfer(a, b, amount=600_000, expires=far))
        self.exe(t1, limit=1_000_000)
        with self.assertRaises(DailyLimitExceeded):
            self.exe(t2, limit=1_000_000)
        self.assertEqual(self.w.get_transfer(t2.id).status, "pending")  # limit oshsa holat o'zgarmaydi
        self.assertEqual(self.exe(t2, now=200.0 + DAY + 1, limit=1_000_000).status, "completed")  # sutka o'tdi

    def test_cancel(self):
        a, b = self.funded()
        t = self.w.create_transfer(mk_transfer(a, b))
        self.assertEqual(self.w.cancel_transfer(t.id, self.u1).status, "cancelled")
        self.assertEqual(self.w.cancel_transfer(t.id, self.u1).status, "cancelled")
        with self.assertRaises(TransferNotPending):
            self.exe(t)
        with self.assertRaises(TransferNotFound):
            self.w.cancel_transfer(t.id, self.u2)

    # --- parallel ---
    def test_parallel_execute_same_transfer_debits_once(self):
        a, b = self.funded()
        t = self.w.create_transfer(mk_transfer(a, b, amount=300_000, fee=3_000))
        out, lock = [], threading.Lock()

        def run():
            try:
                r = self.exe(t)
                res = r.status
            except Exception as ex:  # noqa: BLE001
                res = type(ex).__name__
            with lock:
                out.append(res)

        ts = [threading.Thread(target=run) for _ in range(8)]
        [x.start() for x in ts]
        [x.join() for x in ts]
        self.assertEqual(out.count("completed"), 8)  # takroriy chaqiriq o'sha natijani qaytaradi
        self.assertEqual(self.w.get_card(a.id).balance, 697_000)
        self.assertEqual(self.w.get_card(b.id).balance, 1_300_000)

    def test_parallel_transfers_cannot_overdraw(self):
        a, b = self.funded(balance=1_000_000)
        ts_ = [self.w.create_transfer(mk_transfer(a, b, amount=300_000)) for _ in range(6)]
        out, lock = [], threading.Lock()

        def run(t):
            try:
                self.exe(t)
                res = "ok"
            except InsufficientFunds:
                res = "insufficient"
            with lock:
                out.append(res)

        ths = [threading.Thread(target=run, args=(t,)) for t in ts_]
        [x.start() for x in ths]
        [x.join() for x in ths]
        self.assertEqual(out.count("ok"), 3)
        self.assertEqual(out.count("insufficient"), 3)
        self.assertEqual(self.w.get_card(a.id).balance, 100_000)
        self.assertEqual(self.w.ledger_sum(a.id), 100_000)
        self.assertEqual(self.w.get_card(b.id).balance, 1_900_000)

    def test_parallel_daily_limit_across_different_source_cards(self):
        """Ikki turli kartadan parallel tasdiqlash ham kunlik limitdan oshib keta olmaydi."""
        a1 = self.w.add_card(mk_card(self.u1, 3), 1_000_000, 1.0)
        a2 = self.w.add_card(mk_card(self.u1, 4), 1_000_000, 1.0)
        b = self.w.add_card(mk_card(self.u2, 5), 0, 1.0)
        t1 = self.w.create_transfer(mk_transfer(a1, b, amount=600_000))
        t2 = self.w.create_transfer(mk_transfer(a2, b, amount=600_000))
        out, lock = [], threading.Lock()

        def run(t):
            try:
                self.exe(t, limit=1_000_000)
                res = "ok"
            except DailyLimitExceeded:
                res = "limit"
            with lock:
                out.append(res)

        ths = [threading.Thread(target=run, args=(t,)) for t in (t1, t2)]
        [x.start() for x in ths]
        [x.join() for x in ths]
        self.assertEqual(sorted(out), ["limit", "ok"])

    # --- tarix ---
    def test_history_keyset_pagination_with_equal_timestamps(self):
        a, b = self.funded()
        made = [self.w.create_transfer(mk_transfer(a, b, created=500.0)) for _ in range(5)]
        made.append(self.w.create_transfer(mk_transfer(a, b, created=900.0)))
        seen, before = [], None
        while True:
            rows = self.w.list_history(self.u1, 2, before, None, None)
            if not rows:
                break
            seen += [t.id for t in rows]
            before = (rows[-1].created_at, rows[-1].id)
        self.assertEqual(len(seen), 6)
        self.assertEqual(len(set(seen)), 6)
        self.assertEqual(seen[0], made[-1].id)  # eng yangisi birinchi
        self.assertEqual(set(seen), {t.id for t in made})

    def test_history_receiver_sees_completed_only(self):
        a, b = self.funded()
        t1 = self.w.create_transfer(mk_transfer(a, b, created=10.0))
        self.w.create_transfer(mk_transfer(a, b, created=20.0))  # pending
        self.exe(t1)
        got = self.w.list_history(self.u2, 10, None, None, None)
        self.assertEqual([t.id for t in got], [t1.id])
        self.assertEqual(self.w.list_history(self.u2, 10, None, None, "sent"), [])
        self.assertEqual(len(self.w.list_history(self.u1, 10, None, "pending", "sent")), 1)
        self.assertEqual(self.w.list_history(self.u1, 10, None, None, "received"), [])


class MemoryWalletContract(WalletStoreContract, unittest.TestCase):
    def make(self):
        return MemoryWalletStore(), MemoryUserStore()


@unittest.skipUnless(URL and HAVE, "TEST_DATABASE_URL va psycopg kerak")
class PostgresWalletContract(WalletStoreContract, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database(URL, max_size=10)
        cls.db.migrate()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def make(self):
        with self.db.connection() as c:
            c.execute("TRUNCATE users CASCADE")
        return PgWalletStore(self.db), PgUserStore(self.db)

    def test_db_rejects_negative_balance_directly(self):
        """Dastur xatosi bo'lsa ham baza manfiy balansga yo'l qo'ymaydi (CHECK)."""
        a, _ = self.funded(balance=100)
        with self.assertRaises(Exception):
            with self.db.connection() as c:
                c.execute("UPDATE cards SET balance = balance - 101 WHERE id = %s", (uuid.UUID(a.id),))
        self.assertEqual(self.w.get_card(a.id).balance, 100)


if __name__ == "__main__":
    unittest.main()
