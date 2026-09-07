"""Пересчёт величин между единицами измерения.

Вся арифметика делается здесь, на Python, а не в голове у модели: модель
только разбирает фразу пользователя и подставляет число и две единицы.

Устройство таблиц:
* _LINEAR — категории, где пересчёт линейный: у каждой единицы есть
  коэффициент к базовой единице категории (метр, килограмм, литр, ...).
  Перевод = value * factor(from) / factor(to).
* _TEMPERATURE — температура, где нужен сдвиг нуля, поэтому у каждой
  шкалы своя пара функций в кельвины и обратно.
"""

from __future__ import annotations

from langchain.tools import tool

# category -> canonical unit -> (коэффициент к базовой единице, синонимы)
_LINEAR: dict[str, dict[str, tuple[float, tuple[str, ...]]]] = {
    "длина": {
        "m": (1.0, ("м", "метр", "метра", "метров", "meter", "meters", "metre")),
        "km": (1000.0, ("км", "километр", "километра", "километров", "kilometer", "kilometre")),
        "dm": (0.1, ("дм", "дециметр", "дециметра", "дециметров")),
        "cm": (0.01, ("см", "сантиметр", "сантиметра", "сантиметров", "centimeter")),
        "mm": (0.001, ("мм", "миллиметр", "миллиметра", "миллиметров", "millimeter")),
        "um": (1e-6, ("мкм", "микрометр", "микрон", "micron", "micrometer")),
        "nm": (1e-9, ("нм", "нанометр", "nanometer")),
        "mi": (1609.344, ("миля", "мили", "миль", "mile", "miles")),
        "nmi": (1852.0, ("морская миля", "морских миль", "nautical mile")),
        "yd": (0.9144, ("ярд", "ярда", "ярдов", "yard", "yards")),
        "ft": (0.3048, ("фут", "фута", "футов", "foot", "feet")),
        "in": (0.0254, ("дюйм", "дюйма", "дюймов", "inch", "inches")),
        "au": (1.495978707e11, ("а.е.", "астрономическая единица", "astronomical unit")),
        "ly": (9.4607304725808e15, ("св.год", "световой год", "световых лет", "light year")),
        "pc": (3.0856775814913673e16, ("парсек", "парсека", "parsec")),
    },
    "масса": {
        "kg": (1.0, ("кг", "килограмм", "килограмма", "килограммов", "kilogram")),
        "g": (0.001, ("г", "грамм", "грамма", "граммов", "gram", "grams")),
        "mg": (1e-6, ("мг", "миллиграмм", "milligram")),
        "ug": (1e-9, ("мкг", "микрограмм", "microgram")),
        "t": (1000.0, ("т", "тонна", "тонны", "тонн", "ton", "tonne", "metric ton")),
        "lb": (0.45359237, ("фунт", "фунта", "фунтов", "pound", "pounds", "lbs")),
        "oz": (0.028349523125, ("унция", "унции", "унций", "ounce", "ounces")),
        "st": (6.35029318, ("стоун", "stone")),
        "ct": (0.0002, ("карат", "карата", "каратов", "carat")),
        "gr": (6.479891e-5, ("гран", "grain")),
        "us_ton": (907.18474, ("короткая тонна", "short ton")),
    },
    "объём": {
        "l": (1.0, ("л", "литр", "литра", "литров", "liter", "litre", "liters")),
        "ml": (0.001, ("мл", "миллилитр", "миллилитра", "миллилитров", "milliliter")),
        "m3": (1000.0, ("м3", "кубометр", "кубический метр", "куб.м", "cubic meter")),
        "cm3": (0.001, ("см3", "кубический сантиметр", "cc", "cubic centimeter")),
        "dm3": (1.0, ("дм3", "кубический дециметр")),
        "gal": (3.785411784, ("галлон", "галлона", "галлонов", "gallon", "us gallon")),
        "uk_gal": (4.54609, ("английский галлон", "имперский галлон", "imperial gallon")),
        "qt": (0.946352946, ("кварта", "кварты", "quart")),
        "pt": (0.473176473, ("пинта", "пинты", "пинт", "pint")),
        "cup": (0.2365882365, ("чашка", "стакан", "cup")),
        "floz": (0.0295735295625, ("жидкая унция", "fluid ounce", "fl oz")),
        "tbsp": (0.01478676478125, ("столовая ложка", "tablespoon")),
        "tsp": (0.00492892159375, ("чайная ложка", "teaspoon")),
        "bbl": (158.987294928, ("баррель", "барреля", "баррелей", "barrel")),
        "ft3": (28.316846592, ("фут3", "кубический фут", "cubic foot")),
    },
    "скорость": {
        "m/s": (1.0, ("м/с", "метр в секунду", "метров в секунду", "mps", "meters per second")),
        "km/h": (0.2777777777777778, ("км/ч", "километр в час", "километров в час", "kph", "kmh")),
        "mph": (0.44704, ("миль в час", "миля в час", "миль/ч", "miles per hour")),
        "kn": (0.5144444444444445, ("узел", "узла", "узлов", "knot", "knots")),
        "ft/s": (0.3048, ("фут/с", "футов в секунду", "feet per second", "fps")),
        "mach": (343.0, ("мах", "число маха")),
        # Не "c": голая буква "c" зарезервирована за Цельсием — так её пишут чаще.
        "c_light": (299792458.0, ("скорость света", "speed of light")),
    },
    "площадь": {
        "m2": (1.0, ("м2", "квадратный метр", "квадратных метров", "кв.м", "square meter")),
        "km2": (1e6, ("км2", "квадратный километр", "кв.км", "square kilometer")),
        "cm2": (1e-4, ("см2", "квадратный сантиметр", "square centimeter")),
        "mm2": (1e-6, ("мм2", "квадратный миллиметр")),
        "ha": (1e4, ("га", "гектар", "гектара", "гектаров", "hectare")),
        "a": (100.0, ("ар", "сотка", "соток")),
        "acre": (4046.8564224, ("акр", "акра", "акров", "acres")),
        "ft2": (0.09290304, ("фут2", "квадратный фут", "square foot", "sqft")),
        "in2": (0.00064516, ("дюйм2", "квадратный дюйм", "square inch")),
        "mi2": (2589988.110336, ("миля2", "квадратная миля", "square mile")),
    },
    "время": {
        "s": (1.0, ("с", "сек", "секунда", "секунды", "секунд", "second", "seconds")),
        "ms": (0.001, ("мс", "миллисекунда", "миллисекунд", "millisecond")),
        "us": (1e-6, ("мкс", "микросекунда", "microsecond")),
        "ns": (1e-9, ("нс", "наносекунда", "nanosecond")),
        "min": (60.0, ("мин", "минута", "минуты", "минут", "minute", "minutes")),
        "h": (3600.0, ("ч", "час", "часа", "часов", "hour", "hours", "hr")),
        "day": (86400.0, ("д", "сут", "сутки", "день", "дня", "дней", "days")),
        "week": (604800.0, ("нед", "неделя", "недели", "недель", "week", "weeks")),
        "month": (2629746.0, ("мес", "месяц", "месяца", "месяцев", "month", "months")),
        "year": (31556952.0, ("год", "года", "лет", "year", "years")),
    },
    "давление": {
        "pa": (1.0, ("па", "паскаль", "паскалей", "pascal")),
        "kpa": (1000.0, ("кпа", "килопаскаль", "kilopascal")),
        "mpa": (1e6, ("мпа", "мегапаскаль", "megapascal")),
        "bar": (1e5, ("бар", "бара", "баров")),
        "mbar": (100.0, ("мбар", "миллибар", "millibar")),
        "atm": (101325.0, ("атм", "атмосфера", "атмосферы", "атмосфер", "atmosphere")),
        "mmhg": (133.322387415, ("мм рт.ст.", "мм рт ст", "миллиметр ртутного столба", "torr", "торр")),
        "psi": (6894.757293168, ("фунт на квадратный дюйм", "psia")),
    },
    "энергия": {
        "j": (1.0, ("дж", "джоуль", "джоулей", "joule", "joules")),
        "kj": (1000.0, ("кдж", "килоджоуль", "kilojoule")),
        "mj": (1e6, ("мдж", "мегаджоуль", "megajoule")),
        "cal": (4.184, ("кал", "калория", "калорий", "calorie")),
        "kcal": (4184.0, ("ккал", "килокалория", "килокалорий", "kilocalorie")),
        "wh": (3600.0, ("вт·ч", "вт*ч", "втч", "ватт-час", "watt hour")),
        "kwh": (3.6e6, ("квт·ч", "квт*ч", "квтч", "киловатт-час", "kilowatt hour")),
        "ev": (1.602176634e-19, ("эв", "электронвольт", "electronvolt")),
        "btu": (1055.05585262, ("бте", "британская тепловая единица")),
    },
    "мощность": {
        "w": (1.0, ("вт", "ватт", "ватта", "ваттов", "watt", "watts")),
        "kw": (1000.0, ("квт", "киловатт", "киловатта", "kilowatt")),
        "mw": (1e6, ("мвт", "мегаватт", "megawatt")),
        "hp": (745.6998715822702, ("л.с.", "лошадиная сила", "лошадиных сил", "horsepower")),
        "ps": (735.49875, ("метрическая лошадиная сила", "pferdestarke")),
    },
    "данные": {
        "b": (1.0, ("байт", "байта", "байтов", "byte", "bytes")),
        "bit": (0.125, ("бит", "бита", "битов", "bits")),
        "kb": (1000.0, ("кб", "килобайт", "kilobyte")),
        "mb": (1e6, ("мб", "мегабайт", "megabyte")),
        "gb": (1e9, ("гб", "гигабайт", "gigabyte")),
        "tb": (1e12, ("тб", "терабайт", "terabyte")),
        "pb": (1e15, ("пб", "петабайт", "petabyte")),
        "kib": (1024.0, ("кибибайт", "kibibyte")),
        "mib": (1048576.0, ("мебибайт", "mebibyte")),
        "gib": (1073741824.0, ("гибибайт", "gibibyte")),
        "tib": (1099511627776.0, ("тебибайт", "tebibyte")),
    },
    "угол": {
        "deg": (1.0, ("°", "градус", "градуса", "градусов", "degree", "degrees")),
        "rad": (57.29577951308232, ("рад", "радиан", "радиана", "радианов", "radian")),
        "grad": (0.9, ("град", "гон", "gradian", "gon")),
        "arcmin": (1 / 60, ("угловая минута", "arcminute")),
        "arcsec": (1 / 3600, ("угловая секунда", "arcsecond")),
        "turn": (360.0, ("оборот", "оборота", "оборотов", "circle", "revolution")),
    },
    # Базовая единица — герц. Обороты в минуту это 1/60 Гц.
    # Голое слово "оборот" здесь не используется: оно уже занято категорией
    # "угол", поэтому для rpm берём только формы с указанием минуты.
    "частота": {
        "hz": (1.0, ("гц", "герц", "герца", "герцев", "hertz", "hz")),
        "khz": (1e3, ("кгц", "килогерц", "килогерца", "kilohertz", "khz")),
        "mhz": (1e6, ("мгц", "мегагерц", "мегагерца", "megahertz", "mhz")),
        "ghz": (1e9, ("ггц", "гигагерц", "гигагерца", "gigahertz", "ghz")),
        "rpm": (
            1 / 60,
            (
                "об/мин",
                "об/м",
                "обмин",
                "оборот в минуту",
                "оборота в минуту",
                "оборотов в минуту",
                "оборотов в мин",
                "revolutions per minute",
                "revolution per minute",
                "rev/min",
                "r/min",
                "rpm",
            ),
        ),
    },
}

# Температура: своя пара преобразований к кельвинам и обратно.
_TEMPERATURE: dict[str, tuple[object, object, tuple[str, ...]]] = {
    "c": (
        lambda v: v + 273.15,
        lambda k: k - 273.15,
        ("°c", "цельсий", "цельсия", "по цельсию", "celsius", "centigrade"),
    ),
    "f": (
        lambda v: (v + 459.67) * 5 / 9,
        lambda k: k * 9 / 5 - 459.67,
        ("°f", "фаренгейт", "фаренгейта", "по фаренгейту", "fahrenheit"),
    ),
    "k": (
        lambda v: v,
        lambda k: k,
        ("кельвин", "кельвина", "кельвинов", "kelvin"),
    ),
    "r": (
        lambda v: v * 5 / 9,
        lambda k: k * 9 / 5,
        ("°r", "ранкин", "ранкина", "rankine"),
    ),
}

TEMPERATURE_CATEGORY = "температура"


def _normalize(unit: str) -> str:
    """Привести написание единицы к виду, по которому ищем в индексе."""
    text = unit.strip().lower().replace("^", "").replace("**", "")
    text = text.replace("ё", "е")
    return " ".join(text.split())


def _build_index() -> dict[str, tuple[str, str]]:
    """alias -> (категория, каноническое имя единицы)."""
    index: dict[str, tuple[str, str]] = {}

    def put(alias: str, category: str, canonical: str) -> None:
        key = _normalize(alias)
        # Первое вхождение выигрывает: канонические имена регистрируются раньше.
        index.setdefault(key, (category, canonical))

    for category, units in _LINEAR.items():
        for canonical in units:
            put(canonical, category, canonical)
    for canonical in _TEMPERATURE:
        put(canonical, TEMPERATURE_CATEGORY, canonical)

    for category, units in _LINEAR.items():
        for canonical, (_factor, aliases) in units.items():
            for alias in aliases:
                put(alias, category, canonical)
    for canonical, (_to_k, _from_k, aliases) in _TEMPERATURE.items():
        for alias in aliases:
            put(alias, TEMPERATURE_CATEGORY, canonical)

    return index


_INDEX = _build_index()


def _resolve(unit: str) -> tuple[str, str] | None:
    """Найти категорию и каноническое имя единицы; None — если не опознали."""
    key = _normalize(unit)
    if key in _INDEX:
        return _INDEX[key]
    # Частый случай: "градусы цельсия", "5 метров в секунду" — пробуем убрать
    # хвостовые слова-паразиты и поискать по частям.
    words = key.split()
    for start in range(len(words)):
        for end in range(len(words), start, -1):
            candidate = " ".join(words[start:end])
            if candidate in _INDEX:
                return _INDEX[candidate]
    return None


def _format_number(value: float) -> str:
    """Человекочитаемое число: без хвоста нулей, с наукой на краях диапазона."""
    if value != value or value in (float("inf"), float("-inf")):
        return str(value)
    magnitude = abs(value)
    if magnitude != 0 and (magnitude < 1e-4 or magnitude >= 1e15):
        return f"{value:.6e}"
    text = f"{value:.10f}".rstrip("0").rstrip(".")
    if text in ("", "-"):
        return "0"
    # Ограничиваем значащие цифры, чтобы не показывать мусор двоичной точности.
    rounded = float(f"{value:.10g}")
    text = f"{rounded:.10f}".rstrip("0").rstrip(".")
    return text or "0"


def _convert(value: float, category: str, src: str, dst: str) -> float:
    if category == TEMPERATURE_CATEGORY:
        to_kelvin, _, _ = _TEMPERATURE[src]
        _, from_kelvin, _ = _TEMPERATURE[dst]
        return from_kelvin(to_kelvin(value))
    factor_src = _LINEAR[category][src][0]
    factor_dst = _LINEAR[category][dst][0]
    return value * factor_src / factor_dst


@tool
def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Перевести число из одной единицы измерения в другую.

    Поддерживаются длина, масса, температура, объём, скорость, площадь,
    время, давление, энергия, мощность, объём данных, углы и частота.
    Единицы можно писать по-русски или по-английски, сокращённо или
    полностью: "км", "kg", "фунт", "°F", "кВт·ч", "миль в час", "об/мин".

    Args:
        value: исходное число, например 12.5.
        from_unit: единица, из которой переводим, например "км".
        to_unit: единица, в которую переводим, например "мили".

    Returns:
        Строку вида "12.5 km = 7.7671 mi" либо понятное описание ошибки,
        если единица не опознана или единицы из разных категорий.
    """
    src = _resolve(from_unit)
    dst = _resolve(to_unit)

    if src is None and dst is None:
        return (
            f"Не понял ни одну из единиц: «{from_unit}» и «{to_unit}». "
            "Посмотри доступные через list_units."
        )
    if src is None:
        return f"Не понял единицу «{from_unit}». Посмотри доступные через list_units."
    if dst is None:
        return f"Не понял единицу «{to_unit}». Посмотри доступные через list_units."

    src_category, src_unit = src
    dst_category, dst_unit = dst
    if src_category != dst_category:
        return (
            f"«{from_unit}» — это {src_category}, а «{to_unit}» — это {dst_category}. "
            "Такие величины друг в друга не переводятся."
        )

    try:
        result = _convert(float(value), src_category, src_unit, dst_unit)
    except (TypeError, ValueError) as exc:
        return f"Не смог пересчитать: {exc}"

    return (
        f"{_format_number(float(value))} {src_unit} = "
        f"{_format_number(result)} {dst_unit} ({src_category})"
    )


@tool
def list_units(category: str = "") -> str:
    """Показать, какие единицы измерения агент умеет переводить.

    Args:
        category: название категории по-русски ("длина", "масса",
            "температура", "объём", "скорость", "площадь", "время",
            "давление", "энергия", "мощность", "данные", "угол",
            "частота").
            Пустая строка — вернуть список всех категорий.

    Returns:
        Строку со списком категорий или со списком единиц одной категории.
    """
    key = _normalize(category)
    all_categories = list(_LINEAR) + [TEMPERATURE_CATEGORY]

    if not key:
        return "Категории: " + ", ".join(all_categories)

    if key == _normalize(TEMPERATURE_CATEGORY):
        return "температура: " + ", ".join(sorted(_TEMPERATURE))

    for name, units in _LINEAR.items():
        if _normalize(name) == key:
            return f"{name}: " + ", ".join(sorted(units))

    return (
        f"Категории «{category}» нет. Доступные: " + ", ".join(all_categories)
    )
