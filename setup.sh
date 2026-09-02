#!/bin/bash
set -e

if [ ! -f requirements.txt ]; then
for d in .. $HOME $HOME/* $HOME/*/* /workspace /workspace/* /workspace/*/*; do
if [ -f $d/requirements.txt ]; then cd $d; break; fi
done
fi
if [ ! -f requirements.txt ]; then
find / -maxdepth 7 -name manage.py -not -path '*/site-packages/*' 2>/dev/null > /tmp/_manage || true
while read -r p; do cd ${p%/manage.py}; break; done < /tmp/_manage
fi

if [ ! -f requirements.txt ]; then
echo ERROR: no encontre requirements.txt. Estoy en: $PWD
ls -a
exit 1
fi
echo Instalando desde: $PWD

pip install -r requirements.txt || pip install --break-system-packages -r requirements.txt

python manage.py migrate --noinput
python manage.py seed_groups || true

echo Entorno listo.
