# BlendKit → Ucupaint

[English version](README.md)

Аддон для Blender: материалы из [BlendKit](https://www.blenderkit.com/) попадают в
[Ucupaint](https://github.com/ucupumar/ucupaint) **слоем**, а не заменяют материал Ucupaint.

Обычно щелчок или перетаскивание материала BlendKit на объект заменяет материал объекта, и Ucupaint из этого
слота пропадает. С аддоном материал скачивается, запекается на UV объекта и добавляется новым слоем Ucupaint,
поверх которого можно рисовать дальше.

## Что нужно

- Blender **4.2** или новее
- [Ucupaint](https://extensions.blender.org/add-ons/ucupaint/) (проверено с 3.0)
- [BlendKit](https://extensions.blender.org/add-ons/blenderkit/) (проверено с 3.21) для пункта «Из BlendKit»;
  «Материал файла…» работает и без него
- У объекта должна быть UV-развёртка и материал Ucupaint в одном из слотов

Проверено на Blender 5.1.

## Установка

1. Скачай `blendkit_ucupaint-X.Y.Z.zip` со страницы [Releases](../../releases/latest) (раздел Assets) (или собери, см. ниже).
2. В Blender: **Edit → Preferences → Get Extensions**, справа вверху меню **⌄** → **Install from Disk…** и выбери zip.
   Можно и просто перетащить zip в окно Blender.
3. Проверь, что Ucupaint и BlendKit включены.

Обновление — так же, установкой нового zip.

## Как пользоваться

Выдели объект с материалом Ucupaint и открой у списка слоёв Ucupaint меню **+** (Add Layer):

- **Из BlendKit** открывает полосу материалов BlendKit в 3D-виде. Ищи в ней как обычно и **щёлкни** материал:
  после скачивания он запечётся и появится слоем. Перетаскивание на объект (или в редактор шейдеров) работает так же.
- **Материал файла…** добавляет любой материал, который уже есть в .blend (скачанные из BlendKit отмечены ★).

Когда слой готов, внизу 3D-вида появляется сообщение.

### Настройки

**Edit → Preferences → Add-ons → BlendKit to Ucupaint**:

| Настройка | Что делает |
|---|---|
| Способ | **Запечь на объект** — запекает цвет, шероховатость, металл, нормали (и высоту, если в материале есть displacement) точно как материал выглядит на объекте, с процедурными частями и смешиваниями. **Картинки как есть** — берёт картинки материала напрямую: тайлятся, но процедурные части и смешивания теряются. |
| Размер | Разрешение запечённых карт (512–4096). |
| Папка | Куда сохраняются PNG. `//` — рядом с .blend (по умолчанию `//textures/blendkit/`). С относительным путём сначала сохрани .blend. |
| Материал BlendKit на объект с Ucupaint — слоем | Выключи, чтобы BlendKit заменял материалы как обычно. |

Интерфейс на английском; при **Preferences → Interface → Translation** = русский он показывается по-русски.

## Особенности

- Для запекания на мгновение включается Cycles (CPU, 1 сэмпл), потом настройки рендера возвращаются. Объекты
  с выключенным рендером на время запекания включаются.
- Перехватываются только слоты, где уже стоит материал Ucupaint. Остальные объекты и слоты BlendKit обрабатывает
  как обычно.
- Скачанный материал BlendKit остаётся в файле (неназначенным); убрать его можно через
  **File → Clean Up → Purge Unused Data**.

## Сборка

```
python build.py                 # -> dist/blendkit_ucupaint-<версия>.zip
python build.py --bump patch    # 1.2.1 -> 1.2.2 и сборка (также minor / major)
python build.py --set 2.0.0     # задать точную версию и собрать
```

Нужен Python 3.9+. Версия хранится в одном месте — `blendkit_ucupaint/blender_manifest.toml`. Изменения каждой
версии описывай в [CHANGELOG.md](CHANGELOG.md). Тот же пакет собирает и сам Blender:
`blender --command extension build --source-dir blendkit_ucupaint --output-dir dist`.

## Выпуск версии

Релизы собирает GitHub Actions (`.github/workflows/release.yml`):

1. Подними версию: `python build.py --bump patch` (или `minor` / `major`) и опиши её в `CHANGELOG.md`
   под заголовком `## X.Y.Z`.
2. Закоммить, поставь тег и отправь:
   ```
   git commit -am "Release 1.2.2"
   git tag v1.2.2
   git push && git push --tags
   ```
3. GitHub соберёт `blendkit_ucupaint-1.2.2.zip` и выложит его на странице **Releases** с описанием из CHANGELOG.
   Тег должен совпадать с версией в `blender_manifest.toml`, иначе сборка остановится с ошибкой.

Пользователи качают zip в **Releases → Assets**. Последняя версия всегда по ссылке
`https://github.com/<you>/blendkit-ucupaint/releases/latest`.

## Лицензия

GPL-3.0-or-later, как у Blender, Ucupaint и BlendKit. См. [LICENSE](LICENSE).
