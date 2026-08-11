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
9. Studio не дублирует возможности WanGP без необходимости: Deepy остаётся нативным агентом WanGP и подключается через adapter.

## Предлагаемый стек

- Desktop shell: Tauri 2
- Frontend: React + TypeScript + Vite
- UI: Tailwind CSS + shadcn/ui
- Desktop/backend bridge: Tauri commands + локальный HTTP/WebSocket только внутри приложения при необходимости
- Orchestrator: Python/FastAPI или нативный Rust orchestration layer; первый MVP допускает отдельный локальный Python orchestrator
- AI engine: WanGP
- Native media agent: Deepy внутри WanGP
- Optional external LLM engine: Ollama / KoboldCpp, подключаемые позже для сценариев, текста и альтернативного LLM runtime
- Media: FFmpeg
- Storage: SQLite + файловое хранилище проекта

## Роли Deepy и внешних LLM

Deepy не заменяется Ollama или KoboldCpp. Deepy — нативный WanGP-агент для многошаговой работы с медиа: он может оркестрировать генерацию/обработку изображений, видео и аудио и использовать контекст уже созданных материалов.

В Studio Deepy должен использоваться как существующая capability WanGP, а не как отдельная самостоятельно переписанная система. На текущем этапе adapter только обнаруживает нативный Deepy и его требования; прямые image/video jobs продолжают использовать существующий headless/session API WanGP.

Ollama и KoboldCpp — отдельные внешние LLM-провайдеры. Они не обязательны для базового MVP и не должны вытеснять Deepy. Их будущая роль — сценарии, длинный текст, идеи, структурирование проекта и другие задачи общего LLM.

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

Deepy имеет отдельную границу интеграции:

```text
DeepyAdapter
├── detect_availability()
├── detect_required_prompt_enhancer()
└── launch_native_cli()
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
