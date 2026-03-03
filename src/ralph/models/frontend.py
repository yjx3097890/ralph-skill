"""
前端开发相关数据模型

定义前端项目配置、测试结果、构建结果等数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .enums import (
    BrowserType,
    BuildTool,
    DependencyManager,
    FrameworkType,
    ScreenshotMode,
    TestRunner,
    TraceMode,
    VideoMode,
)


@dataclass
class FrontendProjectInfo:
    """前端项目信息"""
    project_path: Path
    framework: FrameworkType
    framework_version: Optional[str] = None
    build_tool: BuildTool = BuildTool.VITE
    test_runner: Optional[TestRunner] = None
    e2e_runner: Optional[TestRunner] = None
    package_manager: DependencyManager = DependencyManager.NPM
    has_package_json: bool = False
    has_vite_config: bool = False
    has_vue_config: bool = False
    dependencies: Dict[str, str] = field(default_factory=dict)
    dev_dependencies: Dict[str, str] = field(default_factory=dict)


@dataclass
class VueComponentInfo:
    """Vue 组件信息"""
    file_path: Path
    component_name: str
    has_script: bool = False
    has_template: bool = False
    has_style: bool = False
    script_lang: Optional[str] = None  # ts, js
    style_lang: Optional[str] = None  # css, scss, less
    uses_composition_api: bool = False
    uses_options_api: bool = False
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)


@dataclass
class ViteConfig:
    """Vite 配置信息"""
    config_path: Path
    root: Optional[str] = None
    base: str = "/"
    build_outdir: str = "dist"
    server_port: int = 3000
    server_host: str = "localhost"
    plugins: List[str] = field(default_factory=list)
    resolve_alias: Dict[str, str] = field(default_factory=dict)


@dataclass
class BuildResult:
    """构建结果"""
    success: bool
    build_time: float
    output_dir: Path
    output_size_bytes: int
    build_logs: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    assets: List[str] = field(default_factory=list)


@dataclass
class DevServerInfo:
    """开发服务器信息"""
    pid: int
    port: int
    host: str
    url: str
    started_at: datetime
    is_running: bool = True


@dataclass
class TestResult:
    """测试结果基类"""
    success: bool
    test_type: str  # unit, integration, e2e
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    execution_time: float
    test_output: str
    coverage: Optional['CoverageReport'] = None
    failed_test_details: List['FailedTestDetail'] = field(default_factory=list)


@dataclass
class CoverageReport:
    """测试覆盖率报告"""
    total_coverage: float
    line_coverage: float
    branch_coverage: float
    function_coverage: float
    statement_coverage: float
    file_coverage: Dict[str, 'FileCoverage'] = field(default_factory=dict)


@dataclass
class FileCoverage:
    """文件覆盖率"""
    file_path: str
    coverage_percent: float
    lines_covered: int
    lines_total: int
    branches_covered: int
    branches_total: int
    functions_covered: int
    functions_total: int
    uncovered_lines: List[int] = field(default_factory=list)


@dataclass
class FailedTestDetail:
    """失败测试详情"""
    test_name: str
    test_file: str
    error_message: str
    stack_trace: str
    line_number: Optional[int] = None
    expected: Optional[str] = None
    actual: Optional[str] = None


@dataclass
class VitestConfig:
    """Vitest 配置"""
    test_dir: str = "tests"
    coverage: bool = True
    coverage_threshold: float = 80.0
    reporters: List[str] = field(default_factory=lambda: ["default", "json"])
    globals: bool = True
    environment: str = "jsdom"  # jsdom, happy-dom, node
    timeout: int = 5000
    threads: bool = True
    isolate: bool = True


@dataclass
class PlaywrightConfig:
    """Playwright E2E 测试配置"""
    browsers: List[BrowserType] = field(default_factory=lambda: [
        BrowserType.CHROMIUM,
        BrowserType.FIREFOX,
        BrowserType.WEBKIT
    ])
    headless: bool = True
    timeout: int = 30000
    retries: int = 2
    screenshot_mode: ScreenshotMode = ScreenshotMode.ONLY_ON_FAILURE
    video_mode: VideoMode = VideoMode.RETAIN_ON_FAILURE
    trace_mode: TraceMode = TraceMode.ON_FIRST_RETRY
    base_url: str = "http://localhost:3000"
    test_dir: str = "tests/e2e"
    output_dir: str = "test-results"
    workers: int = 4
    fully_parallel: bool = True


@dataclass
class E2ETestResult(TestResult):
    """E2E 测试结果"""
    browser_results: Dict[str, 'BrowserTestResult'] = field(default_factory=dict)
    screenshots: List['Screenshot'] = field(default_factory=list)
    videos: List['VideoFile'] = field(default_factory=list)
    traces: List['TraceFile'] = field(default_factory=list)


@dataclass
class BrowserTestResult:
    """浏览器测试结果"""
    browser: BrowserType
    version: str
    success: bool
    tests_run: int
    tests_passed: int
    tests_failed: int
    execution_time: float
    failed_tests: List['FailedE2ETest'] = field(default_factory=list)


@dataclass
class FailedE2ETest:
    """失败的 E2E 测试"""
    test_name: str
    browser: BrowserType
    error_message: str
    stack_trace: str
    screenshot_path: Optional[str] = None
    video_path: Optional[str] = None
    trace_path: Optional[str] = None
    retry_count: int = 0


@dataclass
class Screenshot:
    """截图信息"""
    test_name: str
    browser: BrowserType
    file_path: Path
    timestamp: datetime
    test_status: str  # passed, failed, skipped
    size_bytes: int


@dataclass
class VideoFile:
    """视频文件信息"""
    test_name: str
    browser: BrowserType
    file_path: Path
    timestamp: datetime
    duration_seconds: float
    size_bytes: int


@dataclass
class TraceFile:
    """追踪文件信息"""
    test_name: str
    browser: BrowserType
    file_path: Path
    timestamp: datetime
    size_bytes: int


@dataclass
class PackageJsonInfo:
    """package.json 信息"""
    name: str
    version: str
    scripts: Dict[str, str] = field(default_factory=dict)
    dependencies: Dict[str, str] = field(default_factory=dict)
    dev_dependencies: Dict[str, str] = field(default_factory=dict)
    engines: Dict[str, str] = field(default_factory=dict)
