.PHONY: help install test lint format clean coverage

# 默认目标
help:
	@echo "Ralph Skill 开发命令"
	@echo ""
	@echo "可用命令:"
	@echo "  make install    - 安装项目依赖"
	@echo "  make test       - 运行所有测试"
	@echo "  make lint       - 运行代码检查"
	@echo "  make format     - 格式化代码"
	@echo "  make coverage   - 生成测试覆盖率报告"
	@echo "  make clean      - 清理临时文件"

# 安装依赖
install:
	poetry install

# 运行测试
test:
	poetry run pytest -v

# 运行代码检查
lint:
	poetry run flake8 src tests
	poetry run mypy src

# 格式化代码
format:
	poetry run black src tests
	poetry run isort src tests

# 生成覆盖率报告
coverage:
	poetry run pytest --cov=ralph --cov-report=html --cov-report=term
	@echo "覆盖率报告已生成到 htmlcov/index.html"

# 清理临时文件
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build dist htmlcov .coverage
	@echo "清理完成"
