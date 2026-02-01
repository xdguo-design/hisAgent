# 门诊挂号系统开发方案

## 1. 技术架构设计

### 1.1 整体架构
采用基于DDD的分层架构：
- **表现层**：Spring MVC + RESTful API
- **应用层**：Spring Boot Service层，负责业务流程编排
- **领域层**：核心业务逻辑，包含实体、值对象、领域服务
- **基础设施层**：MyBatis Plus、MySQL、Redis等

### 1.2 技术栈
- **框架**：Spring Boot 2.7.x
- **持久层**：MyBatis Plus 3.5.x
- **数据库**：MySQL 8.0
- **缓存**：Redis 6.0
- **安全认证**：Spring Security + JWT
- **API文档**：Swagger 3.0

### 1.3 模块划分
```
hospital-registration-system
├── registration-api          # 接口定义模块
├── registration-domain      # 领域模型模块
├── registration-application # 应用服务模块
├── registration-infrastructure # 基础设施模块
└── registration-web          # Web接口模块
```

## 2. 数据库设计建议

### 2.1 核心表结构

#### 患者信息表(patient)
```sql
CREATE TABLE patient (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    patient_no VARCHAR(32) NOT NULL COMMENT '患者编号',
    name VARCHAR(50) NOT NULL COMMENT '患者姓名',
    gender TINYINT NOT NULL COMMENT '性别:1-男,2-女',
    id_card VARCHAR(18) NOT NULL COMMENT '身份证号',
    birth_date DATE COMMENT '出生日期',
    phone VARCHAR(20) NOT NULL COMMENT '联系电话',
    address VARCHAR(200) COMMENT '家庭住址',
    created_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_patient_no (patient_no),
    UNIQUE KEY uk_id_card (id_card)
) COMMENT '患者信息表';
```

#### 科室表(department)
```sql
CREATE TABLE department (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    dept_code VARCHAR(32) NOT NULL COMMENT '科室编码',
    dept_name VARCHAR(50) NOT NULL COMMENT '科室名称',
    parent_id BIGINT DEFAULT 0 COMMENT '父科室ID',
    is_active TINYINT NOT NULL DEFAULT 1 COMMENT '是否启用:1-启用,0-停用',
    created_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_dept_code (dept_code)
) COMMENT '科室表';
```

#### 医生表(doctor)
```sql
CREATE TABLE doctor (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    doctor_no VARCHAR(32) NOT NULL COMMENT '医生工号',
    name VARCHAR(50) NOT NULL COMMENT '医生姓名',
    title VARCHAR(20) NOT NULL COMMENT '职称',
    dept_id BIGINT NOT NULL COMMENT '所属科室ID',
    specialty TEXT COMMENT '专长',
    is_active TINYINT NOT NULL DEFAULT 1 COMMENT '是否在职:1-在职,0-离职',
    created_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (dept_id) REFERENCES department(id),
    UNIQUE KEY uk_doctor_no (doctor_no)
) COMMENT '医生表';
```

#### 医生排班表(doctor_schedule)
```sql
CREATE TABLE doctor_schedule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    doctor_id BIGINT NOT NULL COMMENT '医生ID',
    schedule_date DATE NOT NULL COMMENT '排班日期',
    period TINYINT NOT NULL COMMENT '时段:1-上午,2-下午,3-晚上',
    max_patient_count INT NOT NULL DEFAULT 0 COMMENT '最大接诊人数',
    registration_fee DECIMAL(10,2) NOT NULL COMMENT '挂号费',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态:1-可预约,2-已满,3-停诊',
    created_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctor(id),
    KEY idx_schedule_date (schedule_date),
    KEY idx_doctor_date (doctor_id, schedule_date)
) COMMENT '医生排班表';
```

#### 挂号记录表(registration)
```sql
CREATE TABLE registration (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    registration_no VARCHAR(32) NOT NULL COMMENT '挂号单号',
    patient_id BIGINT NOT NULL COMMENT '患者ID',
    doctor_id BIGINT NOT NULL COMMENT '医生ID',
    schedule_id BIGINT NOT NULL COMMENT '排班ID',
    dept_id BIGINT NOT NULL COMMENT '科室ID',
    registration_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '挂号时间',
    visit_date DATE NOT NULL COMMENT '就诊日期',
    period TINYINT NOT NULL COMMENT '就诊时段',
    registration_fee DECIMAL(10,2) NOT NULL COMMENT '挂号费',
    payment_status TINYINT NOT NULL DEFAULT 0 COMMENT '支付状态:0-未支付,1-已支付',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态:1-待就诊,2-已就诊,3-取消',
    created_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patient(id),
    FOREIGN KEY (doctor_id) REFERENCES doctor(id),
    FOREIGN KEY (schedule_id) REFERENCES doctor_schedule(id),
    FOREIGN KEY (dept_id) REFERENCES department(id),
    UNIQUE KEY uk_registration_no (registration_no)
) COMMENT '挂号记录表';
```

### 2.2 索引设计
- 为所有外键字段创建索引
- 为常用查询条件创建组合索引
- 为状态字段创建索引

## 3. 核心业务逻辑实现

### 3.1 领域模型设计

#### 患者实体(Patient)
```java
@Entity
@Table(name = "patient")
public class Patient {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "patient_no", unique = true, nullable = false)
    private String patientNo;
    
    @Column(name = "name", nullable = false)
    private String name;
    
    @Enumerated(EnumType.ORDINAL)
    @Column(name = "gender", nullable = false)
    private Gender gender;
    
    @Column(name = "id_card", unique = true, nullable = false)
    private String idCard;
    
    @Column(name = "birth_date")
    private LocalDate birthDate;
    
    @Column(name = "phone", nullable = false)
    private String phone;
    
    @Column(name = "address")
    private String address;
    
    // 构造方法、getter、setter等
}
```

#### 挂号单实体(Registration)
```java
@Entity
@Table(name = "registration")
public class Registration {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "registration_no", unique = true, nullable = false)
    private String registrationNo;
    
    @ManyToOne
    @JoinColumn(name = "patient_id", nullable = false)
    private Patient patient;
    
    @ManyToOne
    @JoinColumn(name = "doctor_id", nullable = false)
    private Doctor doctor;
    
    @ManyToOne
    @JoinColumn(name = "schedule_id", nullable = false)
    private DoctorSchedule schedule;
    
    @ManyToOne
    @JoinColumn(name = "dept_id", nullable = false)
    private Department department;
    
    @Column(name = "registration_time", nullable = false)
    private LocalDateTime registrationTime;
    
    @Column(name = "visit_date", nullable = false)
    private LocalDate visitDate;
    
    @Enumerated(EnumType.ORDINAL)
    @Column(name = "period", nullable = false)
    private Period period;
    
    @Column(name = "registration_fee", nullable = false, precision = 10, scale = 2)
    private BigDecimal registrationFee;
    
    @Enumerated(EnumType.ORDINAL)
    @Column(name = "payment_status", nullable = false)
    private PaymentStatus paymentStatus;
    
    @Enumerated(EnumType.ORDINAL)
    @Column(name = "status", nullable = false)
    private RegistrationStatus status;
    
    // 业务方法
    public void confirmPayment() {
        if (this.paymentStatus != PaymentStatus.UNPAID) {
            throw new BusinessException("挂号单已支付或支付状态异常");
        }
        this.paymentStatus = PaymentStatus.PAID;
        this.status = RegistrationStatus.PENDING_VISIT;
    }
    
    public void cancelRegistration() {
        if (this.status == RegistrationStatus.COMPLETED) {
            throw new BusinessException("已就诊的挂号单不能取消");
        }
        if (this.paymentStatus == PaymentStatus.PAID) {
            // 退款逻辑
        }
        this.status = RegistrationStatus.CANCELLED;
    }
    
    // 构造方法、getter、setter等
}
```

### 3.2 应用服务实现

#### 挂号服务(RegistrationService)
```java