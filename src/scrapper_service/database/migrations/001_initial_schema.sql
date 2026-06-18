-- Таблица чатов
CREATE TABLE IF NOT EXISTS chats (
    id BIGINT PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Таблица ссылок
CREATE TABLE IF NOT EXISTS links (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    resource_type VARCHAR(20) CHECK (resource_type IN ('github', 'stackoverflow')),
    resource_id VARCHAR(255),
    last_checked TIMESTAMP WITH TIME ZONE,
    last_updated TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Таблица подписок
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    link_id INTEGER NOT NULL REFERENCES links(id) ON DELETE CASCADE,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(chat_id, link_id)
);

-- Таблица истории обновлений
CREATE TABLE IF NOT EXISTS updates (
    id SERIAL PRIMARY KEY,
    link_id INTEGER NOT NULL REFERENCES links(id) ON DELETE CASCADE,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP WITH TIME ZONE,
    had_changes BOOLEAN DEFAULT FALSE
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_links_url ON links(url);
CREATE INDEX IF NOT EXISTS idx_links_resource_type ON links(resource_type);
CREATE INDEX IF NOT EXISTS idx_links_last_updated ON links(last_updated);
CREATE INDEX IF NOT EXISTS idx_subscriptions_chat_id ON subscriptions(chat_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_link_id ON subscriptions(link_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_tags ON subscriptions USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_updates_link_id ON updates(link_id);
CREATE INDEX IF NOT EXISTS idx_updates_checked_at ON updates(checked_at);
