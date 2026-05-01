#!/bin/bash
set -e

cd /var/www/lawdocs/frontend

git pull origin main

npm install --production=false
npm run build

pm2 restart lawdocs || pm2 start npm --name lawdocs -- start

echo "Deploy done."
