
# 📡 WiFi Audit Tool with OLED Display

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%2FARM-orange.svg)]()
[![Wifite](https://img.shields.io/badge/Wifite-2.7.0-red.svg)](https://github.com/kimocoder/wifite2)

Автоматизированный инструмент для аудита безопасности WiFi сетей на базе одноплатного компьютера **NanoPi NEO** с выводом информации на **OLED дисплей SSD1306 128x64**.

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
12. [Предупреждение](#-предупреждение)

---

## 📋 Описание

Скрипт проводит **трёхэтапный тест** безопасности WiFi:

| Этап | Атака | Время |
|------|-------|-------|
| **1** | WPS Pixie-Dust | ~5 мин |
| **2** | WPA Dictionary + PMKID | ~10 мин |
| **3** | WPA Dictionary (Handshake) | ~10 мин |

**OLED дисплей** переключается каждые **5 секунд**:
- 📊 Статус атаки
- 📜 Логи wifite
- 🔓 Найденные пароли
- ⚙️ Результаты

---

## ✨ Возможности

- ✅ Автономная работа (без монитора)
- ✅ OLED дисплей 128x64
- ✅ Автозапуск при включении
- ✅ 3 типа атак
- ✅ Логирование событий
- ✅ Авторестарт при сбое
- ✅ Фиксация времени взлома

---

## 🛠️ Оборудование

| Компонент | Модель | Цена |
|-----------|--------|------|
| Плата | NanoPi NEO (H3) | $15-20 |
| WiFi адаптер | RTL8812AU / AR9271 | $10-15 |
| Дисплей | OLED SSD1306 128x64 I2C | $3-5 |
| Питание | 5V 2A MicroUSB | $5 |
| Провода | Dupont 4 шт. | $2 |

**Итого:** ~$40-55

---

## 🔌 Подключение OLED дисплея

### Распиновка SSD1306

| Пин OLED | Назначение | Цвет |
|----------|------------|------|
| 1 | GND | ⚫ Чёрный |
| 2 | VCC 3.3V | 🔴 Красный |
| 3 | SCL | 🟡 Жёлтый |
| 4 | SDA | 🟢 Зелёный |

### Схема подключения

```
OLED SSD1306          NanoPi NEO
┌──────────┐          ┌──────────┐
│ GND ●────┼──────────┼─● GND    │
│ VCC ●────┼──────────┼─● 3.3V   │
│ SCL ●────┼──────────┼─● SCL    │
│ SDA ●────┼──────────┼─● SDA    │
└──────────┘          └──────────┘
```

⚠️ **НЕ подключайте VCC к 5V!** OLED сгорит.

### Проверка подключения

```bash
sudo apt install i2c-tools -y
sudo i2cdetect -y 0
```

Должно показать **`3c`** на позиции 3c.

---

## 📦 Установка ПО

```bash
# Обновление
sudo apt update && sudo apt upgrade -y

# Зависимости
sudo apt install python3-pip git wifite aircrack-ng i2c-tools crunch -y
pip3 install luma.oled

# Клонирование
cd ~
git clone https://github.com/ВАШ_НИК/wifi-audit-oled.git
cd wifi-audit-oled
```

---

## 🔑 Генерация словаря паролей

### Использование Crunch

**Crunch** — стандартная утилита для генерации словарей.

```bash
# Цифровой словарь 8 символов
crunch 8 8 0123456789 -o passwords.txt

# Цифры 4-6 символов (быстрый тест)
crunch 4 6 0123456789 -o passwords_small.txt

# Цифры + буквы (долго!)
crunch 8 8 abcdefghijklmnopqrstuvwxyz0123456789 -o passwords_mix.txt
```

### Время генерации

| Длина | Символы | Паролей | Размер | Время |
|-------|---------|---------|--------|-------|
| 4-6 | Цифры | 1.1 млн | 8 MB | 1 мин |
| 8 | Цифры | 100 млн | 800 MB | 1 час |
| 8 | Цифры+буквы | 2.8 трлн | 22 TB | ❌ Не рекомендуется |

### Перемещение словаря

```bash
sudo mv passwords.txt /usr/share/dict/
```

---

## ⚙️ Настройка скрипта

```bash
nano wifi_audit.py
```

**Измените переменные:**

```python
INTERFACE = "wlan0"                              # Ваш интерфейс
DICTIONARY = "/usr/share/dict/passwords.txt"     # Путь к словарю
WIFITE_POWER = 40                                # Мощность сигнала
WIFITE_SCAN_TIME = 60                            # Время сканирования
OLED_UPDATE_INTERVAL = 5                         # Обновление экрана
```

### Проверка работы

```bash
sudo python3 wifi_audit.py
```

Нажмите **Ctrl+C** для остановки.

---

## ⚙️ Автозапуск (systemd)

### Создание службы

```bash
sudo nano /etc/systemd/system/wifi-audit.service
```

**Вставьте:**

```ini
[Unit]
Description=WiFi Audit Tool with OLED Display
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/arkh/wifi-audit-oled
ExecStart=/usr/bin/script -q -c "/usr/bin/python3 /home/arkh/wifi-audit-oled/wifi_audit.py" /dev/null
Restart=on-failure
RestartSec=10
ExecStartPre=/bin/sleep 5

[Install]
WantedBy=multi-user.target
```

⚠️ **Измените пути** на ваши!

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
| `sudo systemctl status wifi-audit.service` | Статус |
| `sudo systemctl stop wifi-audit.service` | Остановить |
| `sudo systemctl start wifi-audit.service` | Запустить |
| `sudo systemctl restart wifi-audit.service` | Перезапустить |
| `sudo journalctl -u wifi-audit.service -f` | Логи онлайн |

---

## 🔍 Диагностика проблем

### Дисплей не работает
```bash
sudo i2cdetect -y 0
# Должно показать 3c
```

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

### Ошибка TTY
```bash
# Проверьте что в службе есть:
ExecStart=/usr/bin/script -q -c "..." /dev/null
```

---

## ❓ FAQ

**Q: Можно без OLED?**  
A: Да, скрипт работает, логи в journalctl.

**Q: Какой словарь лучше?**  
A: 8 цифр (crunch 8 8 0123456789) или rockyou.txt.

**Q: Сколько времени на атаку?**  
A: ~25-30 минут на полный цикл (3 атаки).

**Q: Где взломанные пароли?**  
A: `/home/arkh/cracked.json` и логи.

**Q: Как изменить интервал экрана?**  
A: В скрипте `OLED_UPDATE_INTERVAL = 5`.

**Q: Автовыключение после завершения?**  
A: Добавьте в `show_final_results()`:
```python
subprocess.run(["sudo", "shutdown", "-h", "now"])
```

---

## ⚠️ Предупреждение

> **Используйте ТОЛЬКО для:**
> - Тестирования **своих** сетей
> - Сетей с **письменным разрешением**
> - Образовательных целей
>
> **Запрещено:**
> - Несанкционированный доступ
> - Атака на чужие сети
>
> Авторы не несут ответственности за неправомерное использование.

---

## 📝 Лицензия

MIT License — свободное использование с указанием авторства.

---

## 📧 Контакты

| GitHub | Email |
|--------|-------|
| [@ВАШ_НИК](https://github.com/ВАШ_НИК) | ваш@email.com |

---

<div align="center">

**⭐ Если полезно — поставьте звезду!**

Made with ❤️ for security research

</div>
```

---

## ✅ Теперь:

1.  **Скопируйте весь код выше** (от `# 📡 WiFi Audit` до `</div>`)
2.  **Сохраните как `README.md`** в вашем репозитории
3.  **Замените** `ВАШ_НИК` и `ваш@email.com` на ваши данные

---

## 📁 Структура репозитория:

```
wifi-audit-oled/
├── README.md           # ← Этот файл (документация)
├── wifi_audit.py       # ← Основной скрипт
├── requirements.txt    # ← luma.oled
└── wifi-audit.service  # ← Файл службы (опционально)
```

---

**Всё в одном файле, готово для GitHub!** 🚀
