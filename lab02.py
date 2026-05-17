"""
Лабораторная работа №2: Кэш на основе алгоритма 2Q

Алгоритм 2Q (Two Queue) - это улучшенная версия LRU, предназначенная для кэширования
с учетом "одноразовых" запросов. Он использует три структуры:

1. A1in (FIFO очередь) - для новых элементов, которые попали в кэш впервые.
   Размер этой очереди ограничен параметром Kin.
2. A1out (FIFO очередь только ключей, либо пар ключ-значение) - сюда перемещаются
   элементы, вытесненные из A1in. Размер ограничен параметром Kout.
   (В классической реализации хранятся только ключи, но для простоты тестирования
   в данной работе хранятся и значения, чтобы при повторном обращении можно было
   сразу вернуть значение.)
3. Am (LRU очередь) - основная очередь "горячих" элементов, которые были запрошены
   повторно. Размер ограничен параметром Km.

Правила работы:
- При добавлении нового элемента (промах во всех очередях): если A1in не заполнена,
  элемент помещается в ее конец. Если A1in полна, самый старый элемент из A1in
  вытесняется в A1out (при необходимости вытесняя самый старый из A1out), а новый
  элемент добавляется в A1in.
- При обращении к элементу (get):
    * Если элемент находится в Am - он перемещается в конец Am (становится самым
      недавно использованным).
    * Если элемент находится в A1in - он удаляется оттуда и перемещается в Am
      (с возможным вытеснением из Am, если она полна).
    * Если элемент находится в A1out - он удаляется оттуда и перемещается в Am.
- При обновлении значения (set) для существующего ключа считается, что произошло
  обращение к этому ключу, поэтому он ведет себя как get (перемещается в Am,
  если был в A1in или A1out, и обновляется его значение).
- При переполнении Am вытесняется самый старый (LRU) элемент и удаляется навсегда.
- При переполнении A1out вытесняется самый старый элемент и теряется безвозвратно.

Такой подход позволяет защитить кэш от засорения одноразовыми запросами,
которые не будут повторены, сохраняя при этом часто используемые данные.
"""

from collections import OrderedDict
from typing import Optional, Any, Union


class TwoQCache:
    """Кэш, реализующий алгоритм 2Q."""

    def __init__(self, kin: int, kout: int, km: int):
        """
        Инициализация кэша.

        :param kin: максимальный размер очереди A1in (для новых элементов)
        :param kout: максимальный размер очереди A1out (для вытесненных из A1in)
        :param km: максимальный размер основной LRU-очереди Am
        """
        if kin < 0 or kout < 0 or km < 0:
            raise ValueError("Размеры очередей не могут быть отрицательными")
        self.kin = kin
        self.kout = kout
        self.km = km

        # A1in: FIFO очередь (ключ -> значение). Используем OrderedDict,
        # где новые элементы добавляются в конец, а удаление из головы.
        self.ain = OrderedDict()
        self.aout = OrderedDict()
        self.am = OrderedDict()


    def _add_to_am(self, key: Any, value: Any) -> None:
        """
        Добавить или переместить элемент в Am (как самый новый).
        Если Am переполнена, вытесняется LRU-элемент.
        """
        if key in self.am:
            del self.am[key]
        elif len(self.am) >= self.km:
            self.am.popitem(last=False)
        self.am[key] = value

    def _evict_from_ain(self) -> None:
        """
        Вытеснить самый старый элемент из A1in в A1out.
        Если A1out переполнена, вытесняется самый старый из A1out.
        """
        if not self.ain:
            return
        key, value = self.ain.popitem(last=False)
        self._add_to_aout(key, value)

    def _add_to_aout(self, key: Any, value: Any) -> None:
        """
        Добавить пару ключ-значение в A1out (в конец).
        Если A1out переполнена, удаляется самый старый элемент.
        """
        if key in self.aout:
            del self.aout[key]
        elif len(self.aout) >= self.kout:
            self.aout.popitem(last=False)
        self.aout[key] = value

    def _add_to_ain(self, key: Any, value: Any) -> None:
        """
        Добавить элемент в A1in (в конец). Если A1in переполнена,
        предварительно вытесняется самый старый элемент в A1out.
        """
        if key in self.ain:
            self.ain[key] = value
            return
        if len(self.ain) >= self.kin:
            self._evict_from_ain()
        self.ain[key] = value

    def get(self, key: Any) -> Optional[Any]:
        """
        Получить значение по ключу.
        Возвращает значение или None, если ключ не найден.
        """
        if key in self.am:
            value = self.am.pop(key)
            self.am[key] = value
            return value

        if key in self.ain:
            value = self.ain.pop(key)
            self._add_to_am(key, value)
            return value

        if key in self.aout:
            value = self.aout.pop(key)
            self._add_to_am(key, value)
            return value

        return None

    def set(self, key: Any, value: Any) -> None:
        """
        Добавить или обновить пару ключ-значение.
        Если ключ уже существует, он обрабатывается как обращение (перемещается в Am).
        """
        if key in self.am:
            del self.am[key]
            self._add_to_am(key, value)
        elif key in self.ain:
            del self.ain[key]
            self._add_to_am(key, value)
        elif key in self.aout:
            del self.aout[key]
            self._add_to_am(key, value)
        else:
            self._add_to_ain(key, value)

    def show_queues(self) -> None:
        """Вывести текущее состояние всех трех очередей."""
        print("\n=== Состояние кэша ===")
        print(f"A1in (размер {len(self.ain)}/{self.kin}):")
        if self.ain:
            for k, v in self.ain.items():
                print(f"  {k}: {v}")
        else:
            print("  (пусто)")

        print(f"\nA1out (размер {len(self.aout)}/{self.kout}):")
        if self.aout:
            for k, v in self.aout.items():
                print(f"  {k}: {v}")
        else:
            print("  (пусто)")

        print(f"\nAm (размер {len(self.am)}/{self.km}):")
        if self.am:
            for k, v in self.am.items():
                print(f"  {k}: {v}")
        else:
            print("  (пусто)")
        print("=====================\n")


def parse_value(s: str) -> Union[str, int]:
    """Попытаться преобразовать строку в целое число, иначе оставить строкой."""
    try:
        return int(s)
    except ValueError:
        return s


def main():
    print("Добро пожаловать в тестирование кэша 2Q!")
    print( "\n".join([
        "Алгоритм 2Q (Two Queue):",
        " - A1in (FIFO) – для новых элементов",
        " - A1out (FIFO) – для вытесненных из A1in",
        " - Am (LRU) – для часто используемых элементов",
        "Подробное описание приведено в комментариях к коду.\n"
    ]))

    # Ввод размеров секций
    while True:
        try:
            kin = int(input("Введите размер A1in (Kin): "))
            kout = int(input("Введите размер A1out (Kout): "))
            km = int(input("Введите размер Am (Km): "))
            if kin < 0 or kout < 0 or km < 0:
                print("Размеры не могут быть отрицательными. Повторите ввод.")
                continue
            break
        except ValueError:
            print("Ошибка: введите целые числа.")

    cache = TwoQCache(kin, kout, km)
    print("\nКэш создан. Доступные команды:")
    print("  add <ключ> <значение>   – добавить или обновить элемент")
    print("  get <ключ>              – получить значение по ключу")
    print("  show                    – показать состояние всех очередей")
    print("  exit                    – выход")

    while True:
        try:
            cmd = input("\n> ").strip().split()
            if not cmd:
                continue
            command = cmd[0].lower()

            if command == "exit":
                print("До свидания!")
                break

            elif command == "show":
                cache.show_queues()

            elif command == "add":
                if len(cmd) < 3:
                    print("Использование: add <ключ> <значение>")
                    continue
                key = parse_value(cmd[1])
                value = parse_value(" ".join(cmd[2:]))  # значение может содержать пробелы
                cache.set(key, value)
                print(f"Элемент ({key}: {value}) добавлен/обновлен.")

            elif command == "get":
                if len(cmd) != 2:
                    print("Использование: get <ключ>")
                    continue
                key = parse_value(cmd[1])
                val = cache.get(key)
                if val is None:
                    print(f"Ключ '{key}' не найден в кэше.")
                else:
                    print(f"Значение: {val}")

            else:
                print("Неизвестная команда. Доступные: add, get, show, exit")

        except KeyboardInterrupt:
            print("\nВыход по прерыванию.")
            break
        except Exception as e:
            print(f"Произошла ошибка: {e}")


if __name__ == "__main__":
    main()