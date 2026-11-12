import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/brand.dart';
import '../domain/wallet_models.dart';
import 'mock_wallet_repository.dart';

class WalletException implements Exception {
  const WalletException(this.code, this.message);
  final String code;
  final String message;

  @override
  String toString() => 'WalletException($code)';
}

/// Hamyon shartnomasi. Hozir faqat `MockWalletRepository` bor: backendda karta/o'tkazma/to'lov
/// modullari hali yo'q (ARCHITECTURE.md: keyingi bosqichlar), shuning uchun HTTP implementatsiya ham yo'q.
abstract class WalletRepository {
  Future<List<CardInfo>> cards();

  /// Eng yangilari birinchi.
  Future<List<Txn>> transactions({int limit = 50});

  /// Bir xil [idempotencyKey] bilan qayta chaqirilsa pul QAYTA yechilmaydi, avvalgi natija qaytadi.
  Future<Txn> transfer({
    required String fromCardId,
    required String toCardNumber,
    required int amountTiyin,
    required String idempotencyKey,
  });

  /// O'z kartalari orasida (komissiyasiz). Kalitlar [transfer] dagidek.
  Future<Txn> transferOwn({
    required String fromCardId,
    required String toCardId,
    required int amountTiyin,
    required String idempotencyKey,
  });

  /// Oldin o'tkazma qilingan qabul qiluvchilar, eng yangisi birinchi.
  Future<List<Recipient>> recentRecipients();

  /// Tanlangan to'lovlar (shablonlar), eng yangisi birinchi.
  Future<List<FavoritePayment>> favorites();

  /// Bir xil xizmat + hisob raqami bo'lsa yangi qator qo'shilmaydi, summa yangilanadi.
  Future<FavoritePayment> addFavorite({
    required String serviceId,
    required String account,
    required int amountTiyin,
  });

  Future<void> removeFavorite(String id);

  Future<Txn> pay({
    required String fromCardId,
    required String serviceId,
    required String account,
    required int amountTiyin,
    required String idempotencyKey,
  });
}

final walletRepositoryProvider = Provider<WalletRepository>((ref) {
  if (!kMockMode) {
    throw UnimplementedError(
      "Hamyon backendi hali yo'q. Hozircha API_MODE=mock ishlating.",
    );
  }
  return MockWalletRepository();
});

final cardsProvider = FutureProvider<List<CardInfo>>(
  (ref) => ref.watch(walletRepositoryProvider).cards(),
);

final recipientsProvider = FutureProvider<List<Recipient>>(
  (ref) => ref.watch(walletRepositoryProvider).recentRecipients(),
);

final favoritesProvider = FutureProvider<List<FavoritePayment>>(
  (ref) => ref.watch(walletRepositoryProvider).favorites(),
);

final transactionsProvider = FutureProvider<List<Txn>>(
  (ref) => ref.watch(walletRepositoryProvider).transactions(),
);
