-- ============================================
-- PostGIS 初始化脚本
-- 在 Docker 首次启动时自动执行
-- ============================================

-- 启用 PostGIS 扩展（为后续空间查询做准备）
CREATE EXTENSION IF NOT EXISTS postgis;

-- 启用 uuid 扩展（用于会话 ID 等）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 确认扩展已加载
DO $$
BEGIN
    RAISE NOTICE '✅ PostGIS version: %', PostGIS_Version();
END
$$;
