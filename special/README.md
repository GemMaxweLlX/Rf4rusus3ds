# Rune Factory 4 Special: обработка машинного перевода

В этой ветке (`rf4-special`) идёт работа над русским текстом Rune Factory 4 Special (Switch/PC).

## Что лежит в `special/machine/`

Исходный машинный перевод в том виде, в каком он был получен:

- `*.eng`: игровые файлы из `Bundle` (формат `TEXT`, как на 3DS);
- `rf3TxtMenuCommon_split1_1.eng.txt`: только текст, файла `.eng` для него не было.

Отличия формата от 3DS:
- в Special пустые записи имеют смещение 0 (длина 0), но байт NUL в теле файла для них всё равно есть;
- в диалогах (`rf3mc.eng`) 113 348 записей против 99 572 на 3DS.

## Конвертер `tools/rf4s_txt.py`

Работает так же, как RF4STextExtractor: одна строка `.txt` на запись, перенос строки внутри записи обозначается `{LF}`.

```
python3 tools/rf4s_txt.py export file.eng                  # -> file.eng.txt
python3 tools/rf4s_txt.py import original.eng file.txt out.eng
```

Проверено: все файлы из `special/machine/` пересобираются байт в байт.
