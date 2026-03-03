---
inclusion: always
---

# CSS & Sass 代码规范（精简版）

基于 Airbnb CSS / Sass Style Guide

## 核心原则

- **一致性**：保持一致的编码风格
- **可读性**：代码易于阅读和理解
- **模块化**：使用模块化方法组织样式
- **性能**：考虑样式性能影响

## 1. CSS 基础格式

```css
/* ✅ 好的做法 */
.avatar {
  border-radius: 50%;
  border: 2px solid white;
}

.one,
.selector,
.per-line {
  /* 多个选择器独占一行 */
}

/* ❌ 不好的做法 */
.avatar{
    border-radius:50%;
    border:2px solid white; }

#lol-no {  /* 不要使用 ID 选择器 */
  /* ... */
}
```

### 格式规则
- 使用 2 个空格缩进
- 类名使用破折号分隔
- 不要使用 ID 选择器
- 大括号前加空格
- 冒号后加空格
- 规则声明间用空行分隔

## 2. BEM 命名约定

```html
<article class="listing-card listing-card--featured">
  <h1 class="listing-card__title">标题</h1>
  <div class="listing-card__content">
    <p>内容</p>
  </div>
</article>
```

```css
.listing-card { }           /* 块（Block） */
.listing-card--featured { } /* 修饰符（Modifier） */
.listing-card__title { }    /* 元素（Element） */
.listing-card__content { }  /* 元素（Element） */
```

## 3. Sass 语法

### 3.1 属性声明排序

```scss
.btn {
  // 1. 属性声明
  background: green;
  font-weight: bold;
  
  // 2. @include 声明
  @include transition(background 0.5s ease);
  
  // 3. 嵌套选择器
  .icon {
    margin-right: 10px;
  }
}
```

### 3.2 变量命名

```scss
// ✅ 好的做法 - 破折号分隔
$primary-color: #3bbfce;
$secondary-color: #ff8700;
$base-font-size: 16px;

// ❌ 不好的做法
$primaryColor: #3bbfce;
$SECONDARY_COLOR: #ff8700;
```

### 3.3 嵌套限制

```scss
// ✅ 好的做法 - 不超过 3 层嵌套
.page-container {
  .content {
    .profile {
      // 最多 3 层
    }
  }
}

// ❌ 不好的做法 - 过度嵌套
.page-container {
  .content {
    .profile {
      .avatar {
        .image {  // 太深了！
          // ...
        }
      }
    }
  }
}
```

## 4. 常用 Mixins

```scss
// 清除浮动
@mixin clearfix {
  &::after {
    content: '';
    display: table;
    clear: both;
  }
}

// 文本截断
@mixin text-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

// 居中对齐
@mixin flex-center {
  display: flex;
  align-items: center;
  justify-content: center;
}

// 按钮样式
@mixin button-variant($background, $border, $color: #fff) {
  color: $color;
  background-color: $background;
  border-color: $border;

  &:hover {
    background-color: darken($background, 7.5%);
    border-color: darken($border, 10%);
  }
}

// 使用示例
.card {
  @include clearfix;
  
  &__title {
    @include text-truncate;
  }
  
  &__button {
    @include button-variant(#007bff, #007bff);
  }
}
```

## 5. 属性顺序

```scss
.declaration-order {
  // 1. 定位
  position: absolute;
  top: 0;
  left: 0;
  z-index: 100;

  // 2. 盒模型
  display: block;
  width: 100px;
  height: 100px;
  margin: 10px;
  padding: 10px;
  border: 1px solid #e5e5e5;

  // 3. 排版
  font: normal 13px "Helvetica Neue", sans-serif;
  line-height: 1.5;
  color: #333;
  text-align: center;

  // 4. 视觉外观
  background-color: #f5f5f5;
  opacity: 1;
  cursor: pointer;
}
```

## 6. 变量组织

```scss
// 颜色变量
$color-primary: #007bff;
$color-secondary: #6c757d;
$color-success: #28a745;
$color-danger: #dc3545;

// 字体变量
$font-family-sans-serif: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
$font-size-base: 1rem;
$font-weight-normal: 400;
$font-weight-bold: 700;

// 间距变量
$spacer: 1rem;
$spacers: (
  0: 0,
  1: ($spacer * 0.25),
  2: ($spacer * 0.5),
  3: $spacer,
  4: ($spacer * 1.5),
  5: ($spacer * 3)
);

// 断点变量
$grid-breakpoints: (
  xs: 0,
  sm: 576px,
  md: 768px,
  lg: 992px,
  xl: 1200px
);
```

## 7. 文件组织

```
scss/
├── abstracts/
│   ├── _variables.scss    # 变量
│   ├── _mixins.scss       # Mixins
│   └── _functions.scss    # 函数
├── base/
│   ├── _reset.scss        # 重置样式
│   └── _typography.scss   # 排版
├── components/
│   ├── _buttons.scss      # 按钮
│   ├── _cards.scss        # 卡片
│   └── _forms.scss        # 表单
├── layout/
│   ├── _header.scss       # 头部
│   ├── _footer.scss       # 底部
│   └── _sidebar.scss      # 侧边栏
└── main.scss              # 主文件
```

### 主文件示例

```scss
// main.scss
// 1. 抽象层
@import 'abstracts/variables';
@import 'abstracts/mixins';

// 2. 基础样式
@import 'base/reset';
@import 'base/typography';

// 3. 布局
@import 'layout/header';
@import 'layout/footer';

// 4. 组件
@import 'components/buttons';
@import 'components/cards';
```

## 8. 媒体查询

```scss
// ✅ 好的做法 - 就近放置
.element {
  padding: 15px;
}

.element-avatar {
  width: 40px;
  height: 40px;
}

@media (max-width: 768px) {
  .element {
    padding: 10px;
  }
  
  .element-avatar {
    width: 30px;
    height: 30px;
  }
}

// 媒体查询 mixin
@mixin media-breakpoint-up($name) {
  @if $name == sm {
    @media (min-width: 576px) { @content; }
  }
  @if $name == md {
    @media (min-width: 768px) { @content; }
  }
  @if $name == lg {
    @media (min-width: 992px) { @content; }
  }
}

// 使用
.card {
  padding: 1rem;
  
  @include media-breakpoint-up(md) {
    padding: 2rem;
  }
}
```

## 9. 性能优化

```scss
// ✅ 好的做法 - 简单选择器
.nav-link {
  color: #333;
}

// 使用 placeholder 减少重复
%button-base {
  display: inline-block;
  padding: 0.375rem 0.75rem;
  border: 1px solid transparent;
  border-radius: 0.25rem;
}

.btn {
  @extend %button-base;
}

.btn-primary {
  @extend %button-base;
  @include button-variant(#007bff, #007bff);
}

// ❌ 不好的做法 - 过度限定
ul.nav li.nav-item a.nav-link {
  color: #333;
}
```

## 10. 注释规范

```scss
/**
 * 按钮组件样式
 * 
 * 包含各种按钮样式：主要按钮、次要按钮等
 */

/* ==========================================================================
   按钮组件
   ========================================================================== */

.btn {
  // 基础按钮样式
  display: inline-block;
  padding: 0.375rem 0.75rem;
  
  // 悬停效果
  &:hover {
    opacity: 0.8;
  }
}

/* 按钮变体
   ========================================================================== */

.btn--primary {
  // 主要按钮样式
  background-color: #007bff;
  color: white;
}
```

## 11. 工具和检查清单

### 推荐工具
- **Sass**: Dart Sass (推荐)
- **Stylelint**: 代码检查
- **Autoprefixer**: 自动前缀
- **PostCSS**: CSS 处理

### Stylelint 基本配置
```json
{
  "extends": "stylelint-config-standard-scss",
  "rules": {
    "indentation": 2,
    "string-quotes": "single",
    "selector-max-id": 0,
    "declaration-colon-space-after": "always",
    "declaration-colon-space-before": "never"
  }
}
```

### 提交前检查清单
- [ ] 代码通过 Stylelint 检查
- [ ] 遵循 BEM 命名约定
- [ ] 选择器嵌套不超过 3 层
- [ ] 使用了适当的变量和 mixins
- [ ] 没有重复的样式
- [ ] 添加了必要的注释
- [ ] 考虑了响应式设计

**记住：好的 CSS 代码简洁、模块化、易于维护。**