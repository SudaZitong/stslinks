"""兼容旧启动方式，实际入口是 cli.py / webapp.py。"""
from cli import main

if __name__ == "__main__":
    raise SystemExit(main())
