/// Matnlar. Hozircha faqat o'zbekcha. Ru/En qo'shish: `flutter gen-l10n` ga o'tkaziladi (keyingi bosqich).
class Strings {
  const Strings._();

  static const testMode = "TEST REJIMI — haqiqiy SMS va to'lov yo'q";
  static const phoneTitle = 'Telefon raqamingiz';
  static const phoneHint = 'XX XXX XX XX';
  static const phoneError = "Telefon raqami noto'g'ri";
  static const next = 'Davom etish';
  static const otpTitle = 'Tasdiqlash kodi';
  static const otpSubtitle = 'SMS orqali yuborilgan 6 xonali kodni kiriting';
  static const otpWrong = "Kod noto'g'ri";
  static const pinCreateTitle = 'PIN-kod yarating';
  static const pinConfirmTitle = 'PIN-kodni takrorlang';
  static const pinLoginTitle = 'PIN-kodni kiriting';
  static const pinWeak = "PIN juda oddiy (masalan 1111 yoki 1234). Boshqasini tanlang";
  static const pinMismatch = 'PIN-kodlar mos kelmadi, qaytadan urinib ko\'ring';
  static const pinWrong = "PIN-kod noto'g'ri";
  static const genericError = "Xatolik yuz berdi. Qayta urinib ko'ring";

  // Bosh sahifa
  static const totalBalance = 'Umumiy balans';
  static const myCards = 'Kartalarim';
  static const recent = "So'nggi operatsiyalar";
  static const all = 'Hammasi';
  static const noOperations = "Hozircha operatsiyalar yo'q";
  static const actionTransfer = "O'tkazma";
  static const actionMobile = 'Mobil aloqa';
  static const actionBills = "Kommunal";
  static const actionHistory = 'Tarix';
  static const history = 'Operatsiyalar tarixi';
  static const retry = 'Qayta urinish';

  // O'tkazma va to'lov
  static const transferTitle = "Kartaga o'tkazma";
  static const payMobileTitle = "Mobil aloqa to'lovi";
  static const payBillsTitle = "Kommunal to'lovlar";
  static const fromCard = 'Qaysi kartadan';
  static const toCard = 'Qabul qiluvchi karta raqami';
  static const cardHint = '8600 XXXX XXXX XXXX';
  static const cardError = "Karta raqami noto'g'ri (Uzcard 8600 yoki Humo 9860)";
  static const amount = "Summa (so'm)";
  static const amountError = "Summa 1 000 dan 10 000 000 so'mgacha bo'lishi kerak";
  static const accountError = "Raqam noto'g'ri";
  static const amountLabel = 'Summa';
  static const fee = 'Komissiya';
  static const total = 'Jami yechiladi';
  static const confirm = 'Tasdiqlash';
  static const cancel = 'Bekor qilish';
  static const success = 'Muvaffaqiyatli bajarildi';
  static const done = 'Tayyor';
  static const operationId = 'Operatsiya raqami';
  static const noCards = "Kartalar topilmadi";

  // Navigatsiya
  static const navHome = 'Asosiy';
  static const navTransfers = "O'tkazmalar";
  static const navPay = "To'lov";
  static const navMonitoring = 'Monitoring';
  static const navProfile = 'Profil';

  // O'tkazmalar markazi
  static const transfersTitle = "O'tkazmalar";
  static const transferToCard = "Kartaga o'tkazma";
  static const transferOwnTitle = "Kartalarim orasida";
  static const recentRecipients = "So'nggi qabul qiluvchilar";
  static const noRecipients = "Hozircha o'tkazmalar yo'q";
  static const needTwoCards = "Kartalar orasida o'tkazish uchun kamida 2 ta karta kerak";
  static const fromCardOwn = 'Qaysi kartadan';
  static const toCardOwn = 'Qaysi kartaga';

  // To'lov markazi
  static const payTitle = "To'lovlar";

  // Monitoring
  static const monitoringTitle = 'Monitoring';
  static const incomes = 'Tushumlar';
  static const expenses = 'Xarajatlar';
  static const filterAll = 'Hammasi';
  static const thisMonth = 'Shu oy';

  // Profil
  static const profileTitle = 'Profil';
  static const hideBalance = 'Balansni yashirish';
  static const language = 'Til';
  static const languageValue = "O'zbek";
  static const logout = 'Chiqish';
  static const logoutConfirm = "Ilovadan chiqasizmi? Qayta kirish uchun telefon raqami va SMS kod kerak bo'ladi";
  static const version = 'Versiya';
  static const hiddenAmount = '\u2022\u2022\u2022\u2022\u2022\u2022';
}
