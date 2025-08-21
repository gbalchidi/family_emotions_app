#!/bin/bash

# Family Emotions App - Quick Setup Script
# Этот скрипт поможет быстро настроить проект

echo "🤖 Family Emotions Bot - Quick Setup"
echo "===================================="
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для проверки команд
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Проверка Python
echo "1️⃣ Проверка Python..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
    echo -e "${GREEN}✓ Python установлен (версия $PYTHON_VERSION)${NC}"
else
    echo -e "${RED}✗ Python не установлен. Установите Python 3.11+${NC}"
    exit 1
fi

# 2. Проверка Poetry
echo ""
echo "2️⃣ Проверка Poetry..."
if command_exists poetry; then
    echo -e "${GREEN}✓ Poetry установлен${NC}"
else
    echo -e "${YELLOW}⚠ Poetry не установлен. Устанавливаю...${NC}"
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# 3. Создание .env файла
echo ""
echo "3️⃣ Настройка окружения..."
if [ -f .env ]; then
    echo -e "${YELLOW}⚠ Файл .env уже существует${NC}"
    read -p "Перезаписать? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Пропускаю создание .env"
    else
        cp .env .env.backup
        echo -e "${GREEN}✓ Создана резервная копия .env.backup${NC}"
    fi
else
    echo "Создаю .env файл..."
    cp .env.example .env
    echo -e "${GREEN}✓ Создан .env файл из шаблона${NC}"
fi

# 4. Сбор необходимых данных
echo ""
echo "4️⃣ Введите необходимые данные:"
echo "================================"

# Telegram Bot Token
echo ""
read -p "📱 Telegram Bot Token (получите у @BotFather): " TELEGRAM_TOKEN
if [ ! -z "$TELEGRAM_TOKEN" ]; then
    sed -i.bak "s/your_telegram_bot_token_here/$TELEGRAM_TOKEN/g" .env
    echo -e "${GREEN}✓ Telegram token сохранен${NC}"
fi

# Database выбор
echo ""
echo "🗄️ Выберите тип базы данных:"
echo "1) Supabase (облачная, рекомендуется)"
echo "2) Локальная PostgreSQL"
echo "3) Пропустить"
read -p "Выбор (1-3): " DB_CHOICE

case $DB_CHOICE in
    1)
        echo ""
        echo "Для Supabase:"
        echo "1. Зайдите на https://supabase.com"
        echo "2. Создайте проект"
        echo "3. Скопируйте Database URL из Settings → Database"
        echo ""
        read -p "Database URL: " DATABASE_URL
        if [ ! -z "$DATABASE_URL" ]; then
            sed -i.bak "s|postgresql://user:password@host:port/database|$DATABASE_URL|g" .env
            echo -e "${GREEN}✓ Database URL сохранен${NC}"
        fi
        
        read -p "Supabase Project URL: " SUPABASE_URL
        if [ ! -z "$SUPABASE_URL" ]; then
            sed -i.bak "s|https://your-project.supabase.co|$SUPABASE_URL|g" .env
            echo -e "${GREEN}✓ Supabase URL сохранен${NC}"
        fi
        
        read -p "Supabase Anon Key: " SUPABASE_KEY
        if [ ! -z "$SUPABASE_KEY" ]; then
            sed -i.bak "s|your_supabase_anon_key|$SUPABASE_KEY|g" .env
            echo -e "${GREEN}✓ Supabase key сохранен${NC}"
        fi
        ;;
    2)
        echo "Используется локальная PostgreSQL"
        read -p "Database URL (postgresql://user:pass@localhost:5432/dbname): " DATABASE_URL
        if [ ! -z "$DATABASE_URL" ]; then
            sed -i.bak "s|postgresql://user:password@host:port/database|$DATABASE_URL|g" .env
            echo -e "${GREEN}✓ Database URL сохранен${NC}"
        fi
        ;;
    3)
        echo "Настройка БД пропущена"
        ;;
esac

# Claude API
echo ""
read -p "🤖 Claude API Key (получите на console.anthropic.com): " CLAUDE_KEY
if [ ! -z "$CLAUDE_KEY" ]; then
    sed -i.bak "s/your_anthropic_api_key_here/$CLAUDE_KEY/g" .env
    echo -e "${GREEN}✓ Claude API key сохранен${NC}"
fi

# Redis
echo ""
echo "💾 Redis настройка:"
echo "1) Использовать локальный Redis (localhost:6379)"
echo "2) Использовать Upstash (облачный)"
echo "3) Ввести свой URL"
echo "4) Пропустить"
read -p "Выбор (1-4): " REDIS_CHOICE

case $REDIS_CHOICE in
    1)
        echo "Используется локальный Redis"
        ;;
    2)
        echo "Зайдите на https://upstash.com и создайте базу"
        read -p "Redis URL от Upstash: " REDIS_URL
        if [ ! -z "$REDIS_URL" ]; then
            sed -i.bak "s|redis://localhost:6379/0|$REDIS_URL|g" .env
            echo -e "${GREEN}✓ Redis URL сохранен${NC}"
        fi
        ;;
    3)
        read -p "Redis URL: " REDIS_URL
        if [ ! -z "$REDIS_URL" ]; then
            sed -i.bak "s|redis://localhost:6379/0|$REDIS_URL|g" .env
            echo -e "${GREEN}✓ Redis URL сохранен${NC}"
        fi
        ;;
    4)
        echo "Redis настройка пропущена"
        ;;
esac

# Генерация секретных ключей
echo ""
echo "5️⃣ Генерация секретных ключей..."
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 16)
sed -i.bak "s/your_secret_key_here_at_least_32_characters/$SECRET_KEY/g" .env
sed -i.bak "s/your_encryption_key_here_32_characters/$ENCRYPTION_KEY/g" .env
echo -e "${GREEN}✓ Секретные ключи сгенерированы${NC}"

# 5. Установка зависимостей
echo ""
echo "6️⃣ Установка зависимостей..."
read -p "Установить зависимости сейчас? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    poetry install
    echo -e "${GREEN}✓ Зависимости установлены${NC}"
fi

# 6. Создание таблиц в БД
echo ""
echo "7️⃣ Создание таблиц в базе данных..."
if [ ! -z "$DATABASE_URL" ]; then
    echo "Выполните SQL из файла scripts/init.sql в вашей базе данных"
    echo "Для Supabase: SQL Editor → вставьте содержимое init.sql"
    echo ""
    read -p "Таблицы созданы? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}✓ База данных готова${NC}"
    else
        echo -e "${YELLOW}⚠ Не забудьте создать таблицы перед запуском!${NC}"
    fi
fi

# 7. Финальная проверка
echo ""
echo "======================================"
echo "📋 ИТОГОВАЯ ПРОВЕРКА:"
echo ""

# Проверка .env файла
if [ -f .env ]; then
    # Проверка заполнения ключевых переменных
    if grep -q "your_telegram_bot_token_here" .env; then
        echo -e "${RED}✗ Telegram Bot Token не настроен${NC}"
    else
        echo -e "${GREEN}✓ Telegram Bot Token настроен${NC}"
    fi
    
    if grep -q "your_anthropic_api_key_here" .env; then
        echo -e "${RED}✗ Claude API Key не настроен${NC}"
    else
        echo -e "${GREEN}✓ Claude API Key настроен${NC}"
    fi
    
    if grep -q "postgresql://user:password" .env; then
        echo -e "${YELLOW}⚠ Database URL не настроен${NC}"
    else
        echo -e "${GREEN}✓ Database URL настроен${NC}"
    fi
fi

# 8. Запуск
echo ""
echo "======================================"
echo "🚀 ГОТОВО К ЗАПУСКУ!"
echo ""
echo "Команды для запуска:"
echo ""
echo "  📦 Локальная разработка:"
echo "  poetry run python main.py"
echo ""
echo "  🐳 Docker:"
echo "  docker build -t family-emotions ."
echo "  docker run --env-file .env family-emotions"
echo ""
echo "  ☁️ Production (Coolify):"
echo "  1. Push в GitHub: git push origin main"
echo "  2. Deploy в Coolify Dashboard"
echo ""
echo "======================================"
echo ""
echo "📚 Документация: docs/"
echo "❓ Помощь: DEPLOYMENT_GUIDE.md"
echo "🐛 Issues: https://github.com/gbalchidi/family_emotions_app/issues"
echo ""
echo "Удачного запуска! 🎉"