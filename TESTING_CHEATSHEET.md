# 🧪 Testing Tools Cheat Sheet — March 2026

> Шпаргалка: что есть, как работает, когда что использовать

---

## 📊 Обзорная таблица

| Категория | Инструмент | Зачем | Установка | Сложность |
|-----------|-----------|-------|-----------|-----------|
| **Покрытие** | `pytest-cov` | Какие строки НЕ покрыты тестами | `pip install pytest-cov` | ⭐ |
| **Мутации** | **Poodle** 🏆 | Проверяет КАЧЕСТВО тестов — ломает код и смотрит упали ли | `pip install poodle` | ⭐⭐ |
| **Мутации** | Cosmic Ray | То же + параллельное выполнение | `pip install cosmic-ray` | ⭐⭐⭐ |
| **Мутации** | mutmut v3 | То же, но несовместим с Django ❌ | — | — |
| **Property** | **Hypothesis** ✅ | Авто-генерация 100+ рандомных входов | `pip install hypothesis` | ⭐⭐ |
| **AI-генерация** | Qodo AI (ex-Codium) | AI генерирует тесты по коду | VS Code extension | ⭐ |
| **API-тесты** | Keploy | Записывает реальный API-трафик → тесты | `pip install keploy` | ⭐⭐ |
| **Линтер тестов** | `flake8-pytest-style` | Ищет плохие паттерны в тестах | `pip install flake8-pytest-style` | ⭐ |
| **Мёртвые фикстуры** | `pytest-dead-fixtures` | Находит неиспользуемые фикстуры | `pip install pytest-dead-fixtures` | ⭐ |

---

## 1. 📊 Coverage — Покрытие кода

**Что делает**: Показывает какие строки кода выполняются при запуске тестов.

```bash
# Одна команда — показать покрытие всего проекта
pytest --cov=ai_engine --cov=news --cov-report=html --cov-report=term-missing

# Открыть HTML-отчёт
open htmlcov/index.html
```

**Ключевые метрики**:
- `Stmts` — общее число строк
- `Miss` — пропущенные строки
- `Cover` — процент покрытия (цель: > 80%)
- `term-missing` — покажет номера непокрытых строк в терминале

---

## 2. 🧬 Mutation Testing — Мутационное тестирование

**Что делает**: Намеренно **ЛОМАЕТ** твой код (заменяет `>` на `>=`, `+` на `-`, удаляет return) и запускает тесты. Если тесты НЕ упали — тест бесполезный.

### Poodle 🏆 (рекомендуется, 2025-2026)

Лучший mutation testing для Python. Многопоточный, простой конфиг, HTML/JSON отчёты.

```bash
pip install poodle

# Запуск на конкретном модуле
poodle --source ai_engine/modules/prompt_sanitizer.py

# Запуск на всём проекте (будет ДОЛГО)
poodle --source ai_engine/

# С HTML-отчётом
poodle --source ai_engine/modules/scoring.py --reporter html
```

**Конфиг** (`poodle.toml`):
```toml
[poodle]
source_folders = ["ai_engine/modules"]
test_command = "pytest tests/ -x -q"
min_timeout = 10
runners = 4  # параллельные потоки
```

**Метрики**:
- 🎉 **Killed** — мутант убит (тест поймал ошибку) — ХОРОШО
- 🙁 **Survived** — мутант выжил (тест НЕ поймал) — ПЛОХО
- **Mutation Score** = killed / total × 100%. Цель: > 80%

### Cosmic Ray (альтернатива — параллельный)

```bash
pip install cosmic-ray

# Инициализация
cosmic-ray init config.toml session.sqlite

# Запуск
cosmic-ray exec session.sqlite

# Отчёт
cr-report session.sqlite
```

---

## 3. 🎲 Property-Based Testing — Hypothesis

**Что делает**: Вместо ручных тестовых данных, **генерирует сотни рандомных входов** и проверяет что свойства (инварианты) всегда выполняются.

```python
from hypothesis import given, strategies as st

@given(text=st.text(), max_len=st.integers(min_value=1, max_value=1000))
def test_sanitizer_never_crashes(text, max_len):
    result = sanitize_for_prompt(text, max_length=max_len)
    assert isinstance(result, str)
    assert len(result) <= max_len + 200
```

**Когда использовать**:
- Чистые функции (без БД, без API)
- Парсеры, валидаторы, scoring, форматирование
- Когда нужно найти edge-cases

**Новое в 2025-2026**:
- ✅ Thread-safe (Aug 2025) — работает с GIL-less Python
- ✅ Ghostwriter — автогенерация тестов для NumPy
- ✅ Python 3.14/3.15 совместимость

---

## 4. 🤖 AI-генерация тестов (2025-2026)

### Qodo AI (ex-Codium AI) — VS Code плагин
- Анализирует код и предлагает тест-кейсы
- Понимает контекст проекта
- Бесплатная версия для open source

### Baserock.ai — Agentic тестирование
- AI-агент читает код + user stories → генерирует тесты
- Работает с API и E2E тестами

### Keploy — API Recording → тесты
```bash
pip install keploy
# Записывает реальные API-вызовы и превращает их в тесты
keploy record -c "python manage.py runserver"
keploy test
```

---

## 5. 🔍 Статический анализ тестов

### Линтер для pytest
```bash
pip install flake8-pytest-style

# Найдёт:
# - неправильные ассерты (assert x == True → assert x)
# - дублированные параметризации
# - неправильный стиль фикстур
flake8 tests/ --select=PT
```

### Мёртвые фикстуры
```bash
pip install pytest-dead-fixtures
pytest --dead-fixtures
```

### SonarQube — комплексный анализ
- Code coverage + code smells + security + duplication
- Работает как сервер, интеграция с CI/CD

---

## 6. 🚀 Быстрая команда — проверить всё

```bash
# 1. Coverage
pytest --cov=ai_engine --cov=news --cov-report=term-missing -q

# 2. Property-based тесты
pytest tests/test_hypothesis_properties.py -v

# 3. Mutation testing (Poodle) — конкретный модуль
poodle --source ai_engine/modules/prompt_sanitizer.py

# 4. Линтер тестов
flake8 tests/ --select=PT

# 5. Мёртвые фикстуры
pytest --dead-fixtures
```

---

## 📝 Что есть в нашем проекте

| Что | Статус | Кол-во |
|-----|--------|--------|
| Unit/Integration тесты | ✅ | 1875+ |
| Property-based (Hypothesis) | ✅ | 22 |
| Coverage (pytest-cov) | ⚠️ Встроен в CI | — |
| Mutation (Poodle) | ❌ Не настроен | — |
| Линтер тестов | ❌ Не настроен | — |
| AI-генерация | ❌ | — |

---

## 🎯 Рекомендуемый следующий шаг

**Poodle** на `prompt_sanitizer.py` — займёт 5 минут, покажет реальный mutation score.
