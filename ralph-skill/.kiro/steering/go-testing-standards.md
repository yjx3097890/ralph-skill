---
inclusion: always
---

# Go 语言测试规范（精简版）

## 核心原则

- **测试是代码质量的保障**：所有测试必须通过，警告必须处理
- **不要逃避问题**：遇到依赖特殊环境的测试，寻求用户帮助配置
- **测试要有意义**：每个测试都应验证具体的行为或属性
- **测试要可维护**：测试代码应该清晰、简洁、易于理解

## 1. 单元测试标准

### 1.1 命名规范

```go
// ✅ 好的命名：清晰描述测试场景和期望结果
func TestCreateUser_ShouldReturnErrorWhenEmailIsEmpty(t *testing.T) { }
func TestParseJSON_ShouldParseValidJSONSuccessfully(t *testing.T) { }
func TestCalculateTotal_ShouldCalculateCorrectTotalForMultipleItems(t *testing.T) { }

// ❌ 不好的命名：模糊不清
func TestCreateUser1(t *testing.T) { }
func TestURL(t *testing.T) { }
func TestItWorks(t *testing.T) { }
```

### 1.2 测试结构 - AAA 模式

```go
func TestTaskList_Add_ShouldAddTaskToEmptyList(t *testing.T) {
    // Arrange（准备）：设置测试数据和环境
    taskList := NewTaskList()
    task := &Task{Description: "完成测试"}
    
    // Act（执行）：调用被测试的功能
    err := taskList.Add(task)
    
    // Assert（断言）：验证结果
    assert.NoError(t, err)
    assert.Equal(t, 1, taskList.Len())
}
```

### 1.3 表驱动测试

```go
func TestValidateEmail(t *testing.T) {
    tests := []struct {
        name    string
        email   string
        wantErr bool
    }{
        {
            name:    "有效邮箱",
            email:   "test@example.com",
            wantErr: false,
        },
        {
            name:    "无效邮箱_缺少@符号",
            email:   "testexample.com",
            wantErr: true,
        },
        {
            name:    "空邮箱",
            email:   "",
            wantErr: true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            err := ValidateEmail(tt.email)
            if tt.wantErr {
                assert.Error(t, err)
            } else {
                assert.NoError(t, err)
            }
        })
    }
}
```

### 1.4 覆盖范围

单元测试应该覆盖：
- **正常路径**：功能按预期工作的情况
- **边界条件**：空输入、最大值、最小值等
- **错误情况**：无效输入、异常状态等
- **特殊情况**：nil、空字符串、特殊字符等

```go
func TestTask(t *testing.T) {
    t.Run("should create task with valid description", func(t *testing.T) {
        task := NewTask("测试任务")
        assert.Equal(t, "测试任务", task.Description)
        assert.False(t, task.IsCompleted())
    })

    t.Run("should reject empty description", func(t *testing.T) {
        _, err := NewTask("")
        assert.Error(t, err)
        assert.Contains(t, err.Error(), "描述不能为空")
    })

    t.Run("should mark task as completed", func(t *testing.T) {
        task := NewTask("测试任务")
        task.Complete()
        assert.True(t, task.IsCompleted())
    })
}
```

## 2. 基准测试

```go
func BenchmarkCreateUser(b *testing.B) {
    req := CreateUserRequest{
        Name:  "张三",
        Email: "zhangsan@example.com",
    }
    
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        _, _ = CreateUser(req)
    }
}

func BenchmarkParseJSON(b *testing.B) {
    data := []byte(`{"name":"张三","email":"zhangsan@example.com"}`)
    
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        var user User
        _ = json.Unmarshal(data, &user)
    }
}
```

## 3. 示例测试

```go
func ExampleCreateUser() {
    req := CreateUserRequest{
        Name:  "张三",
        Email: "zhangsan@example.com",
    }
    
    user, err := CreateUser(req)
    if err != nil {
        panic(err)
    }
    
    fmt.Printf("用户创建成功: %s", user.Name)
    // Output: 用户创建成功: 张三
}

func ExampleUser_String() {
    user := &User{
        ID:   1,
        Name: "张三",
    }
    
    fmt.Println(user.String())
    // Output: User{ID: 1, Name: 张三}
}
```

## 4. Mock 和测试替身

### 4.1 接口设计

```go
// 定义接口
type UserRepository interface {
    Create(*User) error
    GetByID(int64) (*User, error)
    Update(*User) error
    Delete(int64) error
}

// 服务依赖接口
type UserService struct {
    repo UserRepository
}

func NewUserService(repo UserRepository) *UserService {
    return &UserService{repo: repo}
}

func (s *UserService) CreateUser(req CreateUserRequest) (*User, error) {
    user := &User{
        Name:  req.Name,
        Email: req.Email,
    }
    
    if err := s.repo.Create(user); err != nil {
        return nil, fmt.Errorf("创建用户失败: %w", err)
    }
    
    return user, nil
}
```

### 4.2 使用 testify/mock

```go
// 生成 mock（使用 mockery 工具）
//go:generate mockery --name=UserRepository

func TestUserService_CreateUser(t *testing.T) {
    // 创建 mock
    mockRepo := &mocks.UserRepository{}
    service := NewUserService(mockRepo)
    
    // 设置期望
    user := &User{Name: "张三", Email: "zhangsan@example.com"}
    mockRepo.On("Create", mock.AnythingOfType("*User")).Return(nil)
    
    // 执行测试
    req := CreateUserRequest{Name: "张三", Email: "zhangsan@example.com"}
    result, err := service.CreateUser(req)
    
    // 验证结果
    assert.NoError(t, err)
    assert.Equal(t, user.Name, result.Name)
    assert.Equal(t, user.Email, result.Email)
    
    // 验证 mock 调用
    mockRepo.AssertExpectations(t)
}
```

### 4.3 简单 Mock 实现

```go
// 简单的内存 mock 实现
type MockUserRepository struct {
    users map[int64]*User
    nextID int64
}

func NewMockUserRepository() *MockUserRepository {
    return &MockUserRepository{
        users: make(map[int64]*User),
        nextID: 1,
    }
}

func (m *MockUserRepository) Create(user *User) error {
    user.ID = m.nextID
    m.nextID++
    m.users[user.ID] = user
    return nil
}

func (m *MockUserRepository) GetByID(id int64) (*User, error) {
    user, exists := m.users[id]
    if !exists {
        return nil, errors.New("用户不存在")
    }
    return user, nil
}
```

## 5. 集成测试

```go
func TestUserService_Integration(t *testing.T) {
    // 设置测试数据库
    db := setupTestDB(t)
    defer cleanupTestDB(t, db)
    
    repo := NewUserRepository(db)
    service := NewUserService(repo)
    
    t.Run("should create and retrieve user", func(t *testing.T) {
        // 创建用户
        req := CreateUserRequest{
            Name:  "张三",
            Email: "zhangsan@example.com",
        }
        
        user, err := service.CreateUser(req)
        assert.NoError(t, err)
        assert.NotZero(t, user.ID)
        
        // 检索用户
        retrieved, err := service.GetUser(user.ID)
        assert.NoError(t, err)
        assert.Equal(t, user.Name, retrieved.Name)
        assert.Equal(t, user.Email, retrieved.Email)
    })
}

func setupTestDB(t *testing.T) *sql.DB {
    // 使用测试数据库连接
    dsn := os.Getenv("TEST_DATABASE_URL")
    if dsn == "" {
        dsn = "root:password@tcp(localhost:3306)/test_db?charset=utf8mb4&parseTime=True&loc=Local"
    }
    
    db, err := sql.Open("mysql", dsn)
    require.NoError(t, err)
    
    // 创建表结构
    _, err = db.Exec(`
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    `)
    require.NoError(t, err)
    
    return db
}

func cleanupTestDB(t *testing.T, db *sql.DB) {
    err := db.Close()
    require.NoError(t, err)
}
```

## 6. HTTP API 测试

```go
func TestUserHandler(t *testing.T) {
    // 设置测试服务器
    mockRepo := &mocks.UserRepository{}
    service := NewUserService(mockRepo)
    handler := NewUserHandler(service)
    
    router := gin.New()
    router.POST("/users", handler.CreateUser)
    
    t.Run("should create user via API", func(t *testing.T) {
        // 设置 mock 期望
        mockRepo.On("Create", mock.AnythingOfType("*User")).Return(nil)
        
        // 准备请求
        reqBody := `{"name":"张三","email":"zhangsan@example.com"}`
        req := httptest.NewRequest("POST", "/users", strings.NewReader(reqBody))
        req.Header.Set("Content-Type", "application/json")
        
        // 执行请求
        w := httptest.NewRecorder()
        router.ServeHTTP(w, req)
        
        // 验证响应
        assert.Equal(t, http.StatusOK, w.Code)
        
        var response map[string]interface{}
        err := json.Unmarshal(w.Body.Bytes(), &response)
        assert.NoError(t, err)
        assert.Equal(t, "张三", response["name"])
        
        mockRepo.AssertExpectations(t)
    })
    
    t.Run("should return 400 for invalid request", func(t *testing.T) {
        reqBody := `{"name":"","email":"zhangsan@example.com"}`
        req := httptest.NewRequest("POST", "/users", strings.NewReader(reqBody))
        req.Header.Set("Content-Type", "application/json")
        
        w := httptest.NewRecorder()
        router.ServeHTTP(w, req)
        
        assert.Equal(t, http.StatusBadRequest, w.Code)
    })
}
```

## 7. 依赖特殊环境的测试

### 7.1 处理流程

```go
// ✅ 正确做法：检查环境并提供清晰错误
func TestRedisConnection(t *testing.T) {
    if os.Getenv("SKIP_REDIS_TESTS") != "" {
        t.Skip("跳过 Redis 测试（设置了 SKIP_REDIS_TESTS）")
    }
    
    redisURL := os.Getenv("REDIS_URL")
    if redisURL == "" {
        t.Fatal(`需要 Redis 环境。请：
1. 安装 Redis: brew install redis (macOS) 或 apt install redis (Linux)
2. 启动 Redis: redis-server
3. 设置环境变量: export REDIS_URL=redis://localhost:6379
或者设置 SKIP_REDIS_TESTS=1 跳过这些测试`)
    }
    
    // 继续测试...
    client := redis.NewClient(&redis.Options{
        Addr: redisURL,
    })
    defer client.Close()
    
    err := client.Ping(context.Background()).Err()
    assert.NoError(t, err)
}

// ❌ 错误做法：自动跳过
func TestRedisConnection_Bad(t *testing.T) {
    t.Skip("需要 Redis") // 不要这样做
}
```

### 7.2 环境配置文档

```go
// tests/README.md 示例内容：
/*
# 测试环境配置

## Redis 测试

需要运行 Redis 服务器：

```bash
# macOS
brew install redis
redis-server

# Linux
sudo apt install redis-server
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:latest
```

设置环境变量：
```bash
export REDIS_URL=redis://localhost:6379
```

## MySQL 测试

```bash
# Docker
docker run -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password -e MYSQL_DATABASE=test_db mysql:8.0

# 设置环境变量
export TEST_DATABASE_URL="root:password@tcp(localhost:3306)/test_db?charset=utf8mb4&parseTime=True&loc=Local"
```
*/
```

## 8. 测试执行和工具

### 8.1 基本命令

```bash
# 运行所有测试
go test ./...

# 运行特定包的测试
go test ./pkg/user

# 运行特定测试
go test -run TestCreateUser ./pkg/user

# 显示详细输出
go test -v ./...

# 运行基准测试
go test -bench=. ./...

# 测试覆盖率
go test -cover ./...

# 生成覆盖率报告
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out

# 竞态检测
go test -race ./...

# 并行测试
go test -parallel 4 ./...
```

### 8.2 测试标签

```go
//go:build integration
// +build integration

package user_test

// 集成测试文件

//go:build !integration
// +build !integration

package user_test

// 单元测试文件
```

```bash
# 只运行单元测试
go test -tags="!integration" ./...

# 只运行集成测试
go test -tags=integration ./...
```

### 8.3 推荐工具

```go
// 测试断言库
import (
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
    "github.com/stretchr/testify/mock"
)

// Mock 生成工具
//go:generate mockery --name=UserRepository

// 测试数据生成
import "github.com/brianvoe/gofakeit/v6"

func TestWithFakeData(t *testing.T) {
    user := &User{
        Name:  gofakeit.Name(),
        Email: gofakeit.Email(),
    }
    // 测试逻辑...
}
```

## 9. 性能和覆盖率

### 9.1 性能要求

- **单元测试**：每个测试 < 10ms
- **集成测试**：每个测试 < 1s
- **端到端测试**：每个测试 < 30s

### 9.2 覆盖率目标

- **核心功能**：100% 覆盖
- **整体代码**：> 80% 覆盖
- **关键路径**：100% 覆盖

```bash
# 检查覆盖率
go test -cover ./...

# 详细覆盖率报告
go test -coverprofile=coverage.out ./...
go tool cover -func=coverage.out

# HTML 覆盖率报告
go tool cover -html=coverage.out -o coverage.html
```

## 10. 最佳实践检查清单

### 提交前检查清单

- [ ] 所有测试通过：`go test ./...`
- [ ] 没有竞态条件：`go test -race ./...`
- [ ] 代码格式化：`go fmt ./...`
- [ ] 静态检查：`go vet ./...`
- [ ] Linter 检查：`golangci-lint run`
- [ ] 测试覆盖率达标
- [ ] 新功能有对应的测试
- [ ] 测试名称清晰描述测试内容
- [ ] 需要特殊环境的测试有清晰文档

### DO（应该做）

- ✅ 使用表驱动测试
- ✅ 为每个公共函数编写测试
- ✅ 测试边界条件和错误情况
- ✅ 使用有意义的测试名称
- ✅ 使用接口进行依赖注入
- ✅ 编写基准测试验证性能
- ✅ 使用 testify 进行断言

### DON'T（不应该做）

- ❌ 不要忽视测试失败
- ❌ 不要自动跳过需要环境的测试
- ❌ 不要编写依赖执行顺序的测试
- ❌ 不要在测试中使用随机数据（除非必要）
- ❌ 不要编写过于复杂的测试
- ❌ 不要为了覆盖率而写无意义的测试

**记住：好的测试让你有信心重构，是最好的文档，能尽早发现 bug。**