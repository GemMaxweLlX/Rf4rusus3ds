# Rune Factory 4 Special — Nintendo Switch

Русский перевод для Switch-версии RF4 Special. Собран на основе перевода Steam-версии (`special/Bundle`).

## Готовый патч

`patch/RF4S_RUS_Switch.zip` — папка `romfs` для Atmosphere (LayeredFS) и инструкция `INSTALL_RU.txt`.
Папку `romfs` нужно положить в `atmosphere/contents/<TitleID игры>/`. Игру запускать на английском языке.

## Чем Switch отличается от Steam

Структура и имена файлов те же (25 файлов `.eng` в `script/`, `text/`, `textAndData/text/`).
20 файлов совпадают со Steam байт в байт. Отличаются:

- `script/rf3mc.eng`: 108 927 строк против 113 348 в Steam, часть реплик в другой редакции;
- `rf3TxtLoad`: тексты ошибок сохранения;
- `rf3TxtTouchPocket`: кнопки «Equip Y/X» буквами, без значков;
- `rf3TxtItem_split2_1/2_2`: по одной строке.

## Откуда взят перевод

| Источник | Строк в `rf3mc` |
|---|---|
| Steam (та же английская строка на том же месте) | 107 751 |
| Ручной перевод 3DS | 1 141 |
| Наши переводы (`special/tr`) | 19 |
| Правки только для Switch (`switch/tr/rf3mc.eng.tsv`) | 16 |

Английского текста не осталось.

## Пересборка

```
python3 special/tools/build_switch.py SWITCH_ROMFS STEAM_EN_DIR DS_EN_TEXT_DIR
```

- `SWITCH_ROMFS` — английская папка `romfs` Switch;
- `STEAM_EN_DIR` и `DS_EN_TEXT_DIR` — те же папки, что для `build_special.py`.

Результат: `switch/romfs/` и таблицы сверки `switch/tables/*.xlsx` (английский, русский, источник).
