# AI Creator Studio

**Windows-first desktop-приложение для локального создания видео и мультимедиа на базе WanGP.**

Наша рабочая ветка `feature/ai-creator-studio` содержит отдельную desktop-оболочку и не изменяет исходную `main` ветку WanGP.

## Цель проекта

AI Creator Studio объединяет генерацию и монтаж в одном русскоязычном приложении:

```text
текст / сценарий
      ↓
   AI-генерация
      ↓
  изображения
  видео / голос / музыка
      ↓
    Timeline
      ↓
   Предпросмотр
      ↓
     FFmpeg
      ↓
    готовый MP4
```

## Архитектура

- **Desktop UI:** Tauri 2 + React + TypeScript
- **Интерфейс:** русский язык, без Gradio
- **Backend:** локальный Python runtime
- **AI engine:** WanGP
- **Монтаж/экспорт:** Timeline + FFmpeg
- **Windows packaging:** NSIS и MSI
- **Docker:** не требуется
- **Отдельная установка Python:** не требуется в конечной сборке

Tauri уже настроен включать каталог `runtime` в пакет приложения. fileciteturn74file0

## Текущее состояние

Уже реализованы основные части Studio:

- русскоязычный desktop UI;
- проекты и Timeline;
- добавление результатов генерации в проект;
- перемещение и изменение длительности клипов;
- Preview видео/изображений;
- синхронизация voice/music в Preview;
- Timeline API для изменения и удаления клипов;
- FFmpeg render pipeline;
- учёт громкости аудиоклипов при финальном рендере;
- автоматическое добавление сгенерированных изображений в Timeline;
- native Tauri launcher для запуска встроенного backend.

## Важное ограничение текущей ветки

Репозиторий **ещё не содержит готового portable Python runtime со всеми зависимостями WanGP**. Поэтому текущую ветку пока нельзя считать готовым установочным релизом для конечного пользователя.

Следующий инфраструктурный этап — собрать runtime для Windows:

```text
ai_creator_studio/runtime/
├── python/
│   └── python.exe
├── WanGP/
└── ffmpeg/
```

После этого Tauri должен собирать обычный Windows-инсталлятор:

```text
AI-Creator-Studio-Setup.exe
```

без ручного запуска Python, Docker или Gradio.

## Разработка

Для разработки интерфейса требуется Node.js 20+:

```powershell
cd ai_creator_studio
npm install
npm run dev
```

Для desktop-режима:

```powershell
npm run tauri:dev
```

Для Windows-сборки:

```powershell
npm run tauri:build
```

Пока portable runtime не собран, `tauri:build` создаёт пакет оболочки, но это ещё не финальный автономный AI-дистрибутив.

## Принцип ветки

Вся работа над AI Creator Studio ведётся только в:

```text
feature/ai-creator-studio
```

Исходная `main` ветка WanGP не используется для изменений проекта Studio.
