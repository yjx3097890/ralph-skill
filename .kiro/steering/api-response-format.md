---
inclusion: always
---

# API 响应格式规范

## 核心原则

所有 API 端点必须使用统一的 JSON 响应格式，确保客户端能够以一致的方式处理响应。

## 统一响应结构

### 基本格式

所有 API 响应都必须遵循以下 JSON 结构：

```json
{
  "code": <HTTP状态码>,
  "data": <响应数据或null>,
  "message": "<状态消息>"
}
```

### 字段说明

- **code**: `number` - HTTP 状态码（200, 400, 500 等）
- **data**: `object | null` - 响应数据，成功时包含实际数据，错误时为 `null`
- **message**: `string` - 状态消息，成功时为"成功"，错误时为具体错误描述

## 成功响应格式

### 200 成功响应

```json
{
  "code": 200,
  "data": {
    "pdf_url": "https://test-zyy-oss.com/DcwjFY00/temp/uuid.pdf",
    "file_size": 1024,
    "page_count": 1
  },
  "message": "成功"
}
```

### 健康检查响应

```json
{
  "code": 200,
  "data": {
    "status": "ok",
    "service": "web-to-pdf-service"
  },
  "message": "成功"
}
```

### 任务创建响应

```json
{
  "code": 200,
  "data": {
    "task_id": "uuid-string",
    "status": "Pending"
  },
  "message": "成功"
}
```

## 错误响应格式

### 400 客户端错误

```json
{
  "code": 400,
  "data": null,
  "message": "URL 不能为空"
}
```

### 404 资源未找到

```json
{
  "code": 404,
  "data": null,
  "message": "任务未找到"
}
```

### 415 不支持的媒体类型

```json
{
  "code": 415,
  "data": null,
  "message": "不支持的媒体类型"
}
```

### 500 服务器内部错误

```json
{
  "code": 500,
  "data": null,
  "message": "转换错误: 页面加载失败"
}
```

### 503 服务不可用

```json
{
  "code": 503,
  "data": null,
  "message": "服务繁忙，请稍后重试"
}
```


## 最佳实践

### DO（应该做）

- ✅ 始终使用统一的响应格式
- ✅ 提供清晰的错误消息
- ✅ 使用适当的 HTTP 状态码
- ✅ 在测试中验证响应格式
- ✅ 保持消息的国际化友好性

### DON'T（不应该做）

- ❌ 不要在不同端点使用不同的响应格式
- ❌ 不要在成功响应中返回 null data
- ❌ 不要使用模糊的错误消息
- ❌ 不要忽略 HTTP 状态码的语义
- ❌ 不要在响应中包含敏感信息


## 总结

统一的 API 响应格式提供了：

- **一致性**：所有端点使用相同的响应结构
- **可预测性**：客户端可以用统一的方式处理响应
- **可维护性**：减少客户端和服务端的复杂性
- **可扩展性**：便于添加新的元数据字段
- **调试友好**：清晰的错误消息和状态码

遵循这个规范，确保 API 的专业性和易用性。