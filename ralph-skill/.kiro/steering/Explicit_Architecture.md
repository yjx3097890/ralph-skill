---
inclusion: always
---
这份文档是**智慧制卷系统（Smart Exam Paper System）**开发的最高指导原则。

这是一份基于 **Explicit Architecture (显式架构)**，并根据 **外部 PDF 服务集成** 和 **JSON 数据存储策略** 深度定制的架构规范文档。

---

# 智慧制卷系统 - Explicit Architecture 架构规范 v2.0

## 1. 核心设计理念
本系统采用 **Explicit Architecture (显式架构)**，融合了 Clean Architecture 和 Hexagonal Architecture 的思想。
**核心原则：**
1.  **依赖倒置**：内层（Domain）绝不依赖外层（Infra/UI）。外层通过依赖注入（DI）实现内层接口。
2.  **显式边界**：业务实体（Entity）与数据库模型（PO）必须严格分离，禁止混用。
3.  **适配器模式**：所有外部服务（PDF生成、LLM、LibreOffice）必须通过 Adapter 接入，核心业务不感知具体实现。

---

## 2. 目录结构规范
采用 Go 标准项目布局（Standard Go Project Layout）与 DDD 分层结合：

```text
/
├── cmd/
│   └── server/             # main.go, 依赖注入初始化 (Wire/Manual)
├── internal/               # 私有应用代码
│   ├── answer_sheet/       # [Context] 答题卡限界上下文
│   │   ├── domain/         # 1. 核心层：Entity, ValueObject, Repo Interface
│   │   ├── app/            # 2. 应用层：UseCase, Command, Query
│   │   ├── infra/          # 3. 基础设施层：Persistence, RemoteAdapter
│   │   └── ui/             # 4. 接口层：HTTP Handlers, DTOs
│   ├── question_import/    # [Context] 题目导入限界上下文
│   └── pkg/                # 共享工具 (Logger, Error types)
├── configs/                # 配置文件 (.yaml, .env)
└── api/                    # OpenAPI/Swagger 定义
```

---

## 3. 分层详细规范

### 3.1 Domain Layer (业务领域层)
**定位**：系统的核心，包含业务逻辑和状态。
**规则**：
*   **纯净性**：只依赖 Go 标准库。**严禁** 引入 `gorm`, `gin`, `sql` 等第三方库。
*   **结构体**：定义纯粹的 Entity。
    *   Forbidden: `gorm.Model`, `json tags` (除非确实用于业务序列化，否则避免), `sql.NullString`.
*   **接口定义**：定义 `Repository` 和 `Service` 的接口，但不实现它们。

**代码示例** (`internal/answer_sheet/domain/entity.go`):
```go
package domain

// AnswerSheet 是纯净的业务实体
type AnswerSheet struct {
    ID          string
    Layout      LayoutConfig    // Value Object
    Coordinates []Coordinate    // Value Object
    PdfResult   PdfResult       // Value Object (Url, JobId)
}

// 接口定义在 Domain 层
type AnswerSheetRepository interface {
    Save(ctx context.Context, sheet *AnswerSheet) error
    FindByID(ctx context.Context, id string) (*AnswerSheet, error)
}
```

### 3.2 Application Layer (应用服务层)
**定位**：编排业务流程，作为 Domain 的入口。
**规则**：
*   **Use Cases**：每个业务动作对应一个 UseCase (e.g., `GeneratePdfUseCase`, `ImportQuestionUseCase`)。
*   **输入输出**：接受基本类型或 DTO，调用 Domain 方法，通过 Repository 接口持久化。
*   **不含 HTTP**：不要在这一层处理 HTTP Request/Response。

**代码示例** (`internal/answer_sheet/app/command/generate_pdf.go`):
```go
type GeneratePdfHandler struct {
    repo       domain.AnswerSheetRepository
    pdfService domain.PdfGeneratorPort // 依赖接口
}

func (h *GeneratePdfHandler) Handle(ctx context.Context, cmd GeneratePdfCommand) error {
    sheet, _ := h.repo.FindByID(ctx, cmd.SheetID)
    
    // 调用外部服务接口（具体是本地还是远程，这里不关心）
    jobId, _ := h.pdfService.SubmitConversion(sheet.PreviewUrl)
    
    sheet.SetGeneratingStatus(jobId)
    return h.repo.Save(ctx, sheet)
}
```

### 3.3 Infrastructure Layer (基础设施层)
**定位**：实现 Domain 定义的接口，处理数据库、外部 API。

#### A. Persistence (持久化/数据库)
**规则**：
*   **独立模型**：定义 `Model` (PO)，包含 SQL 细节。
*   **JSON 规范**：对于复杂结构（布局配置、坐标、选项），必须使用 MySQL `JSON` 类型。
*   **Mapper**：必须显式编写 `ToDomain()` 和 `FromDomain()` 方法。

**代码示例** (`internal/answer_sheet/infra/persistence/model.go`):
```go
type AnswerSheetModel struct {
    ID       string `gorm:"primaryKey"`
    Config   []byte `gorm:"type:json"` // 映射 domain.LayoutConfig
    Coords   []byte `gorm:"type:json"` // 映射 []domain.Coordinate
    PdfUrl   string
    gorm.Model
}

func (m *AnswerSheetModel) ToDomain() *domain.AnswerSheet {
    // 使用 json.Unmarshal 将 []byte 转为 Domain 对象
}
```

#### B. Adapter (外部适配器)
**规则**：
*   **隔离变更**：当外部 API 变更时，只修改 Adapter，不修改 Domain。
*   **实现**：本项目的 PDF 生成服务在此实现。

**代码示例** (`internal/answer_sheet/infra/adapter/remote_pdf.go`):
```go
type RemotePdfAdapter struct {
    client *http.Client
    baseUrl string
}

// 实现 domain.PdfGeneratorPort 接口
func (r *RemotePdfAdapter) SubmitConversion(url string) (string, error) {
    // 调用 POST /api/pdf/v1/convert/async
    // 返回 JobID
}
```

### 3.4 Interface/UI Layer (用户接口层)
**定位**：处理 HTTP 请求，解析参数，格式化响应。
**规则**：
*   **Web 框架**：使用 Gin 或 Echo。
*   **DTO**：定义 `Request` 和 `Response` 结构体，负责 JSON Tag。
*   **逻辑**：调用 App 层的 UseCase，**严禁** 直接调用 Repo 或写业务逻辑。

---

## 4. 关键数据流与交互

### 4.1 坐标数据流 (The Coordinate Flow)
这是系统最特殊的部分，逻辑如下：
1.  **Frontend (Vue3)**: 用户点击生成 -> JS 遍历 DOM 计算坐标 (mm) -> 构造 JSON。
2.  **API**: 接收 JSON Payload。
3.  **App**: 验证数据完整性。
4.  **Domain**: 将坐标视为 `Value Object` 存入实体。
5.  **Infra**: 序列化为 JSON 字符串 (`[]byte`) -> 存入 MySQL `json` 列。

### 4.2 PDF 生成流 (The Async Flow)
1.  **Trigger**: 业务层保存 HTML Url。
2.  **Adapter**: 调用 `RemotePdfAdapter.SubmitTask`。
3.  **State**: 数据库状态变为 `Generating`，记录 `job_id`。
4.  **Worker**: 轮询/回调 -> 调用 `RemotePdfAdapter.QueryStatus` -> 更新数据库 `pdf_url`。

---

## 5. 开发检查清单 (Checklist)

在提交代码前，请自查：

- [ ] **Domain 纯净性**：Domain 层是否有引入 `gorm` 或 `gin`？(如果有，请删除)
- [ ] **显式转换**：是否编写了 `Model <-> Entity` 的转换代码？(禁止直接透传 Model 到 Controller)
- [ ] **JSON 处理**：复杂的嵌套结构是否使用了 MySQL JSON 类型而不是建立了无意义的关联表？
- [ ] **接口依赖**：Service 层是否依赖的是 Repository 的接口（Interface）而不是结构体（Struct）？
- [ ] **配置分离**：外部 PDF 服务的 URL 和 Key 是否放在了 `configs/` 或环境变量中？

---

## 6. 技术栈锁定

*   **Language**: Go 1.21+
*   **Web Framework**: Gin
*   **ORM**: Gorm v2
*   **Database**: MySQL 8.0 (必须支持 JSON 类型)
*   **Frontend**: Vue 3 + Tailwind CSS
*   **External Svc**: Custom PDF Service (API v1)