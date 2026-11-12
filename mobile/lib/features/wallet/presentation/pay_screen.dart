import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/ids.dart';
import '../../../core/l10n/strings.dart';
import '../../../core/money.dart';
import '../../../core/router.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/validators.dart';
import '../../../shared/card_picker.dart';
import '../../../shared/confirm_sheet.dart';
import '../../../shared/icon_badge.dart';
import '../../../shared/picker_field.dart';
import '../../../shared/test_mode_banner.dart';
import '../../../shared/txn_tile.dart';
import '../data/wallet_repository.dart';
import '../domain/wallet_models.dart';

/// To'lov formasiga beriladigan argumentlar. [account]/[amountTiyin] — oldindan to'ldirish
/// (tanlangan to'lovdan yoki mobil bo'limdagi telefon qatoridan).
class PayFormArgs {
  const PayFormArgs({required this.service, this.account, this.amountTiyin});

  final PayService service;
  final String? account;
  final int? amountTiyin;
}

/// Kategoriya ichidagi xizmatlar: qidiruv, (mobil uchun) telefon qatori. Xizmat bo'lmasa — "Tez orada".
class PayScreen extends StatefulWidget {
  const PayScreen({super.key, required this.category});

  final PayCategory category;

  @override
  State<PayScreen> createState() => _PayScreenState();
}

class _PayScreenState extends State<PayScreen> {
  final _search = TextEditingController();
  final _phone = TextEditingController();
  String _query = '';
  String? _phoneError;

  bool get _isMobile => widget.category.id == 'mobile';

  @override
  void dispose() {
    _search.dispose();
    _phone.dispose();
    super.dispose();
  }

  bool _matches(PayService s) {
    final q = _query.trim();
    if (q.isEmpty) return true;
    return searchCatalog(q).services.any((x) => x.id == s.id);
  }

  void _open(PayService s) {
    final digits = _phone.text.replaceAll(RegExp(r'\D'), '');
    context.push(
      Routes.payForm,
      extra: PayFormArgs(service: s, account: _isMobile && digits.isNotEmpty ? digits : null),
    );
  }

  /// Operator avtomatik aniqlanmaydi (raqam ko'chirilgan bo'lishi mumkin) — foydalanuvchi tanlaydi.
  Future<void> _payByPhone(List<PayService> services) async {
    final digits = _phone.text.replaceAll(RegExp(r'\D'), '');
    if (digits.length != 9) {
      setState(() => _phoneError = Strings.phoneError);
      return;
    }
    setState(() => _phoneError = null);
    final id = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(24, 0, 24, 8),
              child: Text(Strings.chooseOperator, style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18)),
            ),
            for (final s in services)
              ListTile(
                leading: IconBadge(s.icon, size: 40),
                title: Text(s.name),
                onTap: () => Navigator.of(ctx).pop(s.id),
              ),
          ],
        ),
      ),
    );
    if (id == null || !mounted) return;
    final s = payServiceById(id);
    if (s != null) _open(s);
  }

  @override
  Widget build(BuildContext context) {
    final all = servicesOf(widget.category.id);
    final services = all.where(_matches).toList();

    return Scaffold(
      appBar: AppBar(title: Text(widget.category.name)),
      body: SafeArea(
        child: Column(
          children: [
            const TestModeBanner(),
            Expanded(
              child: all.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(32),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(widget.category.icon, size: 56, color: AppColors.muted),
                            const SizedBox(height: 16),
                            Text(Strings.soon, style: Theme.of(context).textTheme.titleLarge),
                            const SizedBox(height: 8),
                            const Text(Strings.soonBody, textAlign: TextAlign.center),
                          ],
                        ),
                      ),
                    )
                  : ListView(
                      padding: const EdgeInsets.all(20),
                      children: [
                        TextField(
                          controller: _search,
                          decoration: InputDecoration(
                            hintText: Strings.searchHint,
                            prefixIcon: const Icon(Icons.search),
                            suffixIcon: _query.isEmpty
                                ? null
                                : IconButton(
                                    icon: const Icon(Icons.close),
                                    onPressed: () {
                                      _search.clear();
                                      setState(() => _query = '');
                                    },
                                  ),
                          ),
                          onChanged: (v) => setState(() => _query = v),
                        ),
                        if (_isMobile) ...[
                          const SizedBox(height: 12),
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                child: TextField(
                                  controller: _phone,
                                  keyboardType: TextInputType.phone,
                                  inputFormatters: [
                                    FilteringTextInputFormatter.digitsOnly,
                                    LengthLimitingTextInputFormatter(9),
                                  ],
                                  decoration: InputDecoration(
                                    prefixText: '+998 ',
                                    hintText: Strings.phoneHint,
                                    errorText: _phoneError,
                                  ),
                                  onChanged: (_) => setState(() => _phoneError = null),
                                ),
                              ),
                              const SizedBox(width: 10),
                              SizedBox(
                                width: 120,
                                height: 56,
                                child: FilledButton(
                                  onPressed: () => _payByPhone(all),
                                  child: const Text(Strings.pay),
                                ),
                              ),
                            ],
                          ),
                        ],
                        const SizedBox(height: 16),
                        if (services.isEmpty)
                          const Padding(
                            padding: EdgeInsets.symmetric(vertical: 32),
                            child: Center(child: Text(Strings.nothingFound)),
                          ),
                        for (final s in services)
                          Card(
                            elevation: 0,
                            margin: const EdgeInsets.only(bottom: 10),
                            child: ListTile(
                              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                              leading: IconBadge(s.icon, size: 48),
                              title: Text(s.name, style: const TextStyle(fontWeight: FontWeight.w600)),
                              onTap: () => _open(s),
                            ),
                          ),
                      ],
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Tanlangan xizmat uchun to'lov formasi.
class PayFormScreen extends ConsumerStatefulWidget {
  const PayFormScreen({super.key, required this.args});

  final PayFormArgs args;

  @override
  ConsumerState<PayFormScreen> createState() => _PayFormScreenState();
}

class _PayFormScreenState extends ConsumerState<PayFormScreen> {
  final _accountCtrl = TextEditingController();
  final _amountCtrl = TextEditingController();
  String? _fromId;
  String? _regionId;
  String? _officeCode;
  bool _saveFavorite = false;
  String? _regionError;
  String? _officeError;
  String? _accountError;
  String? _amountError;
  String? _error;
  bool _loading = false;
  String _key = newIdempotencyKey();

  PayService get _service => widget.args.service;

  @override
  void initState() {
    super.initState();
    final account = widget.args.account ?? '';
    if (_service.regional && account.length > kOfficeCodeLength) {
      final office = officeByCode(account.substring(0, kOfficeCodeLength));
      if (office != null) {
        _regionId = office.regionId;
        _officeCode = office.code;
        _accountCtrl.text = account.substring(kOfficeCodeLength);
      }
    } else if (!_service.regional) {
      _accountCtrl.text = account;
    }
    final amount = widget.args.amountTiyin;
    if (amount != null) _amountCtrl.text = (amount ~/ 100).toString();
  }

  @override
  void dispose() {
    _accountCtrl.dispose();
    _amountCtrl.dispose();
    super.dispose();
  }

  void _inputChanged() {
    _key = newIdempotencyKey();
    if (_error != null) setState(() => _error = null);
  }

  /// Serverga yuboriladigan to'liq hisob raqami (regional bo'lsa ETK kodi + abonent raqami).
  String _fullAccount() {
    final d = _accountCtrl.text.replaceAll(RegExp(r'\D'), '');
    return _service.regional ? '${_officeCode ?? ''}$d' : d;
  }

  Future<void> _submit(List<CardInfo> cards) async {
    final s = _service;
    final account = _fullAccount();
    final amount = parseAmountTiyin(_amountCtrl.text);
    final regionOk = !s.regional || _regionId != null;
    final officeOk = !s.regional || _officeCode != null;
    final accountOk = regionOk && officeOk && s.isAccountValid(account);

    setState(() {
      _regionError = regionOk ? null : Strings.regionError;
      _officeError = officeOk ? null : Strings.officeError;
      _accountError = (regionOk && officeOk && !accountOk) ? Strings.accountError : null;
      _amountError = amount == null ? Strings.amountError : null;
      _error = null;
    });
    final fromId = _fromId ?? (cards.isNotEmpty ? cards.first.id : null);
    if (!accountOk || amount == null || fromId == null) return;

    final ok = await showConfirmSheet(
      context,
      title: s.name,
      rows: [
        MapEntry(s.accountLabel, account),
        MapEntry(Strings.amountLabel, formatSom(amount)),
        MapEntry(Strings.fee, formatSom(0)),
        MapEntry(Strings.total, formatSom(amount)),
      ],
    );
    if (!ok || !mounted) return;

    setState(() => _loading = true);
    try {
      final txn = await ref.read(walletRepositoryProvider).pay(
            fromCardId: fromId,
            serviceId: s.id,
            account: account,
            amountTiyin: amount,
            idempotencyKey: _key,
          );
      ref.invalidate(cardsProvider);
      ref.invalidate(transactionsProvider);
      if (_saveFavorite) {
        // To'lov allaqachon bajarilgan; shablonni saqlash muvaffaqiyatsiz bo'lsa ham natijani ko'rsatamiz.
        try {
          await ref.read(walletRepositoryProvider).addFavorite(
                serviceId: s.id,
                account: account,
                amountTiyin: amount,
              );
        } catch (_) {
          // e'tiborsiz
        } finally {
          ref.invalidate(favoritesProvider);
        }
      }
      if (!mounted) return;
      context.go(Routes.result, extra: txn);
    } on WalletException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (_) {
      if (mounted) setState(() => _error = Strings.genericError);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _showHistory() {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => Consumer(
        builder: (ctx, ref, _) {
          final txns = ref.watch(transactionsProvider);
          return SafeArea(
            child: ConstrainedBox(
              constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(ctx).height * 0.7),
              child: txns.when(
                loading: () => const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: CircularProgressIndicator()),
                ),
                error: (_, __) => const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: Text(Strings.genericError)),
                ),
                data: (all) {
                  final list = all.where((t) => t.serviceId == _service.id).toList();
                  return ListView(
                    shrinkWrap: true,
                    padding: const EdgeInsets.fromLTRB(24, 0, 24, 16),
                    children: [
                      Text(Strings.serviceHistory, style: Theme.of(ctx).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      if (list.isEmpty)
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 24),
                          child: Center(child: Text(Strings.noServiceHistory)),
                        )
                      else
                        for (final t in list)
                          TxnTile(
                            t,
                            // Avval oynani yopamiz, keyin chekni ochamiz.
                            onTap: () {
                              Navigator.of(ctx).pop();
                              context.push(Routes.receipt, extra: t);
                            },
                          ),
                    ],
                  );
                },
              ),
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final s = _service;
    final cardsAsync = ref.watch(cardsProvider);
    final offices = _regionId == null ? const <ElectricityOffice>[] : officesOf(_regionId!);

    return Scaffold(
      appBar: AppBar(
        title: Text(s.name),
        actions: [
          IconButton(
            tooltip: Strings.serviceHistory,
            icon: const Icon(Icons.history),
            onPressed: _showHistory,
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            const TestModeBanner(),
            Expanded(
              child: cardsAsync.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (_, __) => const Center(child: Text(Strings.genericError)),
                data: (cards) {
                  final selected = _fromId ?? (cards.isNotEmpty ? cards.first.id : null);
                  return ListView(
                    padding: const EdgeInsets.all(20),
                    children: [
                      if (s.regional) ...[
                        PickerField(
                          label: Strings.region,
                          placeholder: Strings.regionHint,
                          options: [for (final r in kRegions) MapEntry(r.id, r.name)],
                          selectedKey: _regionId,
                          errorText: _regionError,
                          enabled: !_loading,
                          onSelected: (id) {
                            setState(() {
                              if (id != _regionId) _officeCode = null; // boshqa hududning ETK si yaroqsiz
                              _regionId = id;
                              _regionError = null;
                            });
                            _inputChanged();
                          },
                        ),
                        const SizedBox(height: 12),
                        if (_regionId != null && offices.isEmpty)
                          const Padding(
                            padding: EdgeInsets.symmetric(vertical: 8),
                            child: Text(Strings.officesSoon, style: TextStyle(color: AppColors.muted)),
                          )
                        else
                          PickerField(
                            label: Strings.office,
                            placeholder: Strings.officeHint,
                            options: [for (final o in offices) MapEntry(o.code, o.label)],
                            selectedKey: _officeCode,
                            errorText: _officeError,
                            enabled: !_loading && _regionId != null,
                            onSelected: (code) {
                              setState(() {
                                _officeCode = code;
                                _officeError = null;
                              });
                              _inputChanged();
                            },
                          ),
                        const SizedBox(height: 12),
                      ] else ...[
                        const Text(Strings.fromCard),
                        const SizedBox(height: 8),
                        CardPicker(
                          cards: cards,
                          selectedId: selected,
                          onChanged: (id) {
                            setState(() => _fromId = id);
                            _inputChanged();
                          },
                        ),
                        const SizedBox(height: 16),
                      ],
                      TextField(
                        controller: _accountCtrl,
                        enabled: !_loading,
                        keyboardType: TextInputType.number,
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly,
                          LengthLimitingTextInputFormatter(s.accountMax),
                        ],
                        decoration: InputDecoration(
                          labelText: s.accountLabel,
                          hintText: Strings.accountHint,
                          prefixText: s.regional && _officeCode != null ? '$_officeCode  ' : null,
                          errorText: _accountError,
                        ),
                        onChanged: (_) => _inputChanged(),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _amountCtrl,
                        enabled: !_loading,
                        keyboardType: TextInputType.number,
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly,
                          LengthLimitingTextInputFormatter(8),
                        ],
                        decoration: InputDecoration(
                          labelText: Strings.amount,
                          errorText: _amountError,
                        ),
                        onChanged: (_) => _inputChanged(),
                      ),
                      if (s.regional) ...[
                        const SizedBox(height: 16),
                        const Text(Strings.fromCard),
                        const SizedBox(height: 8),
                        CardPicker(
                          cards: cards,
                          selectedId: selected,
                          onChanged: (id) {
                            setState(() => _fromId = id);
                            _inputChanged();
                          },
                        ),
                      ],
                      CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        controlAffinity: ListTileControlAffinity.leading,
                        value: _saveFavorite,
                        onChanged: _loading ? null : (v) => setState(() => _saveFavorite = v ?? false),
                        title: const Text(Strings.saveFavorite),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 4),
                        Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                      ],
                      const SizedBox(height: 16),
                      FilledButton(
                        onPressed: _loading ? null : () => _submit(cards),
                        child: _loading
                            ? const SizedBox(
                                height: 22,
                                width: 22,
                                child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
                              )
                            : const Text(Strings.next),
                      ),
                    ],
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
