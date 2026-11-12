import '../../../core/assets.dart';

enum TxnType { transfer, payment, topUp }

enum TxnStatus { succeeded, failed }

enum ServiceCategory { mobile, bills }

class CardInfo {
  const CardInfo({
    required this.id,
    required this.last4,
    required this.network,
    required this.balanceTiyin,
  });

  final String id;
  final String last4;

  /// 'Uzcard' yoki 'Humo'.
  final String network;
  final int balanceTiyin;

  String get masked => '•••• $last4';

  CardInfo withBalance(int tiyin) =>
      CardInfo(id: id, last4: last4, network: network, balanceTiyin: tiyin);
}

class Txn {
  const Txn({
    required this.id,
    required this.type,
    required this.title,
    required this.amountTiyin,
    required this.feeTiyin,
    required this.createdAt,
    required this.status,
  });

  final String id;
  final TxnType type;
  final String title;

  /// Manfiy — hisobdan yechildi, musbat — tushdi. Komissiya alohida (`feeTiyin`).
  final int amountTiyin;
  final int feeTiyin;
  final DateTime createdAt;
  final TxnStatus status;

  int get totalTiyin => amountTiyin - feeTiyin;
}

class PayService {
  const PayService({
    required this.id,
    required this.name,
    required this.category,
    required this.icon,
    required this.accountLabel,
    required this.accountDigits,
  });

  final String id;
  final String name;
  final ServiceCategory category;
  final String icon;

  /// Maydon nomi: "Telefon raqami", "Hisob raqami".
  final String accountLabel;

  /// Hisob raqamining aniq uzunligi (telefon uchun 9 — +998 siz).
  final int accountDigits;
}

/// Katalog hozircha ilova ichida (test). Haqiqiy katalog provayder shartnomasidan keyin serverdan keladi.
const List<PayService> kPayServices = [
  PayService(
    id: 'mobile_a',
    name: 'Mobil aloqa A',
    category: ServiceCategory.mobile,
    icon: AppAssets.icMobile,
    accountLabel: 'Telefon raqami',
    accountDigits: 9,
  ),
  PayService(
    id: 'mobile_b',
    name: 'Mobil aloqa B',
    category: ServiceCategory.mobile,
    icon: AppAssets.icMobile,
    accountLabel: 'Telefon raqami',
    accountDigits: 9,
  ),
  PayService(
    id: 'electricity',
    name: 'Elektr energiyasi',
    category: ServiceCategory.bills,
    icon: AppAssets.icBills,
    accountLabel: 'Hisob raqami',
    accountDigits: 8,
  ),
  PayService(
    id: 'gas',
    name: 'Tabiiy gaz',
    category: ServiceCategory.bills,
    icon: AppAssets.icBills,
    accountLabel: 'Hisob raqami',
    accountDigits: 8,
  ),
  PayService(
    id: 'water',
    name: 'Suv ta\'minoti',
    category: ServiceCategory.bills,
    icon: AppAssets.icBills,
    accountLabel: 'Hisob raqami',
    accountDigits: 8,
  ),
];

/// Komissiya: o'tkazmada 0,5% (yuqoriga yaxlitlanadi), to'lovda yo'q.
/// Ko'rsatish uchun; haqiqiy komissiyani SERVER hisoblaydi va qayta tekshiradi.
int transferFeeTiyin(int amountTiyin) => (amountTiyin * 5 + 999) ~/ 1000;
