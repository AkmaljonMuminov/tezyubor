import '../../../core/brand.dart';
import '../../../core/format.dart';
import '../../../core/money.dart';
import 'wallet_models.dart';

/// Chekdagi bitta qator.
class ReceiptLine {
  const ReceiptLine(this.label, this.value);

  final String label;
  final String value;
}

/// Operatsiya ma'lumotlaridan chek qatorlarini tuzadi. Faqat mavjud ma'lumot ko'rsatiladi (to'qib chiqarilmaydi).
List<ReceiptLine> buildReceiptLines(Txn t) {
  final lines = <ReceiptLine>[
    ReceiptLine('Holat', t.status == TxnStatus.succeeded ? 'Muvaffaqiyatli' : 'Bekor qilingan'),
  ];

  switch (t.type) {
    case TxnType.payment:
      lines.add(ReceiptLine('Xizmat', t.title));
      final service = t.serviceId == null ? null : payServiceById(t.serviceId!);
      final account = t.account;
      if (account != null && account.isNotEmpty) {
        if (service != null && service.regional && account.length > kOfficeCodeLength) {
          final office = officeByCode(account.substring(0, kOfficeCodeLength));
          if (office != null) lines.add(ReceiptLine("Elektr ta'minoti tumani", office.label));
          lines.add(ReceiptLine(service.accountLabel, account.substring(kOfficeCodeLength)));
        } else {
          final isPhone = service != null && service.categoryId == 'mobile';
          lines.add(ReceiptLine(
            service?.accountLabel ?? 'Hisob raqami',
            isPhone ? formatPhone9(account) : account,
          ));
        }
      }
      if (t.fromCard != null) lines.add(ReceiptLine('Karta', t.fromCard!));
    case TxnType.transfer:
      if (t.toCard != null) lines.add(ReceiptLine('Qabul qiluvchi karta', t.toCard!));
      if (t.fromCard != null) lines.add(ReceiptLine('Qaysi kartadan', t.fromCard!));
    case TxnType.ownTransfer:
      if (t.fromCard != null) lines.add(ReceiptLine('Qaysi kartadan', t.fromCard!));
      if (t.toCard != null) lines.add(ReceiptLine('Qaysi kartaga', t.toCard!));
    case TxnType.topUp:
      lines.add(ReceiptLine('Operatsiya', t.title));
  }

  final outgoing = t.amountTiyin < 0;
  lines.add(ReceiptLine('Summa', formatSom(t.amountTiyin.abs())));
  if (outgoing) {
    lines.add(ReceiptLine('Komissiya', formatSom(t.feeTiyin)));
    lines.add(ReceiptLine('Jami yechildi', formatSom(t.totalTiyin.abs())));
  }
  lines.add(ReceiptLine('Sana', formatDateTime(t.createdAt)));
  lines.add(ReceiptLine('Operatsiya raqami', t.id));
  return lines;
}

/// Nusxalash uchun chek matni. [test] bo'lsa, chek haqiqiy emasligi ochiq yoziladi.
String buildReceiptText(Txn t, {required bool test}) {
  final b = StringBuffer()..writeln('${AppBrand.name} — chek');
  if (test) b.writeln("TEST CHEK — haqiqiy to'lov emas");
  b.writeln();
  for (final l in buildReceiptLines(t)) {
    b.writeln('${l.label}: ${l.value}');
  }
  return b.toString().trimRight();
}
