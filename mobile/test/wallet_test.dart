import 'package:flutter_test/flutter_test.dart';
import 'package:tezyubor_mobile/core/money.dart';
import 'package:tezyubor_mobile/core/validators.dart';
import 'package:tezyubor_mobile/features/wallet/data/mock_wallet_repository.dart';
import 'package:tezyubor_mobile/features/wallet/data/wallet_repository.dart';
import 'package:tezyubor_mobile/features/wallet/domain/wallet_models.dart';

void main() {
  group('formatSom', () {
    test('minglik guruhlash', () {
      expect(formatSom(0), "0 so'm");
      expect(formatSom(1234500), "12 345 so'm");
      expect(formatSom(100000000), "1 000 000 so'm");
    });
    test('tiyin va ishora', () {
      expect(formatSom(1250), "12,50 so'm");
      expect(formatSom(-500000), "−5 000 so'm");
      expect(formatSom(500000, signed: true), "+5 000 so'm");
    });
  });

  group('normalizeCardNumber', () {
    test('to\'g\'ri Uzcard va Humo', () {
      expect(normalizeCardNumber('8600 5555 6666 7770'), '8600555566667770');
      expect(normalizeCardNumber('9860111122223337'), '9860111122223337');
    });
    test('noto\'g\'ri: Luhn, prefiks, uzunlik', () {
      expect(normalizeCardNumber('8600555566667771'), isNull); // Luhn
      expect(normalizeCardNumber('4111111111111111'), isNull); // prefiks
      expect(normalizeCardNumber('86005555'), isNull); // uzun emas
      expect(normalizeCardNumber(''), isNull);
    });
  });

  group('parseAmountTiyin', () {
    test('chegaralar', () {
      expect(parseAmountTiyin('1000'), 100000);
      expect(parseAmountTiyin('1 000'), 100000);
      expect(parseAmountTiyin('10000000'), 1000000000);
      expect(parseAmountTiyin('999'), isNull);
      expect(parseAmountTiyin('10000001'), isNull);
      expect(parseAmountTiyin(''), isNull);
      expect(parseAmountTiyin('99999999999'), isNull);
    });
  });

  test('transferFeeTiyin: 0,5% yuqoriga yaxlitlanadi', () {
    expect(transferFeeTiyin(200000 * 100), 1000 * 100);
    expect(transferFeeTiyin(1001), 6); // 5.005 -> 6
  });

  group('MockWalletRepository', () {
    late MockWalletRepository repo;
    const toCard = '8600555566667770';

    setUp(() => repo = MockWalletRepository());

    test("o'tkazma balansni va tarixni yangilaydi", () async {
      final before = (await repo.cards()).first;
      final amount = 100000 * 100;
      final txn = await repo.transfer(
        fromCardId: before.id,
        toCardNumber: toCard,
        amountTiyin: amount,
        idempotencyKey: 'k1',
      );
      final after = (await repo.cards()).first;
      expect(after.balanceTiyin, before.balanceTiyin - amount - txn.feeTiyin);
      expect((await repo.transactions()).first.id, txn.id);
    });

    test('bir xil Idempotency-Key pulni ikki marta yechmaydi', () async {
      final card = (await repo.cards()).first;
      final a = await repo.transfer(
        fromCardId: card.id,
        toCardNumber: toCard,
        amountTiyin: 50000 * 100,
        idempotencyKey: 'same',
      );
      final b = await repo.transfer(
        fromCardId: card.id,
        toCardNumber: toCard,
        amountTiyin: 50000 * 100,
        idempotencyKey: 'same',
      );
      expect(b.id, a.id);
      final after = (await repo.cards()).first;
      expect(after.balanceTiyin, card.balanceTiyin - 50000 * 100 - a.feeTiyin);
    });

    test("mablag' yetmasa INSUFFICIENT_FUNDS va balans o'zgarmaydi", () async {
      final card = (await repo.cards()).last; // 480 000 so'm
      expect(
        () => repo.transfer(
          fromCardId: card.id,
          toCardNumber: toCard,
          amountTiyin: 479000 * 100, // + komissiya > balans
          idempotencyKey: 'k2',
        ),
        throwsA(isA<WalletException>().having((e) => e.code, 'code', 'INSUFFICIENT_FUNDS')),
      );
      expect((await repo.cards()).last.balanceTiyin, card.balanceTiyin);
    });

    test("o'z kartasiga o'tkazma taqiqlanadi", () async {
      final card = (await repo.cards()).first; // oxiri 9012 (8600123456789012)
      expect(
        () => repo.transfer(
          fromCardId: card.id,
          toCardNumber: '8600123456789012',
          amountTiyin: 10000 * 100,
          idempotencyKey: 'k3',
        ),
        throwsA(isA<WalletException>()),
      );
    });

    test("noto'g'ri karta raqami rad etiladi", () async {
      final card = (await repo.cards()).first;
      expect(
        () => repo.transfer(
          fromCardId: card.id,
          toCardNumber: '8600555566667771',
          amountTiyin: 10000 * 100,
          idempotencyKey: 'k4',
        ),
        throwsA(isA<WalletException>().having((e) => e.code, 'code', 'VALIDATION_ERROR')),
      );
    });

    test("to'lov: hisob uzunligi tekshiriladi va summa yechiladi", () async {
      final card = (await repo.cards()).first;
      expect(
        () => repo.pay(
          fromCardId: card.id,
          serviceId: 'mobile_a',
          account: '12345',
          amountTiyin: 10000 * 100,
          idempotencyKey: 'p1',
        ),
        throwsA(isA<WalletException>()),
      );
      final txn = await repo.pay(
        fromCardId: card.id,
        serviceId: 'mobile_a',
        account: '901234567',
        amountTiyin: 10000 * 100,
        idempotencyKey: 'p2',
      );
      expect(txn.feeTiyin, 0);
      expect((await repo.cards()).first.balanceTiyin, card.balanceTiyin - 10000 * 100);
    });
  });
}
