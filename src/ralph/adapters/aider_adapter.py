"""
Aider 引擎适配器

Aider 引擎的具体实现，通过 aider CLI 工具进行代码重构和优化任务。

## 功能特点
- 代码重构：智能重构和优化代码结构
- 代码审查：分析代码质量并提供改进建议
- 性能优化：识别性能瓶颈并提供优化方案
- 最佳实践：应用编程最佳实践

## CLI 工具
使用 aider CLI 工具：https://github.com/paul-gauthier/aider

## 安装
```bash
# 使用 pip 安装
pip install aider-chat

# 或使用 pipx 安装（推荐）
pipx install aider-chat
```

## 配置
需要设置 API 密钥（根据使用的模型）：
```bash
export OPENAI_API_KEY="your-openai-key"
# 或
export ANTHROPIC_API_KEY="your-anthropic-key"
```

## 使用示例
```python
config = EngineConfig(
    engine_type=EngineType.AIDER,
    cli_path="aider",
    model_name="gpt-4"
)

adapter = AiderAdapter(config)
adapter.initialize()

result = adapter.refactor_code(
    code="legacy_code.py",
    requirements="应用 SOLID 原则重构代码"
)
```
"""

import os
import re
from typing import List, Optional

from ralph.adapters.ai_engine import AIEngineAdapter, CodeResult, EngineConfig
from ralph.managers.cli_process_manager import CLIProcessManager
from ralph.models.enums import ErrorCategory


class AiderAdapter(AIEngineAdapter):
    """Aider 引擎适配器实现"""
    
    def __init__(self, config: EngineConfig):
        """
        初始化 Aider 适配器
        
        Args:
            config: 引擎配置
        """
        super().__init__(config)
        self.process_manager = CLIProcessManager()
        self.cli_path = config.extra_params.get("cli_path", "aider")
        self.aider_process = None  # 保持 aider 进程运行以支持交互式会话
    
    def initialize(self) -> bool:
        """
        初始化 Aider 引擎
        
        检查 CLI 工具是否可用，验证 API 密钥配置
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 检查 CLI 工具是否安装
            import shutil
            if not shutil.which(self.cli_path):
                self.status.is_available = False
                self.status.last_error = f"aider CLI 工具未找到，请先安装: pip install aider-chat"
                return False
            
            # 检查 API 密钥（Aider 支持多种模型）
            has_api_key = (
                self.config.api_key or
                os.getenv("OPENAI_API_KEY") or
                os.getenv("ANTHROPIC_API_KEY") or
                os.getenv("GEMINI_API_KEY")
            )
            
            if not has_api_key:
                self.status.is_available = False
                self.status.last_error = "未设置 API 密钥（OPENAI_API_KEY、ANTHROPIC_API_KEY 或 GEMINI_API_KEY）"
                return False
            
            # 测试 CLI 工具
            process = self.process_manager.start_process(
                command=[self.cli_path, "--version"],
                env=self._build_env()
            )
            
            exit_code = self.process_manager.wait_for_completion(process, timeout=10)
            
            if exit_code == 0:
                self.status.is_available = True
                return True
            else:
                self.status.is_available = False
                self.status.last_error = "aider CLI 工具测试失败"
                return False
                
        except Exception as e:
            self.status.is_available = False
            self.status.last_error = str(e)
            return False
    
    def _build_env(self) -> dict:
        """
        构建环境变量
        
        Returns:
            dict: 环境变量字典
        """
        env = {}
        
        # 设置 API 密钥
        if self.config.api_key and self.config.model_name:
            # 根据模型类型设置相应的环境变量
            model_lower = self.config.model_name.lower()
            if "gpt" in model_lower:
                env["OPENAI_API_KEY"] = self.config.api_key
            elif "claude" in model_lower:
                env["ANTHROPIC_API_KEY"] = self.config.api_key
            elif "gemini" in model_lower:
                env["GEMINI_API_KEY"] = self.config.api_key
        
        return env
    
    def _build_command(
        self,
        files: List[str],
        message: str,
        **kwargs
    ) -> List[str]:
        """
        构建 CLI 命令
        
        Args:
            files: 要处理的文件列表
            message: 指令消息
            **kwargs: 其他参数
            
        Returns:
            List[str]: 命令列表
        """
        command = [self.cli_path]
        
        # 添加模型参数
        if self.config.model_name:
            command.extend(["--model", self.config.model_name])
        
        # 添加文件
        if files:
            command.extend(files)
        
        # 添加消息
        command.extend(["--message", message])
        
        # 添加其他选项
        command.append("--yes")  # 自动确认
        command.append("--no-pretty")  # 禁用彩色输出
        
        return command
    
    def generate_code(
        self,
        prompt: str,
        context: str = "",
        language: Optional[str] = None,
        **kwargs
    ) -> CodeResult:
        """
        使用 Aider 生成代码
        
        Args:
            prompt: 代码生成提示
            context: 上下文信息（文件路径）
            language: 目标编程语言
            **kwargs: 其他参数
            
        Returns:
            CodeResult: 代码生成结果
        """
        try:
            # 解析上下文中的文件路径
            files = context.split(",") if context else []
            
            # 构建命令
            command = self._build_command(files, prompt, **kwargs)
            
            # 启动进程
            process = self.process_manager.start_process(
                command=command,
                env=self._build_env()
            )
            
            # 读取输出
            output = self.process_manager.read_output(
                process,
                timeout=self.config.timeout
            )
            
            # 等待进程完成
            exit_code = self.process_manager.wait_for_completion(process)
            
            if exit_code == 0:
                return CodeResult(
                    success=True,
                    code=output,
                    explanation="Aider 成功生成代码",
                    warnings=[]
                )
            else:
                # 读取错误输出
                error_output = self.process_manager.read_output(
                    process,
                    stream="stderr"
                )
                
                return CodeResult(
                    success=False,
                    code="",
                    explanation=f"Aider 执行失败: {error_output}",
                    warnings=[error_output]
                )
                
        except Exception as e:
            return CodeResult(
                success=False,
                code="",
                explanation=f"Aider 调用异常: {str(e)}",
                warnings=[str(e)]
            )
    
    def refactor_code(
        self,
        code: str,
        requirements: str,
        **kwargs
    ) -> CodeResult:
        """
        使用 Aider 重构代码（Aider 的核心功能）
        
        Args:
            code: 待重构的代码（文件路径）
            requirements: 重构需求描述
            **kwargs: 其他参数
            
        Returns:
            CodeResult: 重构结果
        """
        # Aider 擅长代码重构和优化
        return self.generate_code(
            prompt=f"重构代码：{requirements}",
            context=code,
            **kwargs
        )
    
    def fix_errors(
        self,
        code: str,
        errors: List[str],
        error_category: Optional[ErrorCategory] = None,
        **kwargs
    ) -> CodeResult:
        """
        使用 Aider 修复代码错误
        
        Args:
            code: 包含错误的代码（文件路径）
            errors: 错误信息列表
            error_category: 错误类别
            **kwargs: 其他参数
            
        Returns:
            CodeResult: 修复结果
        """
        errors_text = "\n".join(f"- {error}" for error in errors)
        prompt = f"修复以下错误：\n{errors_text}"
        
        return self.generate_code(
            prompt=prompt,
            context=code,
            **kwargs
        )
    
    def is_available(self) -> bool:
        """
        检查 Aider 引擎是否可用
        
        Returns:
            bool: 引擎是否可用
        """
        return self.status.is_available
    
    def __del__(self):
        """析构函数：清理 Aider 进程"""
        if self.aider_process:
            self.process_manager.terminate_process(self.aider_process)
