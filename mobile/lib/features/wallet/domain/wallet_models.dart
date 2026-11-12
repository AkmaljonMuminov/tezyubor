import '../../../core/assets.dart';

/// `ownTransfer` — o'z kartalari orasida: jami balansni o'zgartirmaydi, tushum/xarajatga kirmaydi.
enum TxnType { transfer, ownTransfer, payment, topUp }

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

/// Oldin o'tkazma qilingan qabul qiluvchi.
/// TEST REJIMI: mock'da to'liq raqam xotirada. Haqiqiy tizimda karta raqami saqlanmaydi, faqat provayder tokeni.
class Recipient {
  const Recipient({required this.cardNumber});

  final String cardNumber;

  String get masked => '${cardNumber.substring(0, 4)} \u2022\u2022\u2022\u2022 \u2022\u2022\u2022\u2022 ${cardNumber.substring(12)}';
}

class PeriodSummary {
  const PeriodSummary({required this.incomeTiyin, required this.expenseTiyin});

  final int incomeTiyin;

  /// Musbat son (komissiya bilan).
  final int expenseTiyin;
}

/// Berilgan oy uchun tushum va xarajat. Faqat muvaffaqiyatli operatsiyalar;
/// o'z kartalari orasidagi o'tkazma hisobga olinmaydi.
PeriodSummary summarizeMonth(List<Txn> txns, DateTime month) {
  var income = 0;
  var expense = 0;
  for (final t in txns) {
    if (t.status != TxnStatus.succeeded || t.type == TxnType.ownTransfer) continue;
    final d = t.createdAt.toLocal();
    if (d.year != month.year || d.month != month.month) continue;
    if (t.amountTiyin > 0) {
      income += t.amountTiyin;
    } else {
      expense += -t.totalTiyin;
    }
  }
  return PeriodSummary(incomeTiyin: income, expenseTiyin: expense);
}

enum TxnFilter { all, income, expense }

List<Txn> applyFilter(List<Txn> txns, TxnFilter f) {
  switch (f) {
    case TxnFilter.all:
      return txns;
    case TxnFilter.income:
      return txns.where((t) => t.amountTiyin > 0 && t.type != TxnType.ownTransfer).toList();
    case TxnFilter.expense:
      return txns.where((t) => t.amountTiyin < 0 && t.type != TxnType.ownTransfer).toList();
  }
}

/// Kun bo'yicha guruhlaydi (yangisi birinchi). Kalit — kun boshi (mahalliy vaqt).
List<MapEntry<DateTime, List<Txn>>> groupByDay(List<Txn> txns) {
  final sorted = [...txns]..sort((a, b) => b.createdAt.compareTo(a.createdAt));
  final groups = <DateTime, List<Txn>>{};
  for (final t in sorted) {
    final l = t.createdAt.toLocal();
    groups.putIfAbsent(DateTime(l.year, l.month, l.day), () => []).add(t);
  }
  return groups.entries.toList();
}
