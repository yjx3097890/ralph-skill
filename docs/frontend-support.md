# 前端开发支持

Ralph Engine 提供了完整的前端开发支持，包括 Vue3 项目识别、Vite 构建工具集成、组件分析等功能。

## 功能特性

### 1. 项目识别

自动检测前端项目的技术栈：

- **框架识别**: Vue3, React, Angular
- **构建工具**: Vite, Webpack, Rollup
- **测试工具**: Vitest, Jest, Playwright
- **包管理器**: npm, yarn, pnpm

### 2. Vue3 组件分析

分析 Vue 组件的结构和特性：

- 检测 `<script>`, `<template>`, `<style>` 标签
- 识别 Composition API 和 Options API
- 提取 import 和 export 语句
- 检测 TypeScript 和 SCSS 使用

### 3. Vite 配置解析

解析 Vite 配置文件：

- 服务器端口和主机配置
- 构建输出目录
- Base URL 配置
- 插件列表

### 4. 构建和开发服务器

- 项目构建（生产和开发模式）
- 启动开发服务器
- 预览构建结果

## 使用示例

### 基本用法

```python
from pathlib import Path
from ralph.support import FrontendSupport

# 创建前端支持实例
project_path = Path("./my-vue3-project")
frontend_support = FrontendSupport(project_path)

# 检测项目信息
project_info = frontend_support.detect_framework()

print(f"框架: {project_info.framework}")
print(f"构建工具: {project_info.build_tool}")
print(f"包管理器: {project_info.package_manager}")
```

### 分析 Vue 组件

```python
# 分析单个组件
component_path = project_path / "src/components/HelloWorld.vue"
component_info = frontend_support.analyze_vue_component(component_path)

print(f"组件名: {component_info.component_name}")
print(f"使用 Composition API: {component_info.uses_composition_api}")
print(f"Script 语言: {component_info.script_lang}")

# 查找所有组件
components = frontend_support.find_vue_components()
print(f"找到 {len(components)} 个组件")
```

### 解析 Vite 配置

```python
# 解析 Vite 配置
vite_config = frontend_support.parse_vite_config()

if vite_config:
    print(f"服务器端口: {vite_config.server_port}")
    print(f"输出目录: {vite_config.build_outdir}")
    print(f"插件: {vite_config.plugins}")
```

### 使用 Vite 管理器

```python
from ralph.support import ViteManager
from ralph.models.enums import DependencyManager

# 创建 Vite 管理器
vite_manager = ViteManager(
    project_path=project_path,
    package_manager=DependencyManager.NPM
)

# 构建项目
build_result = vite_manager.build(mode="production")

if build_result.success:
    print(f"构建成功！")
    print(f"构建时间: {build_result.build_time:.2f}秒")
    print(f"输出大小: {build_result.output_size_bytes / 1024:.2f} KB")
else:
    print(f"构建失败: {build_result.errors}")

# 启动开发服务器
dev_server = vite_manager.start_dev_server(port=3000)
print(f"开发服务器运行在: {dev_server.url}")

# 停止开发服务器
vite_manager.stop_dev_server()
```

## 数据模型

### FrontendProjectInfo

前端项目信息：

```python
@dataclass
class FrontendProjectInfo:
    project_path: Path
    framework: FrameworkType
    framework_version: Optional[str]
    build_tool: BuildTool
    test_runner: Optional[TestRunner]
    e2e_runner: Optional[TestRunner]
    package_manager: DependencyManager
    has_package_json: bool
    has_vite_config: bool
    has_vue_config: bool
    dependencies: Dict[str, str]
    dev_dependencies: Dict[str, str]
```

### VueComponentInfo

Vue 组件信息：

```python
@dataclass
class VueComponentInfo:
    file_path: Path
    component_name: str
    has_script: bool
    has_template: bool
    has_style: bool
    script_lang: Optional[str]  # ts, js
    style_lang: Optional[str]  # css, scss, less
    uses_composition_api: bool
    uses_options_api: bool
    imports: List[str]
    exports: List[str]
```

### ViteConfig

Vite 配置信息：

```python
@dataclass
class ViteConfig:
    config_path: Path
    root: Optional[str]
    base: str
    build_outdir: str
    server_port: int
    server_host: str
    plugins: List[str]
    resolve_alias: Dict[str, str]
```

### BuildResult

构建结果：

```python
@dataclass
class BuildResult:
    success: bool
    build_time: float
    output_dir: Path
    output_size_bytes: int
    build_logs: str
    errors: List[str]
    warnings: List[str]
    assets: List[str]
```

## 支持的框架和工具

### 框架

- ✅ Vue 3
- ⏳ React（计划中）
- ⏳ Angular（计划中）

### 构建工具

- ✅ Vite
- ⏳ Webpack（计划中）
- ⏳ Rollup（计划中）

### 测试工具

- ✅ Vitest（检测）
- ✅ Playwright（检测）
- ⏳ Jest（计划中）

### 包管理器

- ✅ npm
- ✅ yarn
- ✅ pnpm

## 注意事项

1. **package.json 必需**: 所有前端项目必须包含 `package.json` 文件
2. **依赖检测**: 框架和工具的检测基于 `dependencies` 和 `devDependencies`
3. **配置解析**: Vite 配置解析使用正则表达式，可能无法处理复杂的配置
4. **组件分析**: Vue 组件分析基于文本解析，不执行代码

## 错误处理

```python
from ralph.support import FrontendSupport

try:
    frontend_support = FrontendSupport(project_path)
    project_info = frontend_support.detect_framework()
except FileNotFoundError as e:
    print(f"未找到 package.json: {e}")
except Exception as e:
    print(f"检测失败: {e}")
```

## 下一步

- 查看 [Vitest 集成文档](./vitest-integration.md)（待实现）
- 查看 [Playwright E2E 测试文档](./playwright-integration.md)（待实现）
- 查看 [完整 API 文档](./api-reference.md)
