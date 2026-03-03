"""
前端支持模块单元测试

测试 Vue3 项目识别、Vite 配置解析等功能。
"""

import json
import tempfile
from pathlib import Path

import pytest

from ralph.models.enums import (
    BuildTool,
    DependencyManager,
    FrameworkType,
    TestRunner,
)
from ralph.support.frontend_support import FrontendSupport


class TestFrontendSupport:
    """前端支持测试类"""
    
    @pytest.fixture
    def temp_project_dir(self):
        """创建临时项目目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def vue3_package_json(self):
        """Vue3 项目的 package.json 内容"""
        return {
            "name": "test-vue3-project",
            "version": "1.0.0",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview",
                "test": "vitest"
            },
            "dependencies": {
                "vue": "^3.3.4"
            },
            "devDependencies": {
                "vite": "^4.4.9",
                "vitest": "^0.34.6",
                "@playwright/test": "^1.40.0",
                "@vitejs/plugin-vue": "^4.3.4"
            }
        }
    
    def test_detect_vue3_framework(self, temp_project_dir, vue3_package_json):
        """测试检测 Vue3 框架"""
        # 创建 package.json
        package_json_path = temp_project_dir / "package.json"
        with open(package_json_path, 'w', encoding='utf-8') as f:
            json.dump(vue3_package_json, f, indent=2)
        
        # 创建 package-lock.json（表示使用 npm）
        (temp_project_dir / "package-lock.json").touch()
        
        # 创建 vite.config.js
        vite_config = """
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    host: 'localhost'
  }
})
"""
        (temp_project_dir / "vite.config.js").write_text(vite_config, encoding='utf-8')
        
        # 测试检测功能
        frontend_support = FrontendSupport(temp_project_dir)
        project_info = frontend_support.detect_framework()
        
        # 验证结果
        assert project_info.framework == FrameworkType.VUE3
        assert project_info.framework_version == "^3.3.4"
        assert project_info.build_tool == BuildTool.VITE
        assert project_info.test_runner == TestRunner.VITEST
        assert project_info.e2e_runner == TestRunner.PLAYWRIGHT
        assert project_info.package_manager == DependencyManager.NPM
        assert project_info.has_package_json is True
        assert project_info.has_vite_config is True
    
    def test_detect_package_manager_pnpm(self, temp_project_dir, vue3_package_json):
        """测试检测 pnpm 包管理器"""
        # 创建 package.json
        package_json_path = temp_project_dir / "package.json"
        with open(package_json_path, 'w', encoding='utf-8') as f:
            json.dump(vue3_package_json, f, indent=2)
        
        # 创建 pnpm-lock.yaml
        (temp_project_dir / "pnpm-lock.yaml").touch()
        
        frontend_support = FrontendSupport(temp_project_dir)
        project_info = frontend_support.detect_framework()
        
        assert project_info.package_manager == DependencyManager.PNPM
    
    def test_detect_package_manager_yarn(self, temp_project_dir, vue3_package_json):
        """测试检测 yarn 包管理器"""
        # 创建 package.json
        package_json_path = temp_project_dir / "package.json"
        with open(package_json_path, 'w', encoding='utf-8') as f:
            json.dump(vue3_package_json, f, indent=2)
        
        # 创建 yarn.lock
        (temp_project_dir / "yarn.lock").touch()
        
        frontend_support = FrontendSupport(temp_project_dir)
        project_info = frontend_support.detect_framework()
        
        assert project_info.package_manager == DependencyManager.YARN
    
    def test_parse_vite_config(self, temp_project_dir, vue3_package_json):
        """测试解析 Vite 配置"""
        # 创建 package.json
        package_json_path = temp_project_dir / "package.json"
        with open(package_json_path, 'w', encoding='utf-8') as f:
            json.dump(vue3_package_json, f, indent=2)
        
        # 创建 vite.config.js
        vite_config = """
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/app/',
  server: {
    port: 5173,
    host: '0.0.0.0'
  },
  build: {
    outDir: 'build'
  }
})
"""
        (temp_project_dir / "vite.config.js").write_text(vite_config, encoding='utf-8')
        
        frontend_support = FrontendSupport(temp_project_dir)
        vite_config_info = frontend_support.parse_vite_config()
        
        assert vite_config_info is not None
        assert vite_config_info.server_port == 5173
        assert vite_config_info.server_host == "0.0.0.0"
        assert vite_config_info.build_outdir == "build"
        assert vite_config_info.base == "/app/"
        assert "vue" in vite_config_info.plugins
    
    def test_analyze_vue_component(self, temp_project_dir):
        """测试分析 Vue 组件"""
        # 创建 Vue 组件文件
        component_content = """
<template>
  <div class="hello">
    <h1>{{ msg }}</h1>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const msg = ref('Hello Vue 3!')
</script>

<style scoped lang="scss">
.hello {
  color: #42b983;
}
</style>
"""
        component_path = temp_project_dir / "HelloWorld.vue"
        component_path.write_text(component_content, encoding='utf-8')
        
        frontend_support = FrontendSupport(temp_project_dir)
        component_info = frontend_support.analyze_vue_component(component_path)
        
        assert component_info.component_name == "HelloWorld"
        assert component_info.has_script is True
        assert component_info.has_template is True
        assert component_info.has_style is True
        assert component_info.script_lang == "ts"
        assert component_info.style_lang == "scss"
        assert component_info.uses_composition_api is True
        assert component_info.uses_options_api is False
        assert "vue" in component_info.imports
    
    def test_analyze_vue_component_options_api(self, temp_project_dir):
        """测试分析使用 Options API 的 Vue 组件"""
        component_content = """
<template>
  <div>{{ message }}</div>
</template>

<script>
export default {
  name: 'MyComponent',
  data() {
    return {
      message: 'Hello'
    }
  },
  methods: {
    greet() {
      console.log(this.message)
    }
  }
}
</script>
"""
        component_path = temp_project_dir / "MyComponent.vue"
        component_path.write_text(component_content, encoding='utf-8')
        
        frontend_support = FrontendSupport(temp_project_dir)
        component_info = frontend_support.analyze_vue_component(component_path)
        
        assert component_info.uses_composition_api is False
        assert component_info.uses_options_api is True
        assert "default" in component_info.exports
    
    def test_find_vue_components(self, temp_project_dir):
        """测试查找 Vue 组件"""
        # 创建 src 目录结构
        src_dir = temp_project_dir / "src"
        src_dir.mkdir()
        components_dir = src_dir / "components"
        components_dir.mkdir()
        
        # 创建多个 Vue 组件
        (components_dir / "Button.vue").write_text("<template><button></button></template>", encoding='utf-8')
        (components_dir / "Card.vue").write_text("<template><div></div></template>", encoding='utf-8')
        (src_dir / "App.vue").write_text("<template><div id='app'></div></template>", encoding='utf-8')
        
        frontend_support = FrontendSupport(temp_project_dir)
        components = frontend_support.find_vue_components()
        
        assert len(components) == 3
        component_names = [c.component_name for c in components]
        assert "Button" in component_names
        assert "Card" in component_names
        assert "App" in component_names
    
    def test_missing_package_json(self, temp_project_dir):
        """测试缺少 package.json 的情况"""
        frontend_support = FrontendSupport(temp_project_dir)
        
        with pytest.raises(FileNotFoundError) as exc_info:
            frontend_support.detect_framework()
        
        assert "package.json" in str(exc_info.value)
    
    def test_get_package_manager_command(self, temp_project_dir):
        """测试获取包管理器命令"""
        frontend_support = FrontendSupport(temp_project_dir)
        
        assert frontend_support.get_package_manager_command(DependencyManager.NPM) == "npm"
        assert frontend_support.get_package_manager_command(DependencyManager.YARN) == "yarn"
        assert frontend_support.get_package_manager_command(DependencyManager.PNPM) == "pnpm"
