import 'package:flutter_test/flutter_test.dart';
import 'package:tezyubor_mobile/core/format.dart';
import 'package:tezyubor_mobile/features/wallet/data/mock_wallet_repository.dart';
import 'package:tezyubor_mobile/features/wallet/domain/receipt.dart';
import 'package:tezyubor_mobile/features/wallet/domain/wallet_models.dart';

Map<String, String> _asMap(Txn t) => {for (final l in buildReceiptLines(t)) l.label: l.value};

void main() {
  late MockWalletRepository repo;
  setUp(() => repo = MockWalletRepository(clock: () => DateTime(2026, 11, 12, 14, 30)));

  test('formatPhone9', () {
    expect(formatPhone9('901234567'), '+998 90 123 45 67');
    expect(formatPhone9('12345'), '12345');
  });

  test("mobil to'lov cheki: telefon formatlanadi, karta maskalangan, komissiya 0", () async {
    final card = (await repo.cards()).first;
    final txn = await repo.pay(
      fromCardId: card.id,
      serviceId: 'ucell',
      account: '901234567',
      amountTiyin: 12000 * 100,
      idempotencyKey: 'c1',
    );
    final m = _asMap(txn);
    expect(m['Holat'], 'Muvaffaqiyatli');
    expect(m['Xizmat'], 'Ucell');
    expect(m['Telefon raqami'], '+998 90 123 45 67');
    expect(m['Karta'], contains('9012'));
    expect(m['Karta'], isNot(contains('8600')));
    expect(m['Komissiya'], "0\u00A0so'm");
    expect(m['Operatsiya raqami'], txn.id);
    expect(m['Sana'], '12.11.2026 14:30');
  });

  test("elektr to'lovi cheki: ETK alohida qator, hisob raqami ETK kodisiz", () async {
    final card = (await repo.cards()).first;
    final txn = await repo.pay(
      fromCardId: card.id,
      serviceId: 'electricity',
      account: '18227123456',
      amountTiyin: 20000 * 100,
      idempotencyKey: 'c2',
    );
    final m = _asMap(txn);
    expect(m["Elektr ta'minoti tumani"], "18227 - Pastdarg'om ETK");
    expect(m['Abonent hisob-raqami'], '123456');
  });

  test("kartaga o'tkazma cheki: qabul qiluvchi maskalangan, jami = summa + komissiya", () async {
    final card = (await repo.cards()).first;
    final txn = await repo.transfer(
      fromCardId: card.id,
      toCardNumber: '9860111122223337',
      amountTiyin: 100000 * 100,
      idempotencyKey: 'c3',
    );
    final m = _asMap(txn);
    expect(m['Qabul qiluvchi karta'], '9860 •••• •••• 3337');
    // To'liq karta raqami chekning hech qayerida yo'q.
    expect(buildReceiptText(txn, test: false), isNot(contains('9860111122223337')));
    expect(m['Summa'], "100 000 so'm");
    expect(m['Komissiya'], "500 so'm");
    expect(m['Jami yechildi'], "100 500 so'm");
  });

  test("kartalar orasida cheki: ikkala karta, komissiya 0", () async {
    final cards = await repo.cards();
    final txn = await repo.transferOwn(
      fromCardId: cards.first.id,
      toCardId: cards.last.id,
      amountTiyin: 50000 * 100,
      idempotencyKey: 'c4',
    );
    final m = _asMap(txn);
    expect(m['Qaysi kartadan'], contains('9012'));
    expect(m['Qaysi kartaga'], contains('1098'));
    expect(m['Komissiya'], "0 so'm");
  });

  test("tushum cheki: komissiya va 'Jami yechildi' qatori yo'q", () async {
    final seed = (await repo.transactions()).firstWhere((t) => t.type == TxnType.topUp);
    final m = _asMap(seed);
    expect(m.containsKey('Komissiya'), isFalse);
    expect(m.containsKey('Jami yechildi'), isFalse);
    expect(m['Summa'], "1 000 000 so'm");
  });

  test("bekor qilingan operatsiya cheki holati", () {
    final failed = Txn(
      id: 'x',
      type: TxnType.payment,
      title: 'Ucell',
      amountTiyin: -1000 * 100,
      feeTiyin: 0,
      createdAt: DateTime(2026, 11, 12),
      status: TxnStatus.failed,
    );
    expect(_asMap(failed)['Holat'], 'Bekor qilingan');
  });

  test('chek matni: test rejimida "TEST CHEK" belgisi bor, haqiqiyda yo\'q', () async {
    final seed = (await repo.transactions()).first;
    final test = buildReceiptText(seed, test: true);
    final real = buildReceiptText(seed, test: false);
    expect(test, contains('TEST CHEK'));
    expect(real, isNot(contains('TEST')));
    expect(test, contains('Operatsiya raqami: ${seed.id}'));
  });

  test("tarixdagi boshlang'ich operatsiyalar ham to'liq chekka ega", () async {
    for (final t in await repo.transactions()) {
      expect(buildReceiptLines(t).length, greaterThanOrEqualTo(5), reason: t.id);
    }
  });
}
