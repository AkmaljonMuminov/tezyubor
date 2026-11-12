import 'package:flutter/material.dart';

import '../core/assets.dart';
import '../core/format.dart';
import '../core/money.dart';
import '../core/theme/app_colors.dart';
import '../features/wallet/domain/wallet_models.dart';
import 'service_icon.dart';

class TxnTile extends StatelessWidget {
  const TxnTile(this.txn, {super.key});

  final Txn txn;

  String get _icon {
    switch (txn.type) {
      case TxnType.transfer:
        return AppAssets.icTransfer;
      case TxnType.payment:
        return AppAssets.icBills;
      case TxnType.topUp:
        return AppAssets.icCard;
    }
  }

  @override
  Widget build(BuildContext context) {
    final failed = txn.status == TxnStatus.failed;
    final incoming = txn.amountTiyin > 0;
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: ServiceIcon(_icon, size: 44),
      title: Text(txn.title, maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: Text(formatDateTime(txn.createdAt)),
      trailing: Text(
        failed ? 'Bekor' : formatSom(txn.amountTiyin, signed: true),
        style: TextStyle(
          fontWeight: FontWeight.w700,
          color: failed
              ? AppColors.error
              : (incoming ? AppColors.primaryDark : AppColors.text),
        ),
      ),
    );
  }
}
