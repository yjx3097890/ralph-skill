# ACP 集成测试说明

## 概述

本目录包含 ACP (Agent Coding Platform) Harness 的集成测试，验证以下功能：

- **会话生命周期管理**：创建、使用、销毁会话
- **Docker-in-Docker 操作**：镜像构建、容器运行、命令执行
- **Git 集成**：仓库克隆、分支管理、提交推送
- **Buildkit 多架构构建**：支持 amd64、arm64、arm/v7
- **故障恢复**：超时处理、错误恢复、会话重建
- **并发会话管理**：多会话支持、资源配额
- **资源管理和监控**：CPU、内存、磁盘监控
- **网络隔离和安全策略**：网络策略、访问控制
- **日志收集和审计**：日志导出、审计记录

## 测试文件

- `test_acp_integration.py` - ACP 集成测试主文件

## 运行测试

### 运行所有 ACP 集成测试

```bash
pytest tests/integration/test_acp_integration.py -v
```

### 运行特定测试类

```bash
# 测试会话生命周期
pytest tests/integration/test_acp_integration.py::TestACPSessionLifecycle -v

# 测试 Docker 操作
pytest tests/integration/test_acp_integration.py::TestACPDockerOperations -v

# 测试 Git 集成
pytest tests/integration/test_acp_integration.py::TestACPGitIntegration -v

# 测试多架构构建
pytest tests/integration/test_acp_integration.py::TestACPBuildkitMultiArch -v

# 测试故障恢复
pytest tests/integration/test_acp_integration.py::TestACPFailureRecovery -v

# 测试并发会话
pytest tests/integration/test_acp_integration.py::TestACPConcurrentSessions -v
```

### 运行特定测试用例

```bash
pytest tests/integration/test_acp_integration.py::TestACPSessionLifecycle::test_create_session_success -v
```

## 环境配置

### 环境变量

测试使用以下环境变量（可选）：

```bash
# ACP Harness 服务端点
export ACP_HARNESS_ENDPOINT="http://localhost:8080"

# ACP API 认证密钥
export ACP_API_KEY="your-api-key"
```

如果未设置，测试将使用默认值：
- `ACP_HARNESS_ENDPOINT`: `http://localhost:8080`
- `ACP_API_KEY`: `test-api-key`

### 模拟模式 vs 真实环境

**当前实现（模拟模式）**：
- 测试使用内存中的模拟 ACP Harness 实现
- 不需要真实的 ACP Harness 服务
- 适合快速开发和 CI/CD 环境

**真实环境模式**：
- 需要部署真实的 ACP Harness 服务
- 设置正确的 `ACP_HARNESS_ENDPOINT` 和 `ACP_API_KEY`
- 测试将调用真实的 API 端点

## 测试覆盖的需求

### 需求 13.1-13.4：会话生命周期
- ✅ 创建 ACP 会话
- ✅ 使用 ACP 会话
- ✅ 销毁 ACP 会话
- ✅ 列出所有会话
- ✅ 获取会话状态

### 需求 13.5-13.6：Docker-in-Docker
- ✅ 构建 Docker 镜像
- ✅ 运行容器
- ✅ 执行容器命令
- ✅ 收集容器日志
- ✅ 安全隔离验证

### 需求 13.7-13.8：QEMU 多架构
- ✅ 支持 amd64 架构
- ✅ 支持 arm64 架构
- ✅ 支持 arm/v7 架构
- ✅ 架构自动检测

### 需求 13.9-13.10：Git 集成
- ✅ 克隆仓库
- ✅ 切换分支
- ✅ 提交变更
- ✅ 推送变更
- ✅ SSH/HTTPS 认证

### 需求 13.11-13.12：Buildkit
- ✅ 多架构构建
- ✅ 缓存优化
- ✅ Secrets 管理
- ✅ 并行构建

### 需求 13.13-13.14：会话清理
- ✅ 自动销毁会话
- ✅ 超时回收
- ✅ 资源清理
- ✅ 日志导出

### 需求 13.15-13.17：故障恢复
- ✅ 错误检测
- ✅ 会话恢复
- ✅ 操作重试
- ✅ 故障日志

### 需求 13.18-13.19：资源管理
- ✅ CPU 限制
- ✅ 内存限制
- ✅ 磁盘配额
- ✅ 资源监控

### 需求 13.20-13.22：日志管理
- ✅ 日志收集
- ✅ 日志过滤
- ✅ 日志导出（JSON/文本）
- ✅ 日志归档

### 需求 13.25-13.30：网络和安全
- ✅ 网络隔离
- ✅ 访问控制
- ✅ 端口限制
- ✅ 特权模式限制

### 需求 13.31：审计日志
- ✅ 敏感操作记录
- ✅ 审计日志查询
- ✅ 审计日志持久化

### 需求 13.32-13.33：并发管理
- ✅ 多会话支持
- ✅ 并发限制
- ✅ 资源配额
- ✅ 会话排队

## 测试场景

### 场景 1：完整开发工作流
1. 创建 ACP 会话
2. 克隆代码仓库
3. 构建 Docker 镜像
4. 运行测试容器
5. 销毁会话

### 场景 2：多架构构建和推送
1. 创建支持多架构的会话
2. 克隆仓库
3. 使用 Buildkit 构建多架构镜像
4. 推送到镜像仓库
5. 清理资源

### 场景 3：并发会话管理
1. 创建多个并发会话
2. 在不同会话中执行操作
3. 验证资源隔离
4. 批量清理会话

### 场景 4：故障恢复
1. 创建会话
2. 模拟操作失败
3. 验证会话仍可用
4. 重试操作
5. 成功恢复

## 性能基准

预期性能指标：

- **会话创建时间**：< 5 秒
- **镜像构建时间**：取决于镜像大小和缓存
- **容器启动时间**：< 2 秒
- **Git 克隆时间**：取决于仓库大小
- **并发会话数**：最多 5 个（可配置）

## 故障排查

### 常见问题

**问题 1：会话创建失败**
- 检查 ACP Harness 服务是否运行
- 验证 API 密钥是否正确
- 检查网络连接

**问题 2：Docker 操作失败**
- 确认 Docker-in-Docker 环境已启用
- 检查镜像名称是否正确
- 验证网络策略配置

**问题 3：并发限制错误**
- 当前会话数已达上限
- 等待其他会话完成或销毁
- 增加 `max_concurrent_sessions` 配置

**问题 4：资源超限**
- 检查资源使用情况
- 调整资源限制配置
- 清理不需要的会话

## 贡献指南

添加新测试时，请遵循以下规范：

1. **测试命名**：使用描述性名称，如 `test_<功能>_<场景>`
2. **测试文档**：添加清晰的文档字符串
3. **需求追溯**：在注释中标注验证的需求编号
4. **资源清理**：确保测试后清理所有资源
5. **断言明确**：使用清晰的断言消息

## 参考资料

- [ACP Harness 文档](../../../docs/)
- [需求文档](../../../.kiro/specs/ralph-autonomous-engine/requirements.md)
- [设计文档](../../../.kiro/specs/ralph-autonomous-engine/design.md)
