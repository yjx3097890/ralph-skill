---
inclusion: always
---

# JavaScript 代码规范（精简版）

基于 Airbnb JavaScript Style Guide

## 核心原则

- **可读性**：代码易于阅读和理解
- **一致性**：保持一致的编码风格
- **现代化**：使用现代 ES6+ 特性
- **性能**：考虑代码性能影响

## 1. 变量声明

```javascript
// ✅ 好的做法
const name = '张三';
const users = [];
let count = 0;

// ❌ 不好的做法
var name = '张三';  // 不要使用 var
```

## 2. 对象

```javascript
// ✅ 好的做法 - 字面量语法
const item = {};

// 计算属性名
const obj = {
  id: 5,
  [getKey('enabled')]: true,
};

// 方法简写
const atom = {
  value: 1,
  addValue(value) {
    return atom.value + value;
  },
};

// 属性简写
const obj = { lukeSkywalker };

// 解构
function getFullName({ firstName, lastName }) {
  return `${firstName} ${lastName}`;
}

// 默认值
function processUser({ name = '匿名用户', age = 0 } = {}) {
  return { name, age };
}
```

## 3. 数组

```javascript
// ✅ 好的做法
const items = [];
someStack.push('abracadabra');

// 解构
const [first, second] = arr;
const [head, ...tail] = arr;

// 数组方法
const doubled = numbers.map(num => num * 2);
const evens = numbers.filter(num => num % 2 === 0);
const sum = numbers.reduce((total, num) => total + num, 0);

// 复制数组
const itemsCopy = [...items];

// 类数组转换
const nodes = Array.from(foo);
const nodes = [...foo];
```

## 4. 字符串

```javascript
// ✅ 好的做法 - 单引号
const name = '张三';

// 模板字符串
function sayHi(name) {
  return `你好，${name}！`;
}

// ❌ 不好的做法
const name = "张三";  // 不要使用双引号
const message = '你好，' + name + '！';  // 不要字符串拼接
```

## 5. 函数

```javascript
// ✅ 好的做法 - 箭头函数
[1, 2, 3].map((x) => x * x);

// 多行箭头函数
[1, 2, 3].map((number) => {
  const nextNumber = number + 1;
  return `A string containing the ${nextNumber}.`;
});

// 默认参数
function handleThings(name = 'defaultName') {
  // ...
}

// 参数解构
function processUser({ name, age, email }) {
  // 使用 name, age, email
}

// 剩余参数
function concatenateAll(...args) {
  return args.join('');
}

// ❌ 不好的做法
[1, 2, 3].map(function (x) {
  return x * x;
});
```

## 6. 类

```javascript
// ✅ 好的做法
class Queue {
  constructor(contents = []) {
    this.queue = [...contents];
  }
  
  pop() {
    const value = this.queue[0];
    this.queue.splice(0, 1);
    return value;
  }
}

// 继承
class PeekableQueue extends Queue {
  peek() {
    return this.queue[0];
  }
}

// 方法链
class Jedi {
  jump() {
    this.jumping = true;
    return this;
  }

  setHeight(height) {
    this.height = height;
    return this;
  }
}

const luke = new Jedi();
luke.jump().setHeight(20);
```

## 7. 模块

```javascript
// ✅ 好的做法 - ES6 模块
export default class CheckBox {
  // ...
}

export { CheckBox };
export const PI = 3.14159;

// 导入
import CheckBox from './CheckBox';
import { PI } from './math';
import * as MathUtils from './math';

// 导入顺序：Node 模块 → 第三方库 → 本地模块
import fs from 'fs';
import React from 'react';
import CheckBox from './CheckBox';

// ❌ 不好的做法
const CheckBox = require('./CheckBox');
module.exports = CheckBox;
```

## 8. 比较和条件

```javascript
// ✅ 好的做法 - 严格相等
if (name === 'John') {
  // ...
}

if (count !== 0) {
  // ...
}

// 条件语句
if (collection.length > 0) {
  // ...
}

// 三元运算符
const foo = maybe1 > maybe2 ? 'bar' : maybeNull;

// 长条件语句
if (
  foo === 123 &&
  bar === 'abc' &&
  baz === true
) {
  thing1();
}

// ❌ 不好的做法
if (name == 'John') {  // 不要使用 ==
  // ...
}
```

## 9. 代码格式

```javascript
// ✅ 好的做法 - 2 个空格缩进
function foo() {
  const name = 'John';
  if (name === 'John') {
    return true;
  }
  return false;
}

// 大括号前加空格
function test() {
  console.log('test');
}

if (condition) {
  // ...
}

// 运算符空格
const x = y + 5;
const result = a > b ? a : b;

// 尾随逗号
const hero = {
  firstName: 'Dana',
  lastName: 'Scully',
};

const heroes = [
  'Batman',
  'Superman',
];
```

## 10. 命名规范

```javascript
// ✅ 好的做法
// 驼峰命名法 - 变量和函数
const thisIsMyObject = {};
const thisIsMyFunction = () => {};

// 帕斯卡命名法 - 类和构造函数
class User {
  constructor(options) {
    this.name = options.name;
  }
}

// 不要使用下划线前缀
class Calculator {
  constructor() {
    this.number = 42;
  }
}

// ❌ 不好的做法
const this_is_my_object = {};  // 不要使用下划线
class calculator { }           // 类名应该大写开头
```

## 11. 注释

```javascript
// ✅ 好的做法
/**
 * 计算用户的总积分
 * @param {Object} user - 用户对象
 * @param {Array} activities - 活动列表
 * @return {number} 总积分
 */
function calculateUserScore(user, activities) {
  // ...
}

// 单行注释
// 检查用户是否有权限
if (user.hasPermission('admin')) {
  // ...
}

// ❌ 不好的做法
//这是一个单行注释  // 注释前没有空格
if (user.hasPermission('admin')) { // 检查用户是否有权限  // 行末注释
  // ...
}
```

## 12. 类型转换

```javascript
// ✅ 好的做法
// 字符串转换
const totalScore = String(this.reviewScore);

// 数字转换
const val = Number(inputValue);
const val = parseInt(inputValue, 10);

// 布尔转换
const hasAge = Boolean(age);
const hasAge = !!age;

// ❌ 不好的做法
const totalScore = this.reviewScore + '';  // 不要用 + ''
const val = +inputValue;                   // 不要用一元 +
const hasAge = new Boolean(age);           // 不要用构造函数
```

## 13. 高阶函数

```javascript
// ✅ 好的做法 - 优先使用数组方法
const numbers = [1, 2, 3, 4, 5];

const sum = numbers.reduce((total, num) => total + num, 0);
const doubled = numbers.map(num => num * 2);
const evens = numbers.filter(num => num % 2 === 0);

// 生成器函数
function* fibonacci() {
  let a = 0;
  let b = 1;
  
  while (true) {
    yield a;
    [a, b] = [b, a + b];
  }
}

// ❌ 不好的做法 - 使用 for 循环
let sum = 0;
for (const num of numbers) {
  sum += num;
}
```

## 14. 存取器

```javascript
// ✅ 好的做法
class Dragon {
  get age() {
    // ...
  }

  set age(value) {
    // ...
  }
}

// 布尔值存取器
if (dragon.hasAge()) {
  return dragon.getAge();
}

// ❌ 不好的做法
class Dragon {
  getAge() {    // 不要用 get 前缀
    // ...
  }
}
```

## 15. 工具和检查清单

### 推荐工具
- **ESLint**: 代码检查
- **Prettier**: 代码格式化
- **Jest**: 测试框架

### 提交前检查清单
- [ ] 使用 const/let 而不是 var
- [ ] 使用箭头函数
- [ ] 使用模板字符串
- [ ] 使用解构赋值
- [ ] 使用严格相等 (===)
- [ ] 添加尾随逗号
- [ ] 使用分号
- [ ] 遵循命名规范
- [ ] 通过 ESLint 检查

**记住：好的 JavaScript 代码简洁、现代、易于维护。**