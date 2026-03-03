"""
前端项目检测示例

演示如何使用 FrontendSupport 检测 Vue3 项目和 Vite 配置。
"""

from pathlib import Path

from ralph.support import FrontendSupport


def main():
    """主函数"""
    # 假设项目路径
    project_path = Path("./my-vue3-project")
    
    # 如果项目不存在，打印提示信息
    if not project_path.exists():
        print(f"项目路径不存在: {project_path}")
        print("\n使用示例：")
        print("1. 创建一个 Vue3 项目")
        print("2. 将项目路径传递给 FrontendSupport")
        return
    
    # 创建前端支持实例
    frontend_support = FrontendSupport(project_path)
    
    try:
        # 检测前端框架
        print("正在检测前端项目...")
        project_info = frontend_support.detect_framework()
        
        print("\n=== 项目信息 ===")
        print(f"框架: {project_info.framework.value}")
        print(f"框架版本: {project_info.framework_version}")
        print(f"构建工具: {project_info.build_tool.value}")
        print(f"测试运行器: {project_info.test_runner.value if project_info.test_runner else '未检测到'}")
        print(f"E2E 测试: {project_info.e2e_runner.value if project_info.e2e_runner else '未检测到'}")
        print(f"包管理器: {project_info.package_manager.value}")
        
        # 解析 Vite 配置
        if project_info.has_vite_config:
            print("\n=== Vite 配置 ===")
            vite_config = frontend_support.parse_vite_config()
            if vite_config:
                print(f"服务器端口: {vite_config.server_port}")
                print(f"服务器主机: {vite_config.server_host}")
                print(f"构建输出目录: {vite_config.build_outdir}")
                print(f"Base URL: {vite_config.base}")
                print(f"插件: {', '.join(vite_config.plugins)}")
        
        # 查找 Vue 组件
        print("\n=== Vue 组件 ===")
        components = frontend_support.find_vue_components()
        print(f"找到 {len(components)} 个 Vue 组件")
        
        for component in components[:5]:  # 只显示前 5 个
            print(f"\n组件: {component.component_name}")
            print(f"  路径: {component.file_path.relative_to(project_path)}")
            print(f"  Script 语言: {component.script_lang or 'N/A'}")
            print(f"  Style 语言: {component.style_lang or 'N/A'}")
            print(f"  Composition API: {'是' if component.uses_composition_api else '否'}")
            print(f"  Options API: {'是' if component.uses_options_api else '否'}")
        
        if len(components) > 5:
            print(f"\n... 还有 {len(components) - 5} 个组件")
        
    except FileNotFoundError as e:
        print(f"\n错误: {e}")
        print("请确保项目目录包含 package.json 文件")
    except Exception as e:
        print(f"\n发生错误: {e}")


if __name__ == "__main__":
    main()
