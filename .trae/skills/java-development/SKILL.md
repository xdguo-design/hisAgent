---
name: "java-development"
description: "Java开发助手，生成符合阿里规范的代码。Invoke when user asks for Java code development, Spring Boot application, or backend service implementation."
---

# Java Development Assistant

Java 开发助手，专注于生成符合阿里 Java 规范的高质量代码。

## 核心原则

**所有生成的代码必须严格遵循《阿里巴巴 Java 开发手册》规范。**

## 编码规范要求

### 命名规范

1. **类名**：使用 UpperCamelCase（大驼峰），名词形式
   - 正确：`UserService`, `OrderController`, `DataTransferObject`
   - 错误：`userService`, `order_controller`, `GetUserInfo`

2. **方法名**：使用 lowerCamelCase（小驼峰），动词或动词短语开头
   - 正确：`getUserById()`, `createOrder()`, `validatePassword()`
   - 错误：`GetUserById()`, `Create_Order()`, `user_data`

3. **变量名**：使用 lowerCamelCase
   - 正确：`userName`, `totalCount`, `isValid`
   - 错误：`UserName`, `total_count`, `_isValid`

4. **常量名**：全部大写，单词间用下划线分隔
   - 正确：`MAX_RETRY_COUNT`, `DEFAULT_PAGE_SIZE`, `API_BASE_URL`
   - 错误：`maxRetryCount`, `default_page_size`, `apiBaseUrl`

5. **包名**：全部小写，单词间用点分隔，不以 org、com 开头时需有明确归属
   - 正确：`com.company.project.module`, `cn.example.app.service`
   - 错误：`com.company.project.Module`, `Com.Example.App`

### 代码风格

1. **缩进**：统一使用 4 个空格，禁止使用 Tab

2. **大括号**：左大括号不换行，右大括号独占一行
   ```java
   // 正确
   if (condition) {
       doSomething();
   }
   
   // 错误
   if (condition)
   {
       doSomething();
   }
   ```

3. **每行长度**：不超过 120 个字符，超出需换行并保持缩进

4. **空行**：
   - 类成员变量与方法之间空一行
   - 方法与方法之间空一行
   - 逻辑块之间可空一行增强可读性

### OOP 规范

1. **访问控制**：
   - 成员变量私有化（private），通过 getter/setter 访问
   - 方法根据需要使用 public/protected/private

2. **单一职责**：每个类只负责一个功能领域

3. **依赖倒置**：面向接口编程，而非面向实现

4. **避免魔法值**：使用常量或枚举替代硬编码

### 异常处理

1. **不要捕获 Exception 或 Throwable**：精确捕获具体异常类型

2. **不要生吞异常**：
   ```java
   // 错误
   try {
       doSomething();
   } catch (Exception e) {
       
   }
   
   // 正确
   try {
       doSomething();
   } catch (IOException e) {
       log.error("文件操作失败", e);
       throw new BusinessException("文件处理异常", e);
   }
   ```

3. **finally 块不要返回值**

### 集合使用

1. **初始化时指定容量**：
   ```java
   // 正确
   List<String> list = new ArrayList<>(16);
   Map<String, Object> map = new HashMap<>(16);
   
   // 错误
   List<String> list = new ArrayList<>();
   ```

2. **使用 isEmpty() 判断空**：不要用 `size() == 0`

3. **遍历时不要删除元素**：使用 Iterator 或 removeIf

### 字符串处理

1. **字符串比较使用 equals()**：禁止使用 `==`

2. **优先使用 StringBuilder**：在循环中拼接字符串

3. **常量字符串使用 intern()**：减少内存占用

### 并发编程

1. **线程池创建**：
   ```java
   // 正确：使用 ThreadPoolExecutor 或自定义配置
   ThreadPoolExecutor executor = new ThreadPoolExecutor(
       corePoolSize,
       maximumPoolSize,
       keepAliveTime,
       TimeUnit.SECONDS,
       new LinkedBlockingQueue<>(100),
       new ThreadFactoryBuilder().setNameFormat("pool-%d").build(),
       new ThreadPoolExecutor.CallerRunsPolicy()
   );
   
   // 错误：直接使用 Executors
   ExecutorService executor = Executors.newFixedThreadPool(10);
   ```

2. **避免锁嵌套**：防止死锁

3. **使用 ConcurrentHashMap**：而非 Collections.synchronizedMap

### 日志规范

1. **使用占位符**：
   ```java
   // 正确
   log.info("用户登录成功，userId: {}, userName: {}", userId, userName);
   
   // 错误
   log.info("用户登录成功，userId: " + userId + ", userName: " + userName);
   ```

2. **日志级别**：
   - ERROR：系统错误、异常
   - WARN：警告、可恢复问题
   - INFO：关键业务流程
   - DEBUG：调试信息

3. **禁止生产环境使用 System.out/err**

### 数据库操作

1. **使用 PreparedStatement**：防止 SQL 注入

2. **禁止在循环中查询数据库**：使用批量操作

3. **大结果集分页查询**：避免一次性加载

4. **事务注解**：`@Transactional` 明确指定传播行为和回滚策略

### 注释规范

1. **类注释**：描述类的职责、作者、日期
   ```java
   /**
    * 用户服务类
    * 提供用户信息的增删改查功能
    * 
    * @author 张三
    * @since 2024-01-01
    */
   ```

2. **方法注释**：描述功能、参数、返回值、异常
   ```java
   /**
    * 根据用户ID查询用户信息
    * 
    * @param userId 用户ID，不能为空
    * @return 用户信息，不存在返回null
    * @throws IllegalArgumentException userId为空时抛出
    */
   ```

3. **复杂逻辑添加行内注释**

## Spring Boot 开发规范

### Controller 层

```java
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
public class UserController {
    
    private final UserService userService;
    
    @PostMapping
    public Result<UserVO> createUser(@Valid @RequestBody UserCreateRequest request) {
        UserVO user = userService.createUser(request);
        return Result.success(user);
    }
    
    @GetMapping("/{id}")
    public Result<UserVO> getUser(@PathVariable Long id) {
        UserVO user = userService.getUserById(id);
        return Result.success(user);
    }
}
```

### Service 层

```java
@Service
@RequiredArgsConstructor
public class UserServiceImpl implements UserService {
    
    private final UserRepository userRepository;
    private final UserMapper userMapper;
    
    @Override
    @Transactional(rollbackFor = Exception.class)
    public UserVO createUser(UserCreateRequest request) {
        User user = userMapper.toEntity(request);
        user = userRepository.save(user);
        return userMapper.toVO(user);
    }
}
```

### Entity 层

```java
@Entity
@Table(name = "t_user")
@EqualsAndHashCode(callSuper = true)
@Data
public class User extends BaseEntity {
    
    @Column(name = "user_name", nullable = false, length = 64)
    private String userName;
    
    @Column(name = "email", length = 128)
    private String email;
    
    @Column(name = "status", length = 16)
    private String status;
}
```

### DTO/VO 规范

- **Request**：接收请求参数
- **Response**：返回响应数据
- **VO**：前端展示对象
- **DTO**：数据传输对象

### 异常处理

```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    
    @ExceptionHandler(BusinessException.class)
    public Result<Void> handleBusinessException(BusinessException e) {
        log.warn("业务异常: {}", e.getMessage());
        return Result.error(e.getCode(), e.getMessage());
    }
    
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<Void> handleValidationException(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getAllErrors().get(0).getDefaultMessage();
        return Result.error(ErrorCode.INVALID_PARAM, message);
    }
}
```

## 常用框架

根据项目需求选择合适的框架：

- **Web框架**：Spring Boot 2.7+/3.x
- **ORM框架**：MyBatis-Plus / Spring Data JPA
- **数据库连接池**：HikariCP
- **缓存**：Redis / Caffeine
- **消息队列**：RocketMQ / RabbitMQ
- **搜索**：Elasticsearch
- **API文档**：Swagger / Knife4j

## 代码审查检查清单

生成代码后，请自查以下项目：

- [ ] 命名符合规范（类名、方法名、变量名、常量名）
- [ ] 缩进使用4个空格
- [ ] 大括号位置正确
- [ ] 集合初始化指定容量
- [ ] 异常处理不使用生吞
- [ ] 字符串比较使用equals()
- [ ] 日志使用占位符格式
- [ ] 事务注解指定回滚策略
- [ ] 方法添加必要的注释
- [ ] 避免魔法值，使用常量

## 工作流程

1. 理解用户需求，明确功能规格
2. 设计类结构和方法签名
3. 按照阿里规范编写代码
4. 添加必要的注释和文档
5. 生成单元测试代码（如需要）
6. 提供使用示例
