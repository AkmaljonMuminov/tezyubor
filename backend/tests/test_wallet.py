"""Hamyon (sandbox) xizmati: kartalar, o'tkazma, idempotentlik, PIN tasdiq, limitlar, tarix, xavfsizlik regressiyasi."""
import threading
import unittest

from app.config import Settings
from app.errors import (
    AmountOutOfRange,
    CardInvalid,
    CardLimitReached,
    CardNotFound,
    CardUnavailable,
    ConfigError,
    DailyLimitExceeded,
    IdempotencyConflict,
    IdempotencyKeyInvalid,
    InsufficientFunds,
    PinInvalid,
    PinLocked,
    ReceiverNotFound,
    SameCard,
    TokenInvalid,
    TransferExpired,
    TransferNotFound,
    TransferNotPending,
    ValidationError,
    WalletRateLimited,
)
from tests.helpers import SECRET_A, SECRET_B
from tests.wallet_helpers import KEY, PAN_A, PAN_B, PAN_C, PIN, Env, make_pan

START = 100_000_000  # standart sandbox boshlang'ich balans (1 000 000 so'm)


class CardTests(unittest.TestCase):
    def setUp(self):
        self.e = Env()

    def test_add_card_returns_masked_view_with_sandbox_balance(self):
        c = self.e.card(self.e.a, PAN_A)
        self.assertEqual(c["last4"], PAN_A[-4:])
        self.assertEqual(c["balance_tiyin"], START)
        self.assertTrue(c["is_default"])
        self.assertTrue(c["sandbox"])
        self.assertEqual(c["brand"], "uzcard")
        self.assertNotIn(PAN_A, repr(c))
        self.assertNotIn(PAN_A[6:12], repr(c))  # o'rta raqamlar ko'rinmaydi

    def test_second_card_is_not_default_and_set_default_switches(self):
        a1 = self.e.card(self.e.a, PAN_A)
        a2 = self.e.card(self.e.a, PAN_C)
        self.assertFalse(a2["is_default"])
        self.e.wallet.set_default(self.e.a, a2["id"])
        cards = self.e.wallet.list_cards(self.e.a)
        self.assertEqual([c["id"] for c in cards if c["is_default"]], [a2["id"]])
        self.assertEqual(cards[0]["id"], a2["id"])  # standart karta birinchi
        self.assertIn(a1["id"], [c["id"] for c in cards])

    def test_invalid_cards_rejected(self):
        w, a = self.e.wallet, self.e.a
        self.e.clock.t = 1_800_000_000.0  # 2027-01: 2020 muddati o'tgan hisoblanadi
        bad_luhn = PAN_A[:-1] + str((int(PAN_A[-1]) + 1) % 10)
        for pan, m, y, name in [
            (bad_luhn, 12, 2099, "ALI VALI"),
            ("1234", 12, 2099, "ALI VALI"),
            (PAN_A, 13, 2099, "ALI VALI"),
            (PAN_A, 1, 2020, "ALI VALI"),   # muddati o'tgan
            (PAN_A, 12, 2099, "1234"),
            (PAN_A, 12, 2099, ""),
            ("abcd efgh ijkl mnop", 12, 2099, "ALI VALI"),
        ]:
            with self.assertRaises(CardInvalid, msg=(pan, m, y, name)):
                w.add_card(a, pan, m, y, name)

    def test_formatted_pan_accepted_and_duplicate_rejected_for_everyone(self):
        spaced = " ".join(PAN_A[i : i + 4] for i in range(0, 16, 4))
        self.e.wallet.add_card(self.e.a, spaced, 12, 99, "ali vali")
        with self.assertRaises(CardUnavailable):
            self.e.card(self.e.a, PAN_A)
        with self.assertRaises(CardUnavailable):
            self.e.card(self.e.b, PAN_A)  # boshqa foydalanuvchi ham qo'sha olmaydi

    def test_card_limit(self):
        for i in range(5):
            self.e.card(self.e.a, make_pan("8600", f"0000000{i}001"))
        with self.assertRaises(CardLimitReached):
            self.e.card(self.e.a, make_pan("8600", "55555555551"))

    def test_delete_card_reassigns_default_and_hides_foreign(self):
        a1 = self.e.card(self.e.a, PAN_A)
        a2 = self.e.card(self.e.a, PAN_C)
        self.e.wallet.delete_card(self.e.a, a1["id"])
        cards = self.e.wallet.list_cards(self.e.a)
        self.assertEqual([c["id"] for c in cards], [a2["id"]])
        self.assertTrue(cards[0]["is_default"])
        with self.assertRaises(CardNotFound):
            self.e.wallet.delete_card(self.e.b, a2["id"])  # boshqaning kartasi
        with self.assertRaises(CardNotFound):
            self.e.wallet.delete_card(self.e.a, a1["id"])  # allaqachon o'chirilgan
        with self.assertRaises(CardNotFound):
            self.e.wallet.set_default(self.e.b, a2["id"])

    def test_readding_deleted_card_gives_no_second_bonus_and_others_cannot_take_it(self):
        c = self.e.card(self.e.a, PAN_A)
        self.e.wallet.delete_card(self.e.a, c["id"])
        with self.assertRaises(CardUnavailable):
            self.e.card(self.e.b, PAN_A)
        again = self.e.card(self.e.a, PAN_A)
        self.assertEqual(again["id"], c["id"])
        self.assertEqual(again["balance_tiyin"], START)  # sovg'a ikki marta berilmaydi

    def test_lookup_throttle(self):
        self.e.card(self.e.b, PAN_B)
        for _ in range(9):
            with self.assertRaises(ReceiverNotFound):
                self.e.wallet.lookup_receiver(self.e.a, make_pan("8600", "77777777777"))
        # 10-urinish (add_card ham hisobga kirgan emas, bu a uchun): hali ruxsat, 11-si — limit
        self.e.wallet.lookup_receiver(self.e.a, PAN_B)
        with self.assertRaises(WalletRateLimited):
            self.e.wallet.lookup_receiver(self.e.a, PAN_B)
        self.e.clock.advance(61)
        self.assertIn("name_masked", self.e.wallet.lookup_receiver(self.e.a, PAN_B))

    def test_lookup_masks_receiver(self):
        self.e.card(self.e.b, PAN_B, "SARDOR TOSHMATOV")
        r = self.e.wallet.lookup_receiver(self.e.a, PAN_B)
        self.assertEqual(r["name_masked"], "S***** T******")
        self.assertNotIn(PAN_B, repr(r))
        with self.assertRaises(CardInvalid):
            self.e.wallet.lookup_receiver(self.e.a, "1234")


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.e = Env(transfer_fee_bps=100, transfer_fee_min_tiyin=5_000)  # 1%, kamida 50 so'm: TEST qiymatlar
        self.src = self.e.card(self.e.a, PAN_A)
        self.dst = self.e.card(self.e.b, PAN_B)

    def quote(self, key="key-00000001", amount=1_000_000, uid=None, frm=None, pan=PAN_B):
        return self.e.wallet.create_transfer(uid or self.e.a, key, frm or self.src["id"], pan, amount)

    def balances(self):
        s = {c["id"]: c["balance_tiyin"] for c in self.e.wallet.list_cards(self.e.a) + self.e.wallet.list_cards(self.e.b)}
        return s[self.src["id"]], s[self.dst["id"]]

    def test_quote_has_server_computed_fee_and_moves_no_money(self):
        q = self.quote(amount=1_000_000)
        self.assertEqual((q["status"], q["amount_tiyin"], q["fee_tiyin"], q["total_tiyin"]), ("pending", 1_000_000, 10_000, 1_010_000))
        self.assertIsNone(q["receipt"])
        self.assertEqual(self.balances(), (START, START))

    def test_min_fee_applies(self):
        q = self.quote(key="key-00000002", amount=200_000)
        self.assertEqual(q["fee_tiyin"], 5_000)  # 1% = 2000 < min 5000

    def test_confirm_moves_money_once_and_returns_receipt(self):
        q = self.quote()
        done = self.e.wallet.confirm_transfer(self.e.a, q["id"], PIN)
        self.assertEqual(done["status"], "completed")
        self.assertTrue(done["receipt"]["number"].startswith("TZ-"))
        self.assertEqual(self.balances(), (START - 1_010_000, START + 1_000_000))
        again = self.e.wallet.confirm_transfer(self.e.a, q["id"], "0000")  # takroriy tasdiq: PIN so'ralmaydi, qayta yechilmaydi
        self.assertEqual(again["receipt"]["number"], done["receipt"]["number"])
        self.assertEqual(self.balances(), (START - 1_010_000, START + 1_000_000))

    def test_ledger_matches_balances(self):
        q = self.quote()
        self.e.wallet.confirm_transfer(self.e.a, q["id"], PIN)
        self.assertEqual(self.e.store.ledger_sum(self.src["id"]), START - 1_010_000)
        self.assertEqual(self.e.store.ledger_sum(self.dst["id"]), START + 1_000_000)

    def test_wrong_pin_moves_nothing_and_lock_blocks_even_correct_pin(self):
        q = self.quote()
        with self.assertRaises(PinInvalid):
            self.e.wallet.confirm_transfer(self.e.a, q["id"], "9999")
        self.assertEqual(self.balances(), (START, START))
        for _ in range(4):
            try:
                self.e.wallet.confirm_transfer(self.e.a, q["id"], "9999")
            except (PinInvalid, PinLocked):
                pass
        with self.assertRaises(PinLocked):
            self.e.wallet.confirm_transfer(self.e.a, q["id"], PIN)
        self.assertEqual(self.balances(), (START, START))

    def test_pin_required(self):
        q = self.quote()
        for bad in (None, "", 1234):
            with self.assertRaises(ValidationError):
                self.e.wallet.confirm_transfer(self.e.a, q["id"], bad)

    def test_idempotent_create_same_body_same_transfer(self):
        a = self.quote()
        b = self.quote()
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(len(self.e.wallet.history(self.e.a)[0]), 1)

    def test_idempotency_key_reuse_with_other_body_conflicts(self):
        self.quote(amount=1_000_000)
        with self.assertRaises(IdempotencyConflict):
            self.quote(amount=2_000_000)

    def test_idempotency_key_required_and_validated(self):
        for key in (None, "", "short", "has space 12345", "x" * 65, "ключ-123456"):
            with self.assertRaises(IdempotencyKeyInvalid, msg=key):
                self.quote(key=key)

    def test_idempotency_key_is_per_user(self):
        self.quote(key="shared-key-1")
        other = self.e.card(self.e.b, PAN_C)
        q = self.e.wallet.create_transfer(self.e.b, "shared-key-1", other["id"], PAN_A, 1_000_000)
        self.assertEqual(q["direction"], "sent")  # B uchun alohida o'tkazma

    def test_amount_validation(self):
        for amt in (0, -5, 99_999, 500_000_001):
            with self.assertRaises(AmountOutOfRange, msg=amt):
                self.quote(amount=amt)
        for amt in (1.5, "100000", None, True):
            with self.assertRaises(ValidationError, msg=amt):
                self.quote(amount=amt)

    def test_cannot_use_foreign_or_unknown_source_card(self):
        with self.assertRaises(CardNotFound):
            self.quote(frm=self.dst["id"])          # B ning kartasi
        with self.assertRaises(CardNotFound):
            self.quote(frm="00000000-0000-0000-0000-000000000000")
        with self.assertRaises(CardNotFound):
            self.quote(frm="not-a-uuid")

    def test_unknown_receiver_and_same_card(self):
        with self.assertRaises(ReceiverNotFound):
            self.quote(pan=make_pan("8600", "33333333333"))
        with self.assertRaises(SameCard):
            self.quote(pan=PAN_A)

    def test_insufficient_funds_at_quote(self):
        small = Env(sandbox_start_balance_tiyin=500_000, transfer_fee_min_tiyin=5_000)
        s, d = small.card(small.a, PAN_A), small.card(small.b, PAN_B)
        with self.assertRaises(InsufficientFunds):
            small.wallet.create_transfer(small.a, "key-00000009", s["id"], PAN_B, 500_000)  # + komissiya

    def test_insufficient_at_confirm_fails_transfer_and_keeps_money(self):
        e = Env(sandbox_start_balance_tiyin=1_500_000)
        s, d = e.card(e.a, PAN_A), e.card(e.b, PAN_B)
        q1 = e.wallet.create_transfer(e.a, "key-aaaaaaa1", s["id"], PAN_B, 1_000_000)
        q2 = e.wallet.create_transfer(e.a, "key-aaaaaaa2", s["id"], PAN_B, 1_000_000)  # har biri alohida yetadi
        e.wallet.confirm_transfer(e.a, q1["id"], PIN)
        with self.assertRaises(InsufficientFunds):
            e.wallet.confirm_transfer(e.a, q2["id"], PIN)
        self.assertEqual(e.wallet.get_transfer(e.a, q2["id"])["status"], "failed")
        self.assertEqual(e.wallet.get_transfer(e.a, q2["id"])["failure_reason"], "insufficient_funds")
        self.assertEqual(e.store.get_card(s["id"]).balance, e.store.ledger_sum(s["id"]))

    def test_daily_limit_enforced_at_confirm(self):
        e = Env(transfer_daily_limit_tiyin=1_500_000)
        s, d = e.card(e.a, PAN_A), e.card(e.b, PAN_B)
        q1 = e.wallet.create_transfer(e.a, "key-bbbbbbb1", s["id"], PAN_B, 1_000_000)
        q2 = e.wallet.create_transfer(e.a, "key-bbbbbbb2", s["id"], PAN_B, 1_000_000)
        e.wallet.confirm_transfer(e.a, q1["id"], PIN)
        with self.assertRaises(DailyLimitExceeded):
            e.wallet.confirm_transfer(e.a, q2["id"], PIN)
        e.clock.advance(86_401)  # sutka o'tgach limit yangilanadi
        q2 = e.wallet.create_transfer(e.a, "key-bbbbbbb3", s["id"], PAN_B, 1_000_000)
        self.assertEqual(e.wallet.confirm_transfer(e.a, q2["id"], PIN)["status"], "completed")

    def test_expired_quote_cannot_be_confirmed(self):
        q = self.quote()
        self.e.clock.advance(301)
        with self.assertRaises(TransferExpired):
            self.e.wallet.confirm_transfer(self.e.a, q["id"], PIN)
        self.assertEqual(self.balances(), (START, START))
        with self.assertRaises(TransferNotPending):
            self.e.wallet.confirm_transfer(self.e.a, q["id"], PIN)

    def test_cancel(self):
        q = self.quote()
        self.assertEqual(self.e.wallet.cancel_transfer(self.e.a, q["id"])["status"], "cancelled")
        self.assertEqual(self.e.wallet.cancel_transfer(self.e.a, q["id"])["status"], "cancelled")  # takroriy cancel xavfsiz
        with self.assertRaises(TransferNotPending):
            self.e.wallet.confirm_transfer(self.e.a, q["id"], PIN)
        done = self.quote(key="key-00000005")
        self.e.wallet.confirm_transfer(self.e.a, done["id"], PIN)
        with self.assertRaises(TransferNotPending):
            self.e.wallet.cancel_transfer(self.e.a, done["id"])  # bajarilganini bekor qilib bo'lmaydi

    def test_only_owner_can_confirm_or_cancel_or_view_pending(self):
        q = self.quote()
        with self.assertRaises(TransferNotFound):
            self.e.wallet.confirm_transfer(self.e.b, q["id"], PIN)
        with self.assertRaises(TransferNotFound):
            self.e.wallet.cancel_transfer(self.e.b, q["id"])
        with self.assertRaises(TransferNotFound):
            self.e.wallet.get_transfer(self.e.b, q["id"])  # qabul qiluvchi hali tasdiqlanmaganini ko'ra olmaydi
        with self.assertRaises(TransferNotFound):
            self.e.wallet.get_transfer(self.e.a, "not-a-uuid")

    def test_deleted_card_between_quote_and_confirm_fails_safely(self):
        q = self.quote()
        self.e.wallet.delete_card(self.e.b, self.dst["id"])
        with self.assertRaises(CardUnavailable):
            self.e.wallet.confirm_transfer(self.e.a, q["id"], PIN)
        self.assertEqual(self.e.store.get_card(self.src["id"]).balance, START)

    def test_parallel_confirms_debit_exactly_once(self):
        q = self.quote()
        results = []
        lock = threading.Lock()

        def worker():
            try:
                r = self.e.wallet.confirm_transfer(self.e.a, q["id"], PIN)
                out = r["status"]
            except Exception as ex:  # noqa: BLE001
                out = type(ex).__name__
            with lock:
                results.append(out)

        ts = [threading.Thread(target=worker) for _ in range(12)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(self.balances(), (START - 1_010_000, START + 1_000_000))
        self.assertEqual(self.e.store.ledger_sum(self.src["id"]), START - 1_010_000)


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.e = Env()
        self.src = self.e.card(self.e.a, PAN_A)
        self.dst = self.e.card(self.e.b, PAN_B)
        self.ids = []
        for i in range(5):
            self.e.clock.advance(10)
            q = self.e.wallet.create_transfer(self.e.a, f"hist-key-{i:04d}", self.src["id"], PAN_B, 200_000)
            self.e.wallet.confirm_transfer(self.e.a, q["id"], PIN)
            self.ids.append(q["id"])
        self.e.clock.advance(10)
        self.pending = self.e.wallet.create_transfer(self.e.a, "hist-key-9999", self.src["id"], PAN_B, 200_000)

    def test_pagination_covers_everything_once_newest_first(self):
        seen, cursor = [], None
        while True:
            items, cursor = self.e.wallet.history(self.e.a, limit=2, cursor=cursor)
            seen += [i["id"] for i in items]
            if cursor is None:
                break
        self.assertEqual(seen, [self.pending["id"]] + self.ids[::-1])
        self.assertEqual(len(seen), len(set(seen)))

    def test_receiver_sees_only_completed_as_received(self):
        items, _ = self.e.wallet.history(self.e.b, limit=50)
        self.assertEqual(len(items), 5)
        self.assertTrue(all(i["direction"] == "received" and i["status"] == "completed" for i in items))
        self.assertTrue(all(i["fee_tiyin"] == 0 and "from_card_id" not in i for i in items))
        self.assertEqual(self.e.wallet.history(self.e.b, direction="sent")[0], [])

    def test_filters(self):
        pend, _ = self.e.wallet.history(self.e.a, status="pending")
        self.assertEqual([i["id"] for i in pend], [self.pending["id"]])
        self.assertEqual(len(self.e.wallet.history(self.e.a, status="completed", limit=50)[0]), 5)
        self.assertEqual(self.e.wallet.history(self.e.a, direction="received")[0], [])

    def test_receipt_only_for_completed(self):
        items, _ = self.e.wallet.history(self.e.a, limit=50)
        for i in items:
            self.assertEqual(i["receipt"] is not None, i["status"] == "completed")

    def test_bad_params(self):
        for kw in ({"limit": 0}, {"limit": 51}, {"limit": "5"}, {"status": "x"}, {"direction": "up"}, {"cursor": "!!!"}):
            with self.assertRaises(ValidationError, msg=kw):
                self.e.wallet.history(self.e.a, **kw)

    def test_users_do_not_see_each_others_history(self):
        c = self.e.card(self.e.b, PAN_C)
        q = self.e.wallet.create_transfer(self.e.b, "b-hist-key-1", c["id"], PAN_A, 200_000)
        self.e.wallet.confirm_transfer(self.e.b, q["id"], PIN)
        ids_a = {i["id"] for i in self.e.wallet.history(self.e.a, limit=50)[0]}
        self.assertIn(q["id"], ids_a)  # A qabul qiluvchi sifatida ko'radi
        stranger = self.e._user("903333333")
        self.assertEqual(self.e.wallet.history(stranger)[0], [])


class SecurityRegressionTests(unittest.TestCase):
    def test_no_pan_pin_or_token_anywhere_in_audit_or_views(self):
        e = Env()
        s, d = e.card(e.a, PAN_A), e.card(e.b, PAN_B)
        q = e.wallet.create_transfer(e.a, "sec-key-0001", s["id"], PAN_B, 1_000_000)
        try:
            e.wallet.confirm_transfer(e.a, q["id"], "9999")
        except PinInvalid:
            pass
        done = e.wallet.confirm_transfer(e.a, q["id"], PIN)
        blob = repr([(x.event, x.fields) for x in e.audit.events]) + repr(done) + repr(e.wallet.history(e.a)) + repr(e.wallet.lookup_receiver(e.a, PAN_B))
        for secret in (PAN_A, PAN_B, PAN_A[6:12], PAN_B[6:12], "9999", PIN):
            self.assertNotIn(secret, blob)

    def test_pan_is_not_stored_in_store(self):
        e = Env()
        e.card(e.a, PAN_A)
        raw = repr(e.store.__dict__)
        self.assertNotIn(PAN_A, raw)
        self.assertNotIn(PAN_A[6:12], raw)


class ConfigTests(unittest.TestCase):
    def mk(self, **kw):
        return Settings(env="test", jwt_secret=SECRET_A, otp_secret=SECRET_B, **kw)

    def test_disabled_by_default_and_key_required_when_enabled(self):
        self.mk().validate()
        self.assertFalse(self.mk().wallet_enabled)
        with self.assertRaises(ConfigError):
            self.mk(wallet_enabled=True).validate()
        with self.assertRaises(ConfigError):
            self.mk(wallet_enabled=True, card_index_key="short").validate()
        with self.assertRaises(ConfigError):
            self.mk(wallet_enabled=True, card_index_key=SECRET_A).validate()
        self.mk(wallet_enabled=True, card_index_key=KEY).validate()

    def test_limits_must_be_ordered_and_fee_sane(self):
        for kw in (
            {"transfer_min_tiyin": 0},
            {"transfer_min_tiyin": 10, "transfer_max_tiyin": 5},
            {"transfer_max_tiyin": 10**12},
            {"transfer_fee_bps": -1},
            {"transfer_fee_bps": 6000},
        ):
            with self.assertRaises(ConfigError, msg=kw):
                self.mk(**kw).validate()

    def test_from_env_parses_wallet_settings(self):
        s = Settings.from_env(
            {
                "JWT_SECRET": SECRET_A, "OTP_SECRET": SECRET_B, "APP_ENV": "test", "WALLET_ENABLED": "true",
                "CARD_INDEX_KEY": KEY, "TRANSFER_FEE_BPS": "50",
            }
        )
        self.assertTrue(s.wallet_enabled)
        self.assertEqual(s.transfer_fee_bps, 50)
        self.assertNotIn(KEY, repr(s))  # kalit repr'ga tushmaydi


class UnauthorizedTests(unittest.TestCase):
    def test_wallet_needs_valid_token(self):
        e = Env()
        with self.assertRaises(TokenInvalid):
            e.auth.authenticate("garbage")


if __name__ == "__main__":
    unittest.main()
