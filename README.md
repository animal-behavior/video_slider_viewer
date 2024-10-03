## Установка:
1. ```python -m venv video_slider_viewer```
2. ```pip install -r requirements.txt```

## Запуск:
1. ```pip install -r requirements.txt``` (если зависимости обновлялись)
2. ```python video_slider_viewer.py```

## Как пользоваться:
1. Загрузите видео
2. Загрузите csv файл в следующем формате:

| frame | iliac crest x | iliac crest y | hip x | hip y | knee x | knee y | ... |
|-------|---------------|---------------|-------|-------|--------|--------|-----|
| 0     | 1669          | 727           | 1660  | 765   | 1666   | 753    | ... |
| 1     | 1678          | 746           | 1660  | 766   | 1667   | 754    | ... |

Первой идет колонка с номером кадра - 'frame', далее попарно координаты части тела

Столбцы с координатами в следующем порядке: iliac crest -> hip -> knee -> ankle -> mtp -> toe 

Это важно для корректного соединения узлов

3. Установите начальный и конечный номера кадров
4. Нажмите кнопку 'Set Frame Range'
5. Ползунком переключайте кадры (номер текущего кадра отображается в правом верхнем углу)

## Сборка .exe файла:
1. ```pyinstaller --onefile --windowed --icon=.\icon.ico .\video_slider_viewer.py```