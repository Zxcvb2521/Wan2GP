# AI Creator Studio — архитектура

## Цель

Windows-first desktop-приложение поверх существующего WanGP. Пользователь не запускает Python, Docker, Gradio или браузер вручную. Все внутренние runtime-компоненты поставляются вместе с приложением и управляются лаунчером.

## Принципы

1. WanGP остаётся backend/engine, а не пользовательским UI.
2. Gradio не является частью пользовательского интерфейса.
3. Docker и WSL не требуются.
4. Python runtime поставляется локально вместе с приложением либо создаётся первым запуском из поставляемого runtime-пакета.
5. Русский язык — язык интерфейса по умолчанию и обязательная полная локализация первой версии.
6. Frontend и backend отделены от конкретного движка через adapters.
7. GPU/RAM/VRAM состояние показывается пользователю понятно, без необходимости знать внутренности PyTorch.
8. Все тяжёлые операции выполняются как управляемые jobs с прогрессом, отменой и восстановлением.

## Предлагаемый стек

- Desktop shell: Tauri 2
- Frontend: React + TypeScript + Vite
- UI: Tailwind CSS + shadcn/ui
- Desktop/backend bridge: Tauri commands + локальный HTTP/WebSocket только внутри приложения при необходимости
- Orchestrator: Python/FastAPI или нативный Rust orchestration layer; первый MVP допускает отдельный локальный Python orchestrator
- AI engine: WanGP
- Optional LLM engine: KoboldCpp, подключаемый позже
- Media: FFmpeg
- Storage: SQLite + файловое хранилище проекта

## Runtime layout

```text
AI Creator Studio/
├── AI-Creator.exe
├── runtime/
│   ├── python/
│   ├── ffmpeg/
│   └── engine/
│       └── WanGP/
├── models/
├── projects/
├── cache/
├── logs/
└── config/
```

Пользователь не обязан устанавливать Python отдельно. Runtime должен быть приватным для приложения и запускаться лаунчером автоматически.

## Backend adapter

Первый adapter должен скрывать детали WanGP:

```text
EngineAdapter
├── get_status()
├── get_capabilities()
├── list_models()
├── load_model()
├── unload_model()
├── submit_job()
├── get_job()
├── cancel_job()
├── generate_image()
├── generate_video()
├── generate_audio()
├── generate_voice()
└── transcribe_audio()
```

Фактические функции и точки интеграции нельзя угадывать: перед реализацией adapter необходимо исследовать исходники WanGP и существующие Deepy/controller/headless возможности.

## UI

Главные разделы первой версии:

- Создать
- Проекты
- Мои материалы
- Очередь
- Настройки

В разделе «Создать»:

- Изображение
- Видео
- Музыка
- Голос
- Текст/история

Сложные параметры скрыты за «Расширенные настройки».

## Язык

Русский (`ru-RU`) — default locale. Все пользовательские строки должны находиться в locale-файлах, а не быть разбросаны по компонентам.

```text
locales/
├── ru-RU.json
└── en-US.json
```

Английская локализация может быть второй, но русский интерфейс обязателен для MVP.

## Без браузера

Основной режим — нативное окно Tauri. Внутренний WebView используется только как технология отображения интерфейса приложения; пользователь не должен открывать localhost в Chrome/Edge.

## Первый MVP

Путь проверки:

```text
AI-Creator.exe
  -> стартует embedded Python runtime
  -> запускает минимальный WanGP backend
  -> UI получает статус GPU
  -> пользователь вводит prompt
  -> WanGP генерирует изображение
  -> результат появляется в приложении
  -> metadata сохраняется в проект
```

После успешного image path подключаются video, audio/TTS и project/timeline workflows.
