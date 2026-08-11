# Сборка AI Creator Studio для Windows

Этот документ описывает текущую разработческую сборку. Он **не требует Docker** и не предполагает ручной запуск Python в конечном приложении.

## 1. Подготовка

Установите инструменты разработки один раз:

- Node.js 20+;
- Rust stable;
- Microsoft C++ Build Tools;
- WebView2 (обычно уже есть в Windows 10/11).

Python отдельно для пользователя устанавливать не требуется после появления bundled runtime.

## 2. Запуск текущего frontend/desktop прототипа

```powershell
cd ai_creator_studio
npm install
npm run tauri:dev
```

На текущей стадии launcher ожидает встроенный runtime по адресу:

```text
ai_creator_studio/runtime/python/python.exe
ai_creator_studio/runtime/WanGP/studio_backend.py
```

Если runtime ещё не собран, приложение сообщит, что встроенный Python или backend не найден.

## 3. Финальная структура runtime

Для автономной Windows-сборки каталог должен выглядеть примерно так:

```text
runtime/
├── python/
│   ├── python.exe
│   ├── python311.dll
│   └── Lib/...
├── WanGP/
│   ├── studio_backend.py
│   ├── studio_render.py
│   ├── studio_timeline.py
│   └── ...
└── ffmpeg/
    └── bin/
        ├── ffmpeg.exe
        └── ffprobe.exe
```

Точные native/CUDA зависимости будут определены на этапе сборки runtime под Windows.

## 4. Сборка установщика

После заполнения `runtime`:

```powershell
cd ai_creator_studio
npm run tauri:build
```

Tauri настроен на создание NSIS и MSI пакетов.

Ожидаемые артефакты находятся в каталоге `src-tauri/target/release/bundle/`.

## 5. Что пользователь не должен делать

Финальный пользователь не должен выполнять:

```text
python studio_backend.py
pip install ...
docker compose up
gradio ...
```

Все эти детали должны быть скрыты desktop-приложением.

## 6. Проверка после установки

После запуска приложения проверяется следующая цепочка:

1. Tauri находит bundled runtime.
2. Запускается встроенный Python.
3. Запускается `studio_backend.py`.
4. UI ждёт `/health`.
5. Backend сообщает доступные модели.
6. Пользователь создаёт проект.
7. Результат попадает в Timeline.
8. Preview воспроизводит Timeline.
9. Render создаёт MP4 через FFmpeg.

Если любой пункт не проходит, это считается ошибкой runtime/packaging, а не поводом требовать от пользователя ручную установку компонентов.
