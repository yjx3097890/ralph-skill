"""
Qwen Code 引擎适配器

Qwen Code 引擎的具体实现，通过 qwen CLI 工具进行代码生成和修改任务。

## 功能特点
- 代码生成：根据自然语言描述生成代码
- 代码补全：智能代码补全和建议
- 错误修复：分析错误信息并提供修复方案
- 多语言支持：支持主流编程语言

## CLI 工具
使用 https://github.com/QwenLM/qwen-code 提供的 CLI 工具

## 安装
```bash
# 快速安装（推荐）
# Linux / macOS
curl -fsSL https://qwen-code-assets.oss-cn-hangzhou.aliyuncs.com/installation/install-qwen.sh | bash

# Windows (以管理员身份运行 CMD)
curl -fsSL -o %TEMP%\\install-qwen.bat https://qwen-code-assets.oss-cn-hangzhou.aliyuncs.com/installation/install-qwen.bat && %TEMP%\\install-qwen.bat

# 或使用 npm 安装（需要 Node.js 20+）
npm install -g @qwen-code/qwen-code@latest

# 或使用 Homebrew（macOS/Linux）
brew install qwen-code
```

## 配置
支持两种认证方式：

1. Qwen OAuth（推荐，免费）：
   运行 `qwen` 后输入 `/auth`，选择 Qwen OAuth 在浏览器中登录

2. API-KEY 方式：
   编辑 ~/.qwen/settings.json 配置 API 密钥和模型

## 使用示例
```python
config = EngineConfig(
    engine_type=EngineType.QWEN_CODE,
    extra_params={"cli_path": "qwen"},  # CLI 工具路径
    model_name="qwen3-coder-plus"
)

adapter = QwenCodeAdapter(config)
adapter.initialize()

result = adapter.generate_code(
    prompt="实现一个快速排序算法",
    language="python"
)
```
"""

import json
import logging
import os
import re
import subprocess
from typing import List, Optional

from ralph.adapters.ai_engine import AIEngineAdapter, CodeResult, EngineConfig
from ralph.managers.cli_process_manager import CLIProcessManager
from ralph.models.enums import ErrorCategory

logger = logging.getLogger(__name__)


class QwenCodeAdapter(AIEngineAdapter):
    """Qwen Code 引擎适配器实现"""
    
    def __init__(self, config: EngineConfig):
        """
        初始化 Qwen Code 适配器
        
        Args:
            config: 引擎配置
        """
        super().__init__(config)
        self.process_manager = CLIProcessManager()
        # 从 extra_params 获取 cli_path，如果没有则使用默认值
        self.cli_path = getattr(config, 'extra_params', {}).get("cli_path", "qwen") if hasattr(config, 'extra_params') else "qwen"
        
        # 添加日志确认配置
        logger.info(f"QwenCodeAdapter 初始化: timeout={config.timeout}秒, model={config.model}")
    
    def initialize(self) -> bool:
        """
        初始化 Qwen Code 引擎
        
        检查 CLI 工具是否可用，验证 API 密钥配置
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 检查 CLI 工具是否安装
            import shutil
            if not shutil.which(self.cli_path):
                self.status.is_available = False
                self.status.last_error = f"qwen CLI 工具未找到，请先安装: https://github.com/QwenLM/qwen-code"
                return False
            
            # 检查认证配置（Qwen Code 支持 OAuth 和 API-KEY 两种方式）
            # OAuth 方式：运行 qwen 后输入 /auth
            # API-KEY 方式：配置 ~/.qwen/settings.json
            # 这里不强制检查，因为用户可能已经通过 OAuth 登录
            
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
                self.status.last_error = "qwen CLI 工具测试失败"
                return False
                
        except Exception as e:
            self.status.is_available = False
            self.status.last_error = str(e)
            return False
    
    def _build_env(self) -> dict:
        """
        构建环境变量
        
        Qwen Code 使用 ~/.qwen/settings.json 进行配置，
        不需要通过环境变量传递 API 密钥
        
        Returns:
            dict: 环境变量字典（通常为空）
        """
        return {}
    
    def _build_command(
        self,
        prompt: str,
        context: str = "",
        language: Optional[str] = None,
        **kwargs
    ) -> List[str]:
        """
        构建 CLI 命令
        
        Args:
            prompt: 代码生成提示
            context: 上下文信息
            language: 目标编程语言
            **kwargs: 其他参数
            
        Returns:
            List[str]: 命令列表
        """
        command = [self.cli_path]
        
        # 添加模型参数
        if self.config.model:
            command.extend(["--model", self.config.model])
        
        # 添加语言参数
        if language:
            command.extend(["--language", language])
        
        # 添加上下文
        if context:
            command.extend(["--context", context])
        
        # 添加提示
        command.append(prompt)
        
        return command
    
    def generate_code(
        self,
        prompt: str,
        context: str = "",
        language: Optional[str] = None,
        project_root: Optional[str] = None,
        **kwargs
    ) -> CodeResult:
        """
        使用 Qwen Code 生成代码
        
        Args:
            prompt: 代码生成提示
            context: 上下文信息
            language: 目标编程语言
            project_root: 项目根目录
            **kwargs: 其他参数
            
        Returns:
            CodeResult: 代码生成结果
        """
        try:
            # 构建完整的提示（包含上下文）
            full_prompt = prompt
            if context:
                full_prompt = f"{context}\n\n{prompt}"
            
            # 构建命令：使用 -p 参数进行非交互式调用
            command = [
                self.cli_path,
                "-p", full_prompt,
                "-y"  # YOLO 模式，自动接受所有操作
            ]
            
            # 如果指定了模型
            if self.config.model:
                command.extend(["-m", self.config.model])
            
            # 启动进程（在项目目录中运行）
            import subprocess
            import os
            
            cwd = project_root or os.getcwd()
            
            logger.info(f"在目录 {cwd} 中调用 Qwen Code...")
            logger.info(f"超时设置: {self.config.timeout} 秒")
            logger.info(f"提示: {prompt[:100]}...")
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                text=True
            )
            
            # 等待完成
            logger.info(f"等待 Qwen Code 完成（最多 {self.config.timeout} 秒）...")
            stdout, stderr = process.communicate(timeout=self.config.timeout)
            exit_code = process.returncode
            
            if exit_code == 0:
                # Qwen Code 会直接修改文件，我们需要检测哪些文件被修改了
                # 这里返回成功，文件变更由 Git 管理器检测
                return CodeResult(
                    success=True,
                    code="",  # Qwen Code 直接修改文件，不返回代码
                    explanation=f"Qwen Code 执行成功\n\n输出:\n{stdout}",
                    warnings=[],
                    changes=[]  # 由 Git 管理器检测变更
                )
            else:
                return CodeResult(
                    success=False,
                    code="",
                    explanation=f"Qwen Code 执行失败\n\n错误:\n{stderr}\n\n输出:\n{stdout}",
                    warnings=[stderr]
                )
                
        except subprocess.TimeoutExpired:
            return CodeResult(
                success=False,
                code="",
                explanation=f"Qwen Code 执行超时（{self.config.timeout}秒）",
                warnings=["执行超时"]
            )
        except Exception as e:
            return CodeResult(
                success=False,
                code="",
                explanation=f"Qwen Code 调用异常: {str(e)}",
                warnings=[str(e)]
            )
    
    def refactor_code(
        self,
        code: str,
        requirements: str,
        **kwargs
    ) -> CodeResult:
        """
        使用 Qwen Code 重构代码
        
        Args:
            code: 待重构的代码
            requirements: 重构需求描述
            **kwargs: 其他参数
            
        Returns:
            CodeResult: 重构结果
        """
        prompt = f"重构以下代码，要求：{requirements}\n\n```\n{code}\n```"
        return self.generate_code(prompt, **kwargs)
    
    def fix_errors(
        self,
        code: str,
        errors: List[str],
        error_category: Optional[ErrorCategory] = None,
        **kwargs
    ) -> CodeResult:
        """
        使用 Qwen Code 修复代码错误
        
        Args:
            code: 包含错误的代码
            errors: 错误信息列表
            error_category: 错误类别
            **kwargs: 其他参数
            
        Returns:
            CodeResult: 修复结果
        """
        errors_text = "\n".join(f"- {error}" for error in errors)
        prompt = f"修复以下代码中的错误：\n{errors_text}\n\n```\n{code}\n```"
        return self.generate_code(prompt, **kwargs)
    
    def _parse_output(self, output: str) -> tuple[str, str]:
        """
        解析 CLI 输出
        
        Args:
            output: CLI 输出文本
            
        Returns:
            tuple[str, str]: (代码, 解释)
        """
        # 尝试提取代码块
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', output, re.DOTALL)
        
        if code_blocks:
            code = code_blocks[0].strip()
            # 移除代码块后的文本作为解释
            explanation = re.sub(r'```(?:\w+)?\n.*?\n```', '', output, flags=re.DOTALL).strip()
        else:
            # 没有代码块，整个输出作为代码
            code = output.strip()
            explanation = "Qwen Code 生成的代码"
        
        return code, explanation
    
    def is_available(self) -> bool:
        """
        检查 Qwen Code 引擎是否可用
        
        Returns:
            bool: 引擎是否可用
        """
        return self.status.is_available

