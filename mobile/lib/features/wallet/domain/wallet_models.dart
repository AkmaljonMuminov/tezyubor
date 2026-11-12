import 'package:flutter/material.dart' show IconData, Icons;

/// `ownTransfer` — o'z kartalari orasida: jami balansni o'zgartirmaydi, tushum/xarajatga kirmaydi.
enum TxnType { transfer, ownTransfer, payment, topUp }

enum TxnStatus { succeeded, failed }

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
    this.serviceId,
    this.fromCard,
    this.toCard,
    this.account,
  });

  final String id;
  final TxnType type;

  /// To'lov bo'lsa — qaysi xizmatga (xizmat tarixi uchun).
  final String? serviceId;
  final String title;

  /// Chek uchun: qaysi kartadan yechildi ("Uzcard •••• 9012"). Karta raqami to'liq saqlanmaydi.
  final String? fromCard;

  /// Chek uchun: qabul qiluvchi karta (maskalangan: "8600 •••• •••• 7770" yoki o'z kartasi).
  final String? toCard;

  /// Chek uchun: to'lov qilingan hisob raqami / telefon (faqat raqamlar).
  final String? account;

  /// Manfiy — hisobdan yechildi, musbat — tushdi. Komissiya alohida (`feeTiyin`).
  final int amountTiyin;
  final int feeTiyin;
  final DateTime createdAt;
  final TxnStatus status;

  int get totalTiyin => amountTiyin - feeTiyin;
}

/// To'lov kategoriyasi. Xizmatlari bo'lmasa ekranda "Tez orada" ko'rsatiladi (soxta xizmat qo'shilmaydi).
class PayCategory {
  const PayCategory({required this.id, required this.name, required this.icon});

  final String id;
  final String name;
  final IconData icon;
}

const List<PayCategory> kPayCategories = [
  PayCategory(id: 'mobile', name: 'Mobil operatorlar', icon: Icons.signal_cellular_alt),
  PayCategory(id: 'gov', name: 'Davlat xizmatlari va DYHXX (GAI)', icon: Icons.account_balance),
  PayCategory(id: 'bills', name: "Kommunal to'lovlar", icon: Icons.bolt),
  PayCategory(id: 'microcredit', name: "Mikrokredit va muddatli to'lovlar", icon: Icons.percent),
  PayCategory(id: 'bankloans', name: "Bank kreditlarini so'ndirish", icon: Icons.credit_score),
  PayCategory(id: 'isp', name: 'Internet provayderlar', icon: Icons.wifi),
  PayCategory(id: 'taxes', name: 'Soliqlar', icon: Icons.request_quote),
  PayCategory(id: 'webservices', name: 'Internet xizmatlar', icon: Icons.language),
  PayCategory(id: 'tv', name: 'Televidenie', icon: Icons.tv),
  PayCategory(id: 'hosting', name: 'Xosting va domenlar', icon: Icons.cloud),
  PayCategory(id: 'telephony', name: 'Telefoniya', icon: Icons.phone),
  PayCategory(id: 'leisure', name: "Ko'ngil ochar va dam olish", icon: Icons.sports_esports),
  PayCategory(id: 'insurance', name: "Sug'urta", icon: Icons.verified_user),
  PayCategory(id: 'charity', name: 'Xayriya', icon: Icons.favorite),
  PayCategory(id: 'education', name: "Ta'lim", icon: Icons.menu_book),
  PayCategory(id: 'health', name: "Sog'liq", icon: Icons.medical_services),
  PayCategory(id: 'transport', name: 'Transport va avtoturargoh', icon: Icons.directions_bus),
  PayCategory(id: 'taxi', name: 'Taksi', icon: Icons.local_taxi),
  PayCategory(id: 'realestate', name: "Ko'chmas mulk", icon: Icons.apartment),
  PayCategory(id: 'account', name: "Hisob raqamiga to'lov", icon: Icons.description),
];

PayCategory payCategoryById(String id) => kPayCategories.firstWhere((c) => c.id == id);

/// Hudud (viloyat). Elektr ETK ro'yxati hududga bog'langan.
class Region {
  const Region(this.id, this.name);

  final String id;
  final String name;
}

const List<Region> kRegions = [
  Region('tashkent', 'Toshkent'),
  Region('tashkent_region', 'Toshkent viloyati'),
  Region('andijan', 'Andijon'),
  Region('bukhara', 'Buxoro'),
  Region('jizzakh', 'Jizzax'),
  Region('kashkadarya', 'Qashqadaryo'),
  Region('navoi', 'Navoiy'),
  Region('namangan', 'Namangan'),
  Region('karakalpakstan', "Qoraqalpog'iston Respublikasi"),
  Region('samarkand', 'Samarqand'),
  Region('surkhandarya', 'Surxondaryo'),
  Region('syrdarya', 'Sirdaryo'),
  Region('fergana', "Farg'ona"),
  Region('khorezm', 'Xorazm'),
];

/// Elektr ta'minoti tumanlari (ETK). Kod abonent hisob raqamining boshiga qo'shiladi.
class ElectricityOffice {
  const ElectricityOffice(this.code, this.name, this.regionId);

  final String code;
  final String name;
  final String regionId;

  String get label => '$code - $name';
}

const int kOfficeCodeLength = 5;

/// TEST MA'LUMOTI: faqat Samarqand hududining bir qismi (rasmda ko'ringanicha). To'liq va rasmiy ro'yxat
/// provayderdan olinadi; boshqa hududlar uchun ETK ro'yxati hozircha yo'q ("Tez orada" ko'rsatiladi).
const List<ElectricityOffice> kElectricityOffices = [
  ElectricityOffice('18203', 'Oqdaryo ETK', 'samarkand'),
  ElectricityOffice('18206', "Bulung'ur ETK", 'samarkand'),
  ElectricityOffice('18209', 'Jomboy ETK', 'samarkand'),
  ElectricityOffice('18212', 'Ishtixon ETK', 'samarkand'),
  ElectricityOffice('18214', 'Qoradaryo ETK', 'samarkand'),
  ElectricityOffice('18215', "Kattaqo'rg'on ETK", 'samarkand'),
  ElectricityOffice('18216', "Qo'shrabod ETK", 'samarkand'),
  ElectricityOffice('18218', 'Narpay ETK', 'samarkand'),
  ElectricityOffice('18224', 'Payariq ETK', 'samarkand'),
  ElectricityOffice('18226', 'Chelek ETK', 'samarkand'),
  ElectricityOffice('18227', "Pastdarg'om ETK", 'samarkand'),
  ElectricityOffice('18228', 'Guzalkent ETK', 'samarkand'),
  ElectricityOffice('18230', 'Paxtachi ETK', 'samarkand'),
  ElectricityOffice('18233', "Do'stlik ETK", 'samarkand'),
  ElectricityOffice('18234', 'Zarafshon ETK', 'samarkand'),
  ElectricityOffice('18235', 'Nurobod ETK', 'samarkand'),
];

List<ElectricityOffice> officesOf(String regionId) =>
    kElectricityOffices.where((o) => o.regionId == regionId).toList();

ElectricityOffice? officeByCode(String code) =>
    kElectricityOffices.where((o) => o.code == code).firstOrNull;

class PayService {
  const PayService({
    required this.id,
    required this.name,
    required this.categoryId,
    required this.icon,
    required this.accountLabel,
    required this.accountMin,
    required this.accountMax,
    this.regional = false,
  });

  final String id;
  final String name;
  final String categoryId;
  final IconData icon;

  /// Maydon nomi: "Telefon raqami", "Abonent hisob-raqami".
  final String accountLabel;

  /// Raqamlar soni oralig'i. Telefon uchun 9 (+998 siz). [regional] bo'lsa — ETK kodidan KEYINGI qism.
  final int accountMin;
  final int accountMax;

  /// `true` — hudud va ETK tanlanadi, hisob raqami = ETK kodi + abonent raqami.
  final bool regional;

  /// Mock qoidasi. Haqiqiy qoidalarni provayder hujjati belgilaydi; server ham qayta tekshiradi.
  bool isAccountValid(String account) {
    final d = account.replaceAll(RegExp(r'\D'), '');
    if (regional) {
      if (d.length <= kOfficeCodeLength) return false;
      if (officeByCode(d.substring(0, kOfficeCodeLength)) == null) return false;
      final rest = d.length - kOfficeCodeLength;
      return rest >= accountMin && rest <= accountMax;
    }
    return d.length >= accountMin && d.length <= accountMax;
  }
}

/// Katalog hozircha ilova ichida (TEST). Operator/xizmat NOMLARI ko'rsatish uchun; ular bilan haqiqiy
/// integratsiya yo'q — shartnoma va API kalitlari kerak. Haqiqiy katalog keyin serverdan keladi.
const List<PayService> kPayServices = [
  // Mobil operatorlar
  PayService(id: 'uzmobile', name: 'Uzmobile (GSM)', categoryId: 'mobile', icon: Icons.phone_android, accountLabel: 'Telefon raqami', accountMin: 9, accountMax: 9),
  PayService(id: 'beeline', name: 'Beeline', categoryId: 'mobile', icon: Icons.phone_android, accountLabel: 'Telefon raqami', accountMin: 9, accountMax: 9),
  PayService(id: 'ucell', name: 'Ucell', categoryId: 'mobile', icon: Icons.phone_android, accountLabel: 'Telefon raqami', accountMin: 9, accountMax: 9),
  PayService(id: 'mobiuz', name: 'Mobiuz', categoryId: 'mobile', icon: Icons.phone_android, accountLabel: 'Telefon raqami', accountMin: 9, accountMax: 9),
  PayService(id: 'perfectum', name: 'Perfectum', categoryId: 'mobile', icon: Icons.phone_android, accountLabel: 'Telefon raqami', accountMin: 9, accountMax: 9),
  PayService(id: 'oq', name: 'OQ', categoryId: 'mobile', icon: Icons.phone_android, accountLabel: 'Telefon raqami', accountMin: 9, accountMax: 9),
  PayService(id: 'perfectum5g', name: 'Perfectum 5G SA', categoryId: 'mobile', icon: Icons.phone_android, accountLabel: 'Telefon raqami', accountMin: 9, accountMax: 9),

  // Kommunal
  PayService(id: 'electricity', name: 'Elektroenergiya (Jismoniy shaxs)', categoryId: 'bills', icon: Icons.bolt, accountLabel: 'Abonent hisob-raqami', accountMin: 6, accountMax: 12, regional: true),
  PayService(id: 'electricity_penalty', name: 'Elektroenergiya (penya)', categoryId: 'bills', icon: Icons.bolt, accountLabel: 'Abonent hisob-raqami', accountMin: 6, accountMax: 12, regional: true),
  PayService(id: 'electricity_legal', name: 'Elektroenergiya (Yuridik shaxs)', categoryId: 'bills', icon: Icons.bolt, accountLabel: 'Abonent hisob-raqami', accountMin: 6, accountMax: 12, regional: true),
  PayService(id: 'gas', name: 'Gaz (Jismoniy shaxs)', categoryId: 'bills', icon: Icons.local_fire_department, accountLabel: 'Hisob raqami', accountMin: 6, accountMax: 12),
  PayService(id: 'gas_legal', name: 'Gaz (Yuridik shaxs)', categoryId: 'bills', icon: Icons.local_fire_department, accountLabel: 'Hisob raqami', accountMin: 6, accountMax: 12),
  PayService(id: 'water', name: "Suv ta'minoti", categoryId: 'bills', icon: Icons.water_drop, accountLabel: 'Hisob raqami', accountMin: 6, accountMax: 12),
];

List<PayService> servicesOf(String categoryId) =>
    kPayServices.where((s) => s.categoryId == categoryId).toList();

PayService? payServiceById(String id) => kPayServices.where((s) => s.id == id).firstOrNull;

String _norm(String s) =>
    s.toLowerCase().replaceAll(RegExp("[\u2018\u2019\u02BB\u02BC`\u00B4]"), "'").trim();

class CatalogSearchResult {
  const CatalogSearchResult({required this.categories, required this.services});

  final List<PayCategory> categories;
  final List<PayService> services;
}

/// Kategoriya va xizmat nomi bo'yicha qidiruv (katta-kichik harf va apostrof turlariga e'tiborsiz).
/// Bo'sh so'rov — hamma kategoriyalar, xizmatlarsiz.
CatalogSearchResult searchCatalog(String query) {
  final q = _norm(query);
  if (q.isEmpty) return const CatalogSearchResult(categories: kPayCategories, services: []);
  return CatalogSearchResult(
    categories: kPayCategories.where((c) => _norm(c.name).contains(q)).toList(),
    services: kPayServices.where((s) => _norm(s.name).contains(q)).toList(),
  );
}

/// Tanlangan (saqlangan) to'lov shabloni: xizmat + hisob raqami + oxirgi summa.
class FavoritePayment {
  const FavoritePayment({
    required this.id,
    required this.serviceId,
    required this.account,
    required this.amountTiyin,
  });

  final String id;
  final String serviceId;
  final String account;
  final int amountTiyin;
}

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
