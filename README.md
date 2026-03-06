```markdown
# 📡 WiFi Audit Tool with OLED Display

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%2FARM-orange.svg)]()
[![Wifite](https://img.shields.io/badge/Wifite-2.7.0-red.svg)](https://github.com/kimocoder/wifite2)

Автоматизированный инструмент для аудита безопасности WiFi сетей на базе одноплатного компьютера (NanoPi NEO, Raspberry Pi) с выводом информации на **OLED дисплей SSD1306 128x64**.

Предназначен для **тестирования собственных сетей** на устойчивость к атакам. Работает автономно без подключения монитора или клавиатуры.

---

## 📖 Содержание

1. [Описание](#-описание)
2. [Возможности](#-возможности)
3. [Оборудование](#-оборудование)
4. [Подключение OLED](#-подключение-oled-дисплея)
5. [Установка ПО](#-установка-по)
6. [Генерация словаря](#-генерация-словаря-паролей)
7. [Настройка скрипта](#-настройка-скрипта)
8. [Автозапуск (systemd)](#-автозапуск-systemd)
9. [Управление](#-управление-службой)
10. [Диагностика](#-диагностика-проблем)
11. [FAQ](#-faq)

---

## 📋 Описание

Скрипт проводит **трёхэтапный тест** безопасности WiFi:

| Этап | Атака | Описание | Время |
|------|-------|----------|-------|
| **1** | WPS Pixie-Dust | Проверка на уязвимость WPS | ~5 мин |
| **2** | WPA Dictionary + PMKID | Атака по словарю с PMKID | ~10 мин |
| **3** | WPA Dictionary (Handshake) | Атака по словарю (хендшейк) | ~10 мин |

**OLED дисплей** переключается каждые **5 секунд**:
- 📊 Статус атаки (название, таймеры)
- 📜 Логи wifite (последние 4 строки)
- 🔓 Найденные пароли (мигает при взломе)
- ⚙️ Результаты (после завершения)

---

## ✨ Возможности

- ✅ **Автономная работа** — не требует монитора/клавиатуры
- ✅ **OLED дисплей** — вся информация на экране 128x64
- ✅ **Автозапуск** — запуск при включении устройства (systemd)
- ✅ **3 типа атак** — WPS, WPA+PMKID, WPA+Handshake
- ✅ **Логирование** — все события сохраняются в файл
- ✅ **Защита от сбоев** — автоматический перезапуск при ошибке
- ✅ **Умный дисплей** — приоритетный вывод (взлом > атака > логи)
- ✅ **Дата и время** — фиксация момента взлома каждой сети
- ✅ **Универсальность** — автоматическое определение путей (работает на любом Linux)

---

## 🛠️ Оборудование

| Компонент | Модель | Примечание | Цена |
|-----------|--------|------------|------|
| **Плата** | NanoPi NEO / Raspberry Pi | Любая с GPIO | $15-35 |
| **WiFi адаптер** | RTL8812AU / AR9271 | Обязательно режим монитора | $10-15 |
| **Дисплей** | OLED SSD1306 128x64 | Интерфейс I2C | $3-5 |
| **Питание** | 5V 2A | Стабильное питание | $5 |
| **Провода** | Dupont Female-Female | 4 шт. для подключения | $2 |

**💰 Итого:** ~$40-60 за полное устройство

---

## 🔌 Подключение OLED дисплея

### Распиновка SSD1306

| Пин OLED | Назначение | Цвет провода |
|----------|------------|--------------|
| **1** | GND | ⚫ Чёрный |
| **2** | VCC 3.3V | 🔴 Красный |
| **3** | SCL | 🟡 Жёлтый |
| **4** | SDA | 🟢 Зелёный |

### Схема подключения

```
OLED SSD1306          NanoPi NEO / RPi
┌──────────┐          ┌──────────┐
│ GND ●────┼──────────┼─● GND    │
│ VCC ●────┼──────────┼─● 3.3V   │
│ SCL ●────┼──────────┼─● SCL    │
│ SDA ●────┼──────────┼─● SDA    │
└──────────┘          └──────────┘
```

⚠️ **ВАЖНО:** НЕ подключайте VCC к 5V! OLED работает от 3.3V и сгорит от 5V.

### Проверка подключения

```bash
sudo apt install i2c-tools -y
sudo i2cdetect -y 0
```

**Ожидаемый результат:** Должно показать **`3c`** на позиции 3c.

---

## 📦 Установка ПО

### Шаг 1: Обновление системы

```bash
sudo apt update && sudo apt upgrade -y
```

### Шаг 2: Установка зависимостей

```bash
sudo apt install python3-pip git wifite aircrack-ng i2c-tools crunch -y
pip3 install luma.oled
```

### Шаг 3: Клонирование репозитория

```bash
cd ~
git clone https://github.com/ВАШ_НИК/wifi-audit-oled.git
cd wifi-audit-oled
```

---

## 🔑 Генерация словаря паролей

Для генерации словарей используется утилита **Crunch**.

### Быстрый старт

```bash
# Цифровой словарь 8 символов (рекомендуется)
crunch 8 8 0123456789 -o passwords.txt

# Цифры 4-6 символов (быстрый тест)
crunch 4 6 0123456789 -o passwords_small.txt

# Переместить в системную папку
sudo mv passwords.txt /usr/share/dict/
```

### Время генерации

| Длина | Символы | Паролей | Размер | Время |
|-------|---------|---------|--------|-------|
| 4-6 | Цифры | 1.1 млн | 8 MB | 1 мин |
| 8 | Цифры | 100 млн | 800 MB | 1 час |
| 8 | Цифры+буквы | 2.8 трлн | 22 TB | ❌ Не рекомендуется |

---

## ⚙️ Настройка скрипта

```bash
nano wifi_audit.py
```

**Измените переменные в начале файла:**

```python
INTERFACE = "wlan0"                              # Ваш WiFi интерфейс
DICTIONARY = "/usr/share/dict/passwords.txt"     # Путь к словарю
WIFITE_POWER = 40                                # Мин. мощность сигнала (dbm)
WIFITE_SCAN_TIME = 60                            # Время сканирования (сек)
OLED_UPDATE_INTERVAL = 5                         # Обновление экрана (сек)
```

> **✅ Пути к файлам определяются автоматически!**
> - Логи: `~/wifite_full_log.txt`
> - Взломы: `~/cracked.json`
> - Скрипт работает на любом ПК без изменения путей!

### Проверка работы

```bash
sudo python3 wifi_audit.py
```

Нажмите **Ctrl+C** для остановки после проверки.

---

## ⚙️ Автозапуск (systemd)

### Создание службы

```bash
sudo nano /etc/systemd/system/wifi-audit.service
```

**Вставьте содержимое:**

```ini
[Unit]
Description=WiFi Audit Tool with OLED Display
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/ВАШ_ПОЛЬЗОВАТЕЛЬ/wifi-audit-oled
ExecStart=/usr/bin/script -q -c "/usr/bin/python3 /home/ВАШ_ПОЛЬЗОВАТЕЛЬ/wifi-audit-oled/wifi_audit.py" /dev/null
Restart=on-failure
RestartSec=10
ExecStartPre=/bin/sleep 5

[Install]
WantedBy=multi-user.target
```

⚠️ **Замените `/home/ВАШ_ПОЛЬЗОВАТЕЛЬ/` на ваш путь!** (например `/home/user/`)

### Активация

```bash
sudo systemctl daemon-reload
sudo systemctl enable wifi-audit.service
sudo systemctl start wifi-audit.service
```

### Проверка

```bash
sudo systemctl status wifi-audit.service
```

---

## 📊 Управление службой

| Команда | Описание |
|---------|----------|
| `sudo systemctl status wifi-audit.service` | Показать статус |
| `sudo systemctl stop wifi-audit.service` | Остановить |
| `sudo systemctl start wifi-audit.service` | Запустить |
| `sudo systemctl restart wifi-audit.service` | Перезапустить |
| `sudo systemctl disable wifi-audit.service` | Отключить автозапуск |
| `sudo journalctl -u wifi-audit.service -f` | Логи в реальном времени |
| `sudo journalctl -u wifi-audit.service -n 50` | Последние 50 строк |

---

## 🔍 Диагностика проблем

### Дисплей не работает
```bash
sudo i2cdetect -y 0
# Должно показать 3c
```
**Решение:** Проверьте подключение проводов (GND, VCC, SCL, SDA). Убедитесь что VCC = 3.3V.

### Скрипт не запускается
```bash
sudo journalctl -u wifi-audit.service -n 100
sudo chmod +x wifi_audit.py
sudo systemctl restart wifi-audit.service
```

### WiFi адаптер не найден
```bash
iwconfig
sudo reboot
```

### Ошибка TTY / stty
```bash
# Проверьте что в службе есть script:
ExecStart=/usr/bin/script -q -c "..." /dev/null
```

### Служба постоянно перезапускается
```bash
sudo journalctl -u wifi-audit.service -n 50 --no-pager
sudo python3 wifi_audit.py  # Проверка вручную
```

---

## ❓ FAQ

**Q: Можно использовать без OLED?**  
A: Да, скрипт работает, логи пишутся в `journalctl` и файл.

**Q: Какой словарь лучше?**  
A: 8 цифр (`crunch 8 8 0123456789`) или `rockyou.txt`.

**Q: Сколько времени на атаку?**  
A: ~25-30 минут на полный цикл (3 атаки).

**Q: Где взломанные пароли?**  
A: `~/cracked.json` и `~/wifite_full_log.txt`.

**Q: Как изменить интервал экрана?**  
A: В скрипте `OLED_UPDATE_INTERVAL = 5`.

**Q: Автовыключение после завершения?**  
A: Добавьте в конец функции `show_final_results()`:
```python
subprocess.run(["sudo", "shutdown", "-h", "now"])
```

**Q: Работает на Raspberry Pi?**  
A: Да, подключите OLED к GPIO (SCL/SDA/GND/3.3V).


## 📝 Лицензия

**MIT License** — свободное использование с указанием авторства.


## 📁 Структура репозитория:

```
wifi-audit-oled/
├── README.md           # ← Этот файл
├── wifi_audit.py       # ← Основной скрипт (универсальный)
├── requirements.txt    # ← luma.oled
└── wifi-audit.service  # ← Файл службы (опционально)
```
