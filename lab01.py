import getpass
import math
import re

COMMON_PASSWORDS = {
    "password", "123456", "12345678", "qwerty", "abc123", "111111",
    "letmein", "admin", "login", "passw0rd", "qwerty123", "1234567890", "000000",
}


def calc_entropy(pwd):
    entropy = 0
    if re.search(r"[a-zа-яё]", pwd):
        entropy += 32
    if re.search(r"[A-ZА-ЯЁ]", pwd):
        entropy += 32
    if re.search(r"\d", pwd):
        entropy += 10
    if re.search(r"[^a-zA-Zа-яёА-ЯЁ\d]", pwd):
        entropy += 30
    return len(pwd) * math.log2(entropy) if entropy else 0.0


def analyse(pwd):
    length = len(pwd)
    has_lower = bool(re.search(r"[a-zа-яё]", pwd))
    has_upper = bool(re.search(r"[A-ZА-ЯЁ]", pwd))
    has_digit = bool(re.search(r"\d", pwd))
    has_special = bool(re.search(r"[^a-zA-Zа-яёА-ЯЁ\d]", pwd))
    is_common = pwd.lower() in COMMON_PASSWORDS
    entropy = calc_entropy(pwd)
    classes = sum([has_lower, has_upper, has_digit, has_special])

    if is_common or length < 6:
        score, verdict = 1, "Очень слабый"
    elif entropy < 28:
        score, verdict = 2, "Слабый"
    elif entropy < 50:
        score, verdict = 3, "Средний"
    elif entropy < 72:
        score, verdict = 4, "Хороший"
    else:
        score, verdict = 5, "Надёжный"

    return {
        "length": length,
        "has_lower": has_lower,
        "has_upper": has_upper,
        "has_digit": has_digit,
        "has_special": has_special,
        "classes": classes,
        "entropy": entropy,
        "is_common": is_common,
        "score": score,
        "verdict": verdict,
    }


def recommendations(r):
    tips = []
    if r["is_common"]:
        tips.append("Пароль слишком распространен - смените немедленно.")
    if r["length"] < 12:
        tips.append("Увеличьте длину до 12 символов и более.")
    if not r["has_upper"]:
        tips.append("Добавьте заглавные буквы.")
    if not r["has_digit"]:
        tips.append("Добавьте цифры.")
    if not r["has_special"]:
        tips.append("Добавьте спецсимволы (!@#$% и др.).")
    return tips


def main():
    try:
        pwd = getpass.getpass("Введите пароль (скрыто): ")
    except Exception:
        pwd = input("Введите пароль: ")

    if not pwd:
        print("Пароль не введён.")
        return

    r = analyse(pwd)

    print(f"\nДлина: {r['length']} символов")
    print(f"Состав: строчные - {'да' if r['has_lower'] else 'нет'}, "
          f"заглавные - {'да' if r['has_upper'] else 'нет'}, "
          f"цифры - {'да' if r['has_digit'] else 'нет'}, "
          f"спецсимволы - {'да' if r['has_special'] else 'нет'}")
    print(f"Энтропия: {r['entropy']:.1f} бит")
    print(f"\nОценка: {r['score']} / 5 - {r['verdict']}")

    tips = recommendations(r)
    if tips:
        print("\nРекомендации:")
        for i, t in enumerate(tips, 1):
            print(f"  {i}. {t}")


if __name__ == "__main__":
    main()
