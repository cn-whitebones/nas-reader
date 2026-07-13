"""应用配置:全部从环境变量读取,便于 docker 部署。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 基础
    app_name: str = "NAS Reader"
    api_prefix: str = "/api/v1"
    debug: bool = False

    # 数据库(async 驱动)
    database_url: str = "postgresql+asyncpg://nasreader:nasreader@postgres:5432/nasreader"

    # JWT
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 天
    refresh_token_expire_days: int = 30

    # 存储路径(容器内)
    data_root: str = "/data"          # volume 映射的书目录根
    cover_dir: str = "/app/storage/covers"  # 封面缩略图缓存目录

    # 扫描
    scan_default_interval_minutes: int = 60
    scan_hash_read_bytes: int = 1024 * 1024  # 计算 file_hash 读取的字节数(首段)

    # 刮削
    scrape_timeout_seconds: int = 15
    douban_cookie: str = ""  # 可选:提高豆瓣抓取成功率


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
