"""
前端开发支持模块

提供 Vue3 项目识别、Vite 构建工具集成、Vitest 测试等功能。
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ralph.models.enums import (
    BuildTool,
    DependencyManager,
    FrameworkType,
    TestRunner,
)
from ralph.models.frontend import (
    BuildResult,
    DevServerInfo,
    FrontendProjectInfo,
    PackageJsonInfo,
    TestResult,
    ViteConfig,
    VitestConfig,
    VueComponentInfo,
)
from ralph.support.vitest_manager import VitestManager
from ralph.support.playwright_manager import PlaywrightManager


class FrontendSupport:
    """前端开发支持类"""
    
    def __init__(self, project_path: Path):
        """
        初始化前端支持
        
        Args:
            project_path: 项目根目录路径
        """
        self.project_path = Path(project_path)
        self.vitest_manager: Optional[VitestManager] = None
        self.playwright_manager: Optional[PlaywrightManager] = None
    
    def detect_framework(self) -> FrontendProjectInfo:
        """
        检测前端框架和项目配置
        
        Returns:
            FrontendProjectInfo: 前端项目信息
        """
        # 检查 package.json 是否存在
        package_json_path = self.project_path / "package.json"
        if not package_json_path.exists():
            raise FileNotFoundError(f"未找到 package.json: {package_json_path}")
        
        # 解析 package.json
        package_info = self._parse_package_json(package_json_path)
        
        # 检测框架类型
        framework, framework_version = self._detect_framework_from_dependencies(
            package_info.dependencies,
            package_info.dev_dependencies
        )
        
        # 检测构建工具
        build_tool = self._detect_build_tool(
            package_info.dependencies,
            package_info.dev_dependencies
        )
        
        # 检测测试运行器
        test_runner = self._detect_test_runner(
            package_info.dependencies,
            package_info.dev_dependencies
        )
        
        # 检测 E2E 测试运行器
        e2e_runner = self._detect_e2e_runner(
            package_info.dependencies,
            package_info.dev_dependencies
        )
        
        # 检测包管理器
        package_manager = self._detect_package_manager()
        
        # 检查配置文件
        has_vite_config = self._check_vite_config_exists()
        has_vue_config = (self.project_path / "vue.config.js").exists() or \
                        (self.project_path / "vue.config.ts").exists()
        
        return FrontendProjectInfo(
            project_path=self.project_path,
            framework=framework,
            framework_version=framework_version,
            build_tool=build_tool,
            test_runner=test_runner,
            e2e_runner=e2e_runner,
            package_manager=package_manager,
            has_package_json=True,
            has_vite_config=has_vite_config,
            has_vue_config=has_vue_config,
            dependencies=package_info.dependencies,
            dev_dependencies=package_info.dev_dependencies
        )
    
    def _parse_package_json(self, path: Path) -> PackageJsonInfo:
        """解析 package.json 文件"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return PackageJsonInfo(
            name=data.get('name', ''),
            version=data.get('version', ''),
            scripts=data.get('scripts', {}),
            dependencies=data.get('dependencies', {}),
            dev_dependencies=data.get('devDependencies', {}),
            engines=data.get('engines', {})
        )
    
    def _detect_framework_from_dependencies(
        self,
        dependencies: Dict[str, str],
        dev_dependencies: Dict[str, str]
    ) -> Tuple[FrameworkType, Optional[str]]:
        """从依赖中检测框架类型和版本"""
        all_deps = {**dependencies, **dev_dependencies}
        
        # 检测 Vue 3
        if 'vue' in all_deps:
            version = all_deps['vue']
            # Vue 3 版本号以 3 开头
            if version.startswith('^3') or version.startswith('~3') or version.startswith('3'):
                return FrameworkType.VUE3, version
        
        # 检测 React
        if 'react' in all_deps:
            return FrameworkType.REACT, all_deps['react']
        
        # 检测 Angular
        if '@angular/core' in all_deps:
            return FrameworkType.ANGULAR, all_deps['@angular/core']
        
        return FrameworkType.NONE, None
    
    def _detect_build_tool(
        self,
        dependencies: Dict[str, str],
        dev_dependencies: Dict[str, str]
    ) -> BuildTool:
        """检测构建工具"""
        all_deps = {**dependencies, **dev_dependencies}
        
        if 'vite' in all_deps:
            return BuildTool.VITE
        elif 'webpack' in all_deps or '@vue/cli-service' in all_deps:
            return BuildTool.WEBPACK
        elif 'rollup' in all_deps:
            return BuildTool.ROLLUP
        
        return BuildTool.NONE
    
    def _detect_test_runner(
        self,
        dependencies: Dict[str, str],
        dev_dependencies: Dict[str, str]
    ) -> Optional[TestRunner]:
        """检测单元测试运行器"""
        all_deps = {**dependencies, **dev_dependencies}
        
        if 'vitest' in all_deps:
            return TestRunner.VITEST
        elif 'jest' in all_deps or '@vue/test-utils' in all_deps:
            return TestRunner.JEST
        
        return None
    
    def _detect_e2e_runner(
        self,
        dependencies: Dict[str, str],
        dev_dependencies: Dict[str, str]
    ) -> Optional[TestRunner]:
        """检测 E2E 测试运行器"""
        all_deps = {**dependencies, **dev_dependencies}
        
        if '@playwright/test' in all_deps or 'playwright' in all_deps:
            return TestRunner.PLAYWRIGHT
        
        return None
    
    def _detect_package_manager(self) -> DependencyManager:
        """检测包管理器"""
        # 检查锁文件
        if (self.project_path / "pnpm-lock.yaml").exists():
            return DependencyManager.PNPM
        elif (self.project_path / "yarn.lock").exists():
            return DependencyManager.YARN
        elif (self.project_path / "package-lock.json").exists():
            return DependencyManager.NPM
        
        # 默认使用 npm
        return DependencyManager.NPM
    
    def _check_vite_config_exists(self) -> bool:
        """检查 Vite 配置文件是否存在"""
        vite_configs = [
            "vite.config.js",
            "vite.config.ts",
            "vite.config.mjs",
            "vite.config.cjs"
        ]
        
        return any((self.project_path / config).exists() for config in vite_configs)
    
    def parse_vite_config(self) -> Optional[ViteConfig]:
        """
        解析 Vite 配置文件
        
        Returns:
            ViteConfig: Vite 配置信息，如果不存在则返回 None
        """
        # 查找 Vite 配置文件
        vite_config_files = [
            "vite.config.js",
            "vite.config.ts",
            "vite.config.mjs",
            "vite.config.cjs"
        ]
        
        config_path = None
        for config_file in vite_config_files:
            path = self.project_path / config_file
            if path.exists():
                config_path = path
                break
        
        if not config_path:
            return None
        
        # 读取配置文件内容
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取配置信息（简单的正则匹配）
        vite_config = ViteConfig(config_path=config_path)
        
        # 提取 server.port
        port_match = re.search(r'port\s*:\s*(\d+)', content)
        if port_match:
            vite_config.server_port = int(port_match.group(1))
        
        # 提取 server.host
        host_match = re.search(r'host\s*:\s*[\'"]([^\'"]+)[\'"]', content)
        if host_match:
            vite_config.server_host = host_match.group(1)
        
        # 提取 build.outDir
        outdir_match = re.search(r'outDir\s*:\s*[\'"]([^\'"]+)[\'"]', content)
        if outdir_match:
            vite_config.build_outdir = outdir_match.group(1)
        
        # 提取 base
        base_match = re.search(r'base\s*:\s*[\'"]([^\'"]+)[\'"]', content)
        if base_match:
            vite_config.base = base_match.group(1)
        
        # 提取插件（简单检测）
        if 'vue()' in content:
            vite_config.plugins.append('vue')
        if 'react()' in content:
            vite_config.plugins.append('react')
        
        return vite_config
    
    def analyze_vue_component(self, component_path: Path) -> VueComponentInfo:
        """
        分析 Vue 组件结构
        
        Args:
            component_path: Vue 组件文件路径
            
        Returns:
            VueComponentInfo: Vue 组件信息
        """
        if not component_path.exists():
            raise FileNotFoundError(f"组件文件不存在: {component_path}")
        
        with open(component_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取组件名称
        component_name = component_path.stem
        
        # 检查是否有 <script> 标签
        has_script = '<script' in content
        
        # 检查是否有 <template> 标签
        has_template = '<template' in content
        
        # 检查是否有 <style> 标签
        has_style = '<style' in content
        
        # 检测 script 语言
        script_lang = None
        if has_script:
            script_lang_match = re.search(r'<script[^>]*lang=[\'"](\w+)[\'"]', content)
            if script_lang_match:
                script_lang = script_lang_match.group(1)
            else:
                script_lang = 'js'
        
        # 检测 style 语言
        style_lang = None
        if has_style:
            style_lang_match = re.search(r'<style[^>]*lang=[\'"](\w+)[\'"]', content)
            if style_lang_match:
                style_lang = style_lang_match.group(1)
            else:
                style_lang = 'css'
        
        # 检测是否使用 Composition API
        uses_composition_api = '<script setup' in content or 'setup()' in content
        
        # 检测是否使用 Options API
        uses_options_api = 'export default' in content and not uses_composition_api
        
        # 提取 import 语句
        imports = re.findall(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]', content)
        
        # 提取 export 语句
        exports = []
        if 'export default' in content:
            exports.append('default')
        export_matches = re.findall(r'export\s+(?:const|let|var|function|class)\s+(\w+)', content)
        exports.extend(export_matches)
        
        return VueComponentInfo(
            file_path=component_path,
            component_name=component_name,
            has_script=has_script,
            has_template=has_template,
            has_style=has_style,
            script_lang=script_lang,
            style_lang=style_lang,
            uses_composition_api=uses_composition_api,
            uses_options_api=uses_options_api,
            imports=imports,
            exports=exports
        )
    
    def find_vue_components(self, directory: Optional[Path] = None) -> List[VueComponentInfo]:
        """
        查找目录下的所有 Vue 组件
        
        Args:
            directory: 搜索目录，默认为 src 目录
            
        Returns:
            List[VueComponentInfo]: Vue 组件信息列表
        """
        if directory is None:
            directory = self.project_path / "src"
        
        if not directory.exists():
            return []
        
        components = []
        for vue_file in directory.rglob("*.vue"):
            try:
                component_info = self.analyze_vue_component(vue_file)
                components.append(component_info)
            except Exception as e:
                # 记录错误但继续处理其他组件
                print(f"分析组件失败 {vue_file}: {e}")
        
        return components
    
    def get_package_manager_command(self, package_manager: DependencyManager) -> str:
        """获取包管理器命令"""
        if package_manager == DependencyManager.NPM:
            return "npm"
        elif package_manager == DependencyManager.YARN:
            return "yarn"
        elif package_manager == DependencyManager.PNPM:
            return "pnpm"
        else:
            return "npm"
    
    def install_dependencies(self, package_manager: Optional[DependencyManager] = None) -> bool:
        """
        安装项目依赖
        
        Args:
            package_manager: 包管理器，如果为 None 则自动检测
            
        Returns:
            bool: 是否安装成功
        """
        if package_manager is None:
            package_manager = self._detect_package_manager()
        
        cmd = self.get_package_manager_command(package_manager)
        
        try:
            result = subprocess.run(
                [cmd, "install"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 分钟超时
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("依赖安装超时")
            return False
        except Exception as e:
            print(f"依赖安装失败: {e}")
            return False
    
    def run_unit_tests(
        self,
        test_path: Optional[str] = None,
        config: Optional[VitestConfig] = None,
        timeout: int = 300
    ) -> TestResult:
        """
        运行前端单元测试（Vitest）
        
        Args:
            test_path: 测试文件或目录路径，None 表示运行所有测试
            config: Vitest 配置
            timeout: 超时时间（秒）
            
        Returns:
            TestResult: 测试结果
        """
        # 检测项目信息
        project_info = self.detect_framework()
        
        # 检查是否使用 Vitest
        if project_info.test_runner != TestRunner.VITEST:
            raise ValueError(f"项目未使用 Vitest 测试框架，当前测试运行器: {project_info.test_runner}")
        
        # 初始化 Vitest 管理器
        if self.vitest_manager is None:
            self.vitest_manager = VitestManager(
                self.project_path,
                project_info.package_manager
            )
        
        # 运行测试
        return self.vitest_manager.run_tests(test_path, config, timeout)
    
    def extract_test_error_summary(self, test_result: TestResult) -> str:
        """
        提取测试错误摘要
        
        Args:
            test_result: 测试结果
            
        Returns:
            str: 错误摘要
        """
        if self.vitest_manager is None:
            # 如果没有初始化 Vitest 管理器，创建一个临时的
            project_info = self.detect_framework()
            self.vitest_manager = VitestManager(
                self.project_path,
                project_info.package_manager
            )
        
        return self.vitest_manager.extract_error_summary(test_result)
    
    def generate_test_report(self, test_result: TestResult) -> Dict[str, any]:
        """
        生成测试报告
        
        Args:
            test_result: 测试结果
            
        Returns:
            Dict: 测试报告（JSON 格式）
        """
        if self.vitest_manager is None:
            # 如果没有初始化 Vitest 管理器，创建一个临时的
            project_info = self.detect_framework()
            self.vitest_manager = VitestManager(
                self.project_path,
                project_info.package_manager
            )
        
        return self.vitest_manager.generate_test_report(test_result)
    
    def run_e2e_tests(
        self,
        test_files: Optional[List[str]] = None,
        config: Optional['PlaywrightConfig'] = None,
        timeout: int = 600
    ) -> 'E2ETestResult':
        """
        运行 Playwright E2E 测试
        
        Args:
            test_files: 测试文件列表，None 表示运行所有测试
            config: Playwright 配置
            timeout: 超时时间（秒）
            
        Returns:
            E2ETestResult: E2E 测试结果
        """
        # 检测项目信息
        project_info = self.detect_framework()
        
        # 检查是否使用 Playwright
        if project_info.e2e_runner != TestRunner.PLAYWRIGHT:
            raise ValueError(
                f"项目未使用 Playwright E2E 测试框架，当前 E2E 运行器: {project_info.e2e_runner}"
            )
        
        # 初始化 Playwright 管理器
        if self.playwright_manager is None:
            self.playwright_manager = PlaywrightManager(
                self.project_path,
                project_info.package_manager
            )
        
        # 运行测试
        return self.playwright_manager.run_test_suite(test_files, config, timeout)
    
    def extract_e2e_error_summary(self, test_result: 'E2ETestResult') -> str:
        """
        提取 E2E 测试错误摘要
        
        Args:
            test_result: E2E 测试结果
            
        Returns:
            str: 错误摘要
        """
        if self.playwright_manager is None:
            # 如果没有初始化 Playwright 管理器，创建一个临时的
            project_info = self.detect_framework()
            self.playwright_manager = PlaywrightManager(
                self.project_path,
                project_info.package_manager
            )
        
        return self.playwright_manager.extract_error_summary(test_result)
    
    def generate_e2e_test_report(self, test_result: 'E2ETestResult') -> Dict[str, any]:
        """
        生成 E2E 测试报告
        
        Args:
            test_result: E2E 测试结果
            
        Returns:
            Dict: 测试报告（JSON 格式）
        """
        if self.playwright_manager is None:
            # 如果没有初始化 Playwright 管理器，创建一个临时的
            project_info = self.detect_framework()
            self.playwright_manager = PlaywrightManager(
                self.project_path,
                project_info.package_manager
            )
        
        return self.playwright_manager.generate_test_report(test_result)
