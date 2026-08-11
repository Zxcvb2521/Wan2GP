# AI Creator Studio

Windows-first desktop оболочка для WanGP без Docker, без ручного запуска Python и без Gradio UI.

## Текущий статус

Это первый кодовый прототип интерфейса. Он уже содержит русское desktop-oriented UI на React/TypeScript и заготовленную архитектуру интеграции с существующим `shared/api.py` WanGP.

## Запуск frontend-прототипа

Требуется Node.js 20+.

```powershell
cd ai_creator_studio
npm install
npm run dev
```

Для desktop-режима после добавления Tauri configuration:

```powershell
npm run tauri:dev
```

## Важно

Пока frontend не запускает генерацию. Следующий кодовый этап — сделать native bridge/launcher и подключить `WanGPSession` из `shared/api.py`, который уже предоставляет in-process session API, модели, schema, jobs, progress/events и cancel.

Python runtime конечной Windows-сборки должен поставляться вместе с приложением и запускаться автоматически. Отдельная установка Python пользователю не нужна.
