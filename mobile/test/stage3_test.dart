import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:tezyubor_mobile/core/format.dart';
import 'package:tezyubor_mobile/core/network/api_client.dart';
import 'package:tezyubor_mobile/core/network/token_store.dart';
import 'package:tezyubor_mobile/core/validators.dart';
import 'package:tezyubor_mobile/features/auth/data/http_auth_repository.dart';
import 'package:tezyubor_mobile/features/wallet/data/mock_wallet_repository.dart';
import 'package:tezyubor_mobile/features/wallet/data/wallet_repository.dart';
import 'package:tezyubor_mobile/features/wallet/domain/wallet_models.dart';

Txn _t(String id, int amount, DateTime at,
    {int fee = 0, TxnType type = TxnType.payment, TxnStatus status = TxnStatus.succeeded}) {
  return Txn(
    id: id,
    type: type,
    title: id,
    amountTiyin: amount,
    feeTiyin: fee,
    createdAt: at,
    status: status,
  );
}

void main() {
  group('summarizeMonth', () {
    final now = DateTime(2026, 11, 12, 10);
    final txns = [
      _t('in', 5000 * 100, DateTime(2026, 11, 3), type: TxnType.topUp),
      _t('out', -2000 * 100, DateTime(2026, 11, 5)),
      _t('tr', -10000 * 100, DateTime(2026, 11, 6), fee: 50 * 100, type: TxnType.transfer),
      _t('own', -7000 * 100, DateTime(2026, 11, 7), type: TxnType.ownTransfer),
      _t('failed', -999 * 100, DateTime(2026, 11, 8), status: TxnStatus.failed),
      _t('old', -111 * 100, DateTime(2026, 10, 30)),
    ];

    test("komissiya xarajatga kiradi; o'z kartalari, bekor va boshqa oy hisobga olinmaydi", () {
      final s = summarizeMonth(txns, now);
      expect(s.incomeTiyin, 5000 * 100);
      expect(s.expenseTiyin, 2000 * 100 + 10000 * 100 + 50 * 100);
    });

    test("filtr: tushum/xarajatda o'z kartalari orasidagi o'tkazma ko'rinmaydi", () {
      expect(applyFilter(txns, TxnFilter.income).map((t) => t.id), ['in']);
      expect(applyFilter(txns, TxnFilter.expense).map((t) => t.id), ['out', 'tr', 'failed', 'old']);
      expect(applyFilter(txns, TxnFilter.all).length, txns.length);
    });
  });

  test('groupByDay: kunlar yangisidan boshlanadi, kun ichida ham', () {
    final g = groupByDay([
      _t('a', -100, DateTime(2026, 11, 9, 19, 14)),
      _t('b', -100, DateTime(2026, 11, 11, 12, 45)),
      _t('c', -100, DateTime(2026, 11, 11, 13, 36)),
    ]);
    expect(g.map((e) => e.key), [DateTime(2026, 11, 11), DateTime(2026, 11, 9)]);
    expect(g.first.value.map((t) => t.id), ['c', 'b']);
  });

  test('dayLabel', () {
    final now = DateTime(2026, 11, 12, 1, 5);
    expect(dayLabel(DateTime(2026, 11, 12), now), 'Bugun');
    expect(dayLabel(DateTime(2026, 11, 11, 23), now), 'Kecha');
    expect(dayLabel(DateTime(2026, 11, 9), now), '9 noyabr 2026');
  });

  test('maskPhone', () {
    expect(maskPhone('998901234567'), '+998 90 *** ** 67');
  });

  group('MockWalletRepository: kartalar orasida va qabul qiluvchilar', () {
    late MockWalletRepository repo;
    setUp(() => repo = MockWalletRepository());

    test("jami balans o'zgarmaydi, komissiya yo'q, tushum/xarajatga kirmaydi", () async {
      final before = await repo.cards();
      final total = before.fold<int>(0, (s, c) => s + c.balanceTiyin);
      final txn = await repo.transferOwn(
        fromCardId: before.first.id,
        toCardId: before.last.id,
        amountTiyin: 100000 * 100,
        idempotencyKey: 'o1',
      );
      final after = await repo.cards();
      expect(after.fold<int>(0, (s, c) => s + c.balanceTiyin), total);
      expect(after.first.balanceTiyin, before.first.balanceTiyin - 100000 * 100);
      expect(after.last.balanceTiyin, before.last.balanceTiyin + 100000 * 100);
      expect(txn.type, TxnType.ownTransfer);
      expect(txn.feeTiyin, 0);
    });

    test('bir xil kalit ikki marta o\'tkazmaydi', () async {
      final cards = await repo.cards();
      final a = await repo.transferOwn(
        fromCardId: cards.first.id,
        toCardId: cards.last.id,
        amountTiyin: 50000 * 100,
        idempotencyKey: 'same',
      );
      final b = await repo.transferOwn(
        fromCardId: cards.first.id,
        toCardId: cards.last.id,
        amountTiyin: 50000 * 100,
        idempotencyKey: 'same',
      );
      expect(b.id, a.id);
      expect((await repo.cards()).first.balanceTiyin, cards.first.balanceTiyin - 50000 * 100);
    });

    test("bir xil karta va mablag' yetmasligi rad etiladi", () async {
      final cards = await repo.cards();
      expect(
        () => repo.transferOwn(
          fromCardId: cards.first.id,
          toCardId: cards.first.id,
          amountTiyin: 10000 * 100,
          idempotencyKey: 'x1',
        ),
        throwsA(isA<WalletException>()),
      );
      expect(
        () => repo.transferOwn(
          fromCardId: cards.last.id, // 480 000 so'm
          toCardId: cards.first.id,
          amountTiyin: 500000 * 100,
          idempotencyKey: 'x2',
        ),
        throwsA(isA<WalletException>().having((e) => e.code, 'code', 'INSUFFICIENT_FUNDS')),
      );
    });

    test("so'nggi qabul qiluvchi o'tkazmadan keyin birinchi bo'ladi va takrorlanmaydi", () async {
      final card = (await repo.cards()).first;
      await repo.transfer(
        fromCardId: card.id,
        toCardNumber: '9860111122223337',
        amountTiyin: 10000 * 100,
        idempotencyKey: 'r1',
      );
      await repo.transfer(
        fromCardId: card.id,
        toCardNumber: '8600555566667770',
        amountTiyin: 10000 * 100,
        idempotencyKey: 'r2',
      );
      final list = await repo.recentRecipients();
      expect(list.map((r) => r.cardNumber), ['8600555566667770', '9860111122223337']);
    });
  });

  group('HttpAuthRepository: telefon va chiqish', () {
    test('maskalangan telefon saqlanadi, chiqishda tokenlar va telefon o\'chadi', () async {
      final tokens = MemoryTokenStore();
      final client = MockClient((req) async {
        if (req.url.path == '/v1/auth/otp/request') {
          return http.Response(jsonEncode({'challenge_id': 'c1', 'expires_in': 120}), 200,
              headers: {'content-type': 'application/json'});
        }
        return http.Response('{}', 404);
      });
      final repo = HttpAuthRepository(ApiClient(baseUrl: 'http://test', client: client), tokens);

      await repo.requestOtp('90 123 45 67');
      expect(await repo.maskedPhone(), '+998 90 *** ** 67');
      // To'liq raqam hech qayerda saqlanmaydi.
      expect(await repo.maskedPhone(), isNot(contains('1234')));

      await tokens.saveTokens(access: 'A', refresh: 'R');
      await tokens.savePinSet(true);
      await repo.logout();
      expect(await tokens.readRefresh(), isNull);
      expect(await repo.hasPin(), isFalse);
      expect(await repo.maskedPhone(), isNull);
    });
  });
}
