# ADMEXA SMM Parser

Автоматический сборщик новостей из 19 источников для контент-стратегии ADMEXA.

## Как работает

GitHub Actions запускает парсер **4 раза в день** (00:00, 06:00, 12:00, 18:00 UTC).  
Результаты сохраняются в `output/` и коммитятся в репозиторий.

## Результаты

| Файл | Содержание |
|------|-----------|
| `output/news.json` | Все новости в JSON (для Claude) |
| `output/digest.md` | Читаемый дайджест (можно смотреть прямо в GitHub) |

## Как использовать с Claude

1. Открыть `output/digest.md` в GitHub → скопировать содержимое
2. Вставить в чат Claude: *"Вот свежие новости из реестра — напиши посты для ADMEXA"*
3. Claude напишет 2–3 поста в фирменном стиле ADMEXA на основе реальных событий

Или: скачать `output/news.json` и приложить файлом к сообщению.

## Запуск вручную

GitHub → Actions → **ADMEXA News Parser** → **Run workflow**  
Можно выбрать `max_age_days` (по умолчанию 7).

## Источники

**Приоритет А** (ежедневно): STEP Blog · OECD Taxation · ECB · ESMA · FATF ·  
Invest Europe · WealthBriefing · CySEC · KPMG EU Tax Centre · Private Equity News

**Приоритет Б** (2–3 раза/нед): IEA · ITIJ · UK Visas & Immigration · ENISA ·  
Knight Frank · EU Digital Strategy · ECIA · Art Basel / UBS

## Локальный запуск

```bash
pip install -r requirements.txt
python scripts/parser.py
# → output/news.json + output/digest.md
```
