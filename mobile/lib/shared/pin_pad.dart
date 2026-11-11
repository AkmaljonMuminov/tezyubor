import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';

/// PIN nuqtalari + raqamli klaviatura. Kiritish to'lgach `onCompleted` chaqiriladi va maydon tozalanadi.
class PinPad extends StatefulWidget {
  const PinPad({super.key, required this.onCompleted, this.errorText, this.length = 4});

  final ValueChanged<String> onCompleted;
  final String? errorText;
  final int length;

  @override
  State<PinPad> createState() => _PinPadState();
}

class _PinPadState extends State<PinPad> {
  String _value = '';

  void _tap(String digit) {
    if (_value.length >= widget.length) return;
    setState(() => _value += digit);
    if (_value.length == widget.length) {
      final completed = _value;
      widget.onCompleted(completed);
      Future<void>.delayed(const Duration(milliseconds: 150), () {
        if (mounted) setState(() => _value = '');
      });
    }
  }

  void _back() {
    if (_value.isEmpty) return;
    setState(() => _value = _value.substring(0, _value.length - 1));
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            for (var i = 0; i < widget.length; i++)
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 8),
                width: 16,
                height: 16,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: i < _value.length ? AppColors.primary : AppColors.tint,
                ),
              ),
          ],
        ),
        SizedBox(
          height: 28,
          child: widget.errorText == null
              ? null
              : Center(
                  child: Text(widget.errorText!,
                      style: const TextStyle(color: AppColors.error, fontSize: 13)),
                ),
        ),
        const SizedBox(height: 16),
        for (final row in const [
          ['1', '2', '3'],
          ['4', '5', '6'],
          ['7', '8', '9'],
          ['', '0', '<'],
        ])
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              for (final key in row) _key(key),
            ],
          ),
      ],
    );
  }

  Widget _key(String key) {
    const size = 84.0;
    if (key.isEmpty) return const SizedBox(width: size, height: size);
    return SizedBox(
      width: size,
      height: size,
      child: InkResponse(
        onTap: key == '<' ? _back : () => _tap(key),
        radius: 40,
        child: Center(
          child: key == '<'
              ? const Icon(Icons.backspace_outlined, color: AppColors.muted)
              : Text(key, style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w600)),
        ),
      ),
    );
  }
}
