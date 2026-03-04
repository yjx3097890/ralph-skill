#!/usr/bin/env python3
"""
Ralph Skill CLI 包装器
供 Kiro 调用的简化接口
"""

import json
import sys
from pathlib import Path

# 添加 src 到路径
skill_dir = Path(__file__).parent
sys.path.insert(0, str(skill_dir / "src"))

from ralph import autonomous_develop


def main():
    """
    CLI 入口
    
    用法：
        python ralph_cli.py '{"task_description": "创建 Todo 应用", "tech_stack": {...}}'
    """
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "message": "缺少参数：需要 JSON 格式的任务描述"
        }))
        return 1
    
    try:
        # 解析参数
        params = json.loads(sys.argv[1])
        
        # 调用主函数
        result = autonomous_develop(
            task_description=params.get("task_description", ""),
            tech_stack=params.get("tech_stack"),
            requirements=params.get("requirements"),
            config_file=params.get("config_file"),
            project_root=params.get("project_root", ".")
        )
        
        # 输出结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["success"] else 1
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "message": f"执行失败: {str(e)}"
        }))
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
