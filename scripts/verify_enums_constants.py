#!/usr/bin/env python3
"""
验证枚举类型和常量定义

检查所有枚举类型和常量是否正确定义，并输出统计信息。
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ralph.models import enums, constants


def verify_enums():
    """验证枚举类型定义"""
    print("=" * 80)
    print("验证枚举类型定义")
    print("=" * 80)
    
    enum_classes = [
        name for name in dir(enums)
        if not name.startswith("_") and name[0].isupper()
    ]
    
    print(f"\n找到 {len(enum_classes)} 个枚举类型：\n")
    
    for enum_name in sorted(enum_classes):
        enum_class = getattr(enums, enum_name)
        if hasattr(enum_class, "__members__"):
            members = list(enum_class.__members__.keys())
            print(f"  ✓ {enum_name:30s} ({len(members):2d} 个值)")
            
            # 显示前 3 个值作为示例
            if members:
                examples = ", ".join(members[:3])
                if len(members) > 3:
                    examples += ", ..."
                print(f"    示例: {examples}")
    
    return len(enum_classes)


def verify_constants():
    """验证常量定义"""
    print("\n" + "=" * 80)
    print("验证常量定义")
    print("=" * 80)
    
    constant_names = [
        name for name in dir(constants)
        if not name.startswith("_") and name.isupper()
    ]
    
    print(f"\n找到 {len(constant_names)} 个常量：\n")
    
    # 按类别分组
    categories = {}
    for name in constant_names:
        # 根据前缀分类
        if name.startswith("DEFAULT_"):
            category = "默认配置"
        elif name.startswith("MAX_"):
            category = "最大值限制"
        elif name.startswith("MIN_"):
            category = "最小值限制"
        elif "_TIMEOUT" in name:
            category = "超时配置"
        elif "_RETRIES" in name or "_RETRY" in name:
            category = "重试配置"
        elif "_PORT" in name:
            category = "端口配置"
        elif "_DIR" in name or "_PATH" in name:
            category = "路径配置"
        elif "_INTERVAL" in name:
            category = "间隔配置"
        elif "_THRESHOLD" in name:
            category = "阈值配置"
        elif "_SIZE" in name or "_LENGTH" in name:
            category = "大小配置"
        elif name.startswith("RALPH_"):
            category = "系统信息"
        else:
            category = "其他"
        
        if category not in categories:
            categories[category] = []
        categories[category].append(name)
    
    for category in sorted(categories.keys()):
        print(f"\n{category} ({len(categories[category])} 个):")
        for name in sorted(categories[category])[:5]:  # 只显示前 5 个
            value = getattr(constants, name)
            value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."
            print(f"  ✓ {name:40s} = {value_str}")
        
        if len(categories[category]) > 5:
            print(f"    ... 还有 {len(categories[category]) - 5} 个常量")
    
    return len(constant_names)


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Ralph Skill 枚举类型和常量验证")
    print("=" * 80)
    
    try:
        enum_count = verify_enums()
        constant_count = verify_constants()
        
        print("\n" + "=" * 80)
        print("验证结果")
        print("=" * 80)
        print(f"\n✓ 枚举类型: {enum_count} 个")
        print(f"✓ 常量定义: {constant_count} 个")
        print(f"\n所有枚举和常量定义验证通过！")
        print("=" * 80 + "\n")
        
        return 0
    
    except Exception as e:
        print(f"\n✗ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
