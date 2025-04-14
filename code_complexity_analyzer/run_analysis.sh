#!/bin/bash

mkdir -p results

for file in test_files/*.py; do

  filename=$(basename -- "$file")
  filename_without_ext="${filename%.*}"


  python3 analyzer.py "$file" > "results/${filename_without_ext}_analysis.txt"

  if [ $? -eq 0 ]; then
    echo "Анализ для $file завершен успешно. Результаты сохранены в results/${filename_without_ext}_analysis.txt"
  else
    echo "Ошибка при анализе файла $file"
  fi
done
