import '../../../core/validators.dart';
import '../domain/wallet_models.dart';
import 'wallet_repository.dart';

/// TEST REJIMI: ma'lumotlar xotirada, ilova yopilsa boshlang'ich holatga qaytadi.
/// Balanslar va tarix SOXTA — faqat UI oqimini sinash uchun (ilovada "TEST REJIMI" banneri ko'rinadi).
class MockWalletRepository implements WalletRepository {
  MockWalletRepository({DateTime Function()? clock}) : _clock = clock ?? DateTime.now {
    final now = _clock();
    _recipients.add(const Recipient(cardNumber: '8600555566667770'));
    _txns.addAll([
      Txn(
        id: 'seed-3',
        type: TxnType.payment,
        title: 'Elektr energiyasi',
        amountTiyin: -85000 * 100,
        feeTiyin: 0,
        createdAt: now.subtract(const Duration(days: 1)),
        status: TxnStatus.succeeded,
      ),
      Txn(
        id: 'seed-2',
        type: TxnType.transfer,
        title: "Kartaga o'tkazma •••• 7770",
        amountTiyin: -200000 * 100,
        feeTiyin: 1000 * 100,
        createdAt: now.subtract(const Duration(days: 3)),
        status: TxnStatus.succeeded,
      ),
      Txn(
        id: 'seed-1',
        type: TxnType.topUp,
        title: "Hisob to'ldirildi",
        amountTiyin: 1000000 * 100,
        feeTiyin: 0,
        createdAt: now.subtract(const Duration(days: 6)),
        status: TxnStatus.succeeded,
      ),
    ]);
  }

  final DateTime Function() _clock;

  final List<CardInfo> _cards = [
    const CardInfo(id: 'card-1', last4: '9012', network: 'Uzcard', balanceTiyin: 2500000 * 100),
    const CardInfo(id: 'card-2', last4: '1098', network: 'Humo', balanceTiyin: 480000 * 100),
  ];
  final List<Txn> _txns = [];
  final List<Recipient> _recipients = [];
  final List<FavoritePayment> _favorites = [];
  int _favSeq = 0;

  /// Idempotency-Key -> birinchi natija. Qayta kelgan so'rov pulni qayta yechmaydi.
  final Map<String, Txn> _byKey = {};
  int _seq = 0;

  @override
  Future<List<CardInfo>> cards() async {
    await _latency();
    return List.unmodifiable(_cards);
  }

  @override
  Future<List<Txn>> transactions({int limit = 50}) async {
    await _latency();
    final sorted = [..._txns]..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return sorted.take(limit).toList();
  }

  @override
  Future<Txn> transfer({
    required String fromCardId,
    required String toCardNumber,
    required int amountTiyin,
    required String idempotencyKey,
  }) async {
    await _latency();
    final done = _byKey[idempotencyKey];
    if (done != null) return done;

    final to = normalizeCardNumber(toCardNumber);
    if (to == null) {
      throw const WalletException('VALIDATION_ERROR', "Karta raqami noto'g'ri");
    }
    _checkAmount(amountTiyin);
    final fee = transferFeeTiyin(amountTiyin);
    final source = _cards.where((c) => c.id == fromCardId).firstOrNull;
    if (source != null && to.substring(12) == source.last4) {
      // Mock'da faqat oxirgi 4 raqam saqlanadi, shuning uchun o'z kartasini shu bilan aniqlaymiz.
      throw const WalletException('VALIDATION_ERROR', "O'z kartangizga o'tkazib bo'lmaydi");
    }
    _debit(fromCardId, amountTiyin + fee);
    _recipients.removeWhere((r) => r.cardNumber == to);
    _recipients.insert(0, Recipient(cardNumber: to));
    return _record(
      idempotencyKey,
      Txn(
        id: _nextId(),
        type: TxnType.transfer,
        title: "Kartaga o'tkazma •••• ${to.substring(12)}",
        amountTiyin: -amountTiyin,
        feeTiyin: fee,
        createdAt: _clock(),
        status: TxnStatus.succeeded,
      ),
    );
  }

  @override
  Future<Txn> transferOwn({
    required String fromCardId,
    required String toCardId,
    required int amountTiyin,
    required String idempotencyKey,
  }) async {
    await _latency();
    final done = _byKey[idempotencyKey];
    if (done != null) return done;

    if (fromCardId == toCardId) {
      throw const WalletException('VALIDATION_ERROR', "Bir xil kartani tanlab bo'lmaydi");
    }
    final toIndex = _cards.indexWhere((c) => c.id == toCardId);
    if (toIndex < 0) {
      throw const WalletException('CARD_NOT_FOUND', 'Karta topilmadi');
    }
    _checkAmount(amountTiyin);
    final from = _debit(fromCardId, amountTiyin);
    final to = _cards[toIndex];
    _cards[toIndex] = to.withBalance(to.balanceTiyin + amountTiyin);
    return _record(
      idempotencyKey,
      Txn(
        id: _nextId(),
        type: TxnType.ownTransfer,
        title: 'Kartalar orasida \u2022\u2022\u2022\u2022 ${from.last4} \u2192 \u2022\u2022\u2022\u2022 ${to.last4}',
        amountTiyin: -amountTiyin,
        feeTiyin: 0,
        createdAt: _clock(),
        status: TxnStatus.succeeded,
      ),
    );
  }

  @override
  Future<List<Recipient>> recentRecipients() async {
    await _latency();
    return List.unmodifiable(_recipients);
  }

  @override
  Future<List<FavoritePayment>> favorites() async {
    await _latency();
    return List.unmodifiable(_favorites);
  }

  @override
  Future<FavoritePayment> addFavorite({
    required String serviceId,
    required String account,
    required int amountTiyin,
  }) async {
    await _latency();
    final service = payServiceById(serviceId);
    if (service == null) {
      throw const WalletException('VALIDATION_ERROR', 'Xizmat topilmadi');
    }
    final digits = account.replaceAll(RegExp(r'\D'), '');
    if (digits.length != service.accountDigits) {
      throw WalletException('VALIDATION_ERROR', "${service.accountLabel} noto'g'ri");
    }
    _checkAmount(amountTiyin);
    final old = _favorites.where((f) => f.serviceId == serviceId && f.account == digits).firstOrNull;
    _favorites.removeWhere((f) => f.serviceId == serviceId && f.account == digits);
    final fav = FavoritePayment(
      id: old?.id ?? 'fav-${++_favSeq}',
      serviceId: serviceId,
      account: digits,
      amountTiyin: amountTiyin,
    );
    _favorites.insert(0, fav);
    return fav;
  }

  @override
  Future<void> removeFavorite(String id) async {
    await _latency();
    _favorites.removeWhere((f) => f.id == id);
  }

  @override
  Future<Txn> pay({
    required String fromCardId,
    required String serviceId,
    required String account,
    required int amountTiyin,
    required String idempotencyKey,
  }) async {
    await _latency();
    final done = _byKey[idempotencyKey];
    if (done != null) return done;

    final service = kPayServices.where((s) => s.id == serviceId).firstOrNull;
    if (service == null) {
      throw const WalletException('VALIDATION_ERROR', 'Xizmat topilmadi');
    }
    final digits = account.replaceAll(RegExp(r'\D'), '');
    if (digits.length != service.accountDigits) {
      throw WalletException('VALIDATION_ERROR', "${service.accountLabel} noto'g'ri");
    }
    _checkAmount(amountTiyin);
    _debit(fromCardId, amountTiyin);
    return _record(
      idempotencyKey,
      Txn(
        id: _nextId(),
        type: TxnType.payment,
        title: service.name,
        amountTiyin: -amountTiyin,
        feeTiyin: 0,
        createdAt: _clock(),
        status: TxnStatus.succeeded,
      ),
    );
  }

  // --- ichki ---

  Future<void> _latency() => Future<void>.delayed(const Duration(milliseconds: 350));

  String _nextId() => 'mock-txn-${++_seq}';

  void _checkAmount(int amountTiyin) {
    if (amountTiyin < kMinAmountTiyin || amountTiyin > kMaxAmountTiyin) {
      throw const WalletException('VALIDATION_ERROR', "Summa ruxsat etilgan chegaradan tashqarida");
    }
  }

  CardInfo _debit(String cardId, int totalTiyin) {
    final i = _cards.indexWhere((c) => c.id == cardId);
    if (i < 0) {
      throw const WalletException('CARD_NOT_FOUND', 'Karta topilmadi');
    }
    final card = _cards[i];
    if (card.balanceTiyin < totalTiyin) {
      throw const WalletException('INSUFFICIENT_FUNDS', "Kartada mablag' yetarli emas");
    }
    _cards[i] = card.withBalance(card.balanceTiyin - totalTiyin);
    return card;
  }

  Txn _record(String key, Txn txn) {
    _txns.add(txn);
    _byKey[key] = txn;
    return txn;
  }
}
