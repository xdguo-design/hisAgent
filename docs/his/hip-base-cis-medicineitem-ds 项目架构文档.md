# hip-base-cis-medicineitem-ds 项目架构文档

## 概述
这是一个基于 Spring Cloud 的医疗信息系统（HIS）中的**医护管理-医嘱项目微服务**，属于 HIP v5.0 平台的一部分。负责管理医嘱项目字典及相关业务功能。

## 技术栈
- **Java** + **Spring Boot** + **Spring Cloud**
- **Spring Data JPA** (hip-jpa)
- **OpenFeign** 远程调用
- **RabbitMQ** (spring-rabbit, hip-amqp) 消息队列
- **二级缓存** (hip-l2caching)
- **SpringDoc OpenAPI** 接口文档

## 模块结构
```
hip-base-cis-medicineitem-ds/
├── hip-base-cis-medicineitem-api/      # API层：接口定义、DTO对象
├── hip-base-cis-medicineitem-service/  # 服务层：业务实现、实体、仓储
└── hip-base-cis-medicineitem-feign/    # Feign客户端：远程调用封装
```

### 1. hip-base-cis-medicineitem-api
- **职责**: 定义服务接口契约和数据传输对象
- **核心包结构**:
  - `serviceItem/service/` - 服务接口定义 (RESTful API)
  - `serviceItem/to/` - 传输对象 (To、Qto、Nto、Eto)
  - `serviceItemExt/` - 医嘱项目扩展
  - `price/service/` - 价格相关服务接口
  - `limitOrg/service/` - 限制科室服务接口

### 2. hip-base-cis-medicineitem-service
- **职责**: 业务逻辑实现
- **核心包结构**:
  - `entity/` - JPA实体类
  - `service/internal/` - 服务实现类
  - `service/internal/assembler/` - 对象转换器(Assembler)

### 3. hip-base-cis-medicineitem-feign
- **职责**: 提供Feign客户端供其他微服务调用
- **核心类**: `*ServiceFeign.java` Feign接口

## 业务领域

### 核心实体
| 实体 | 说明 |
|------|------|
| ServiceClinicItem | 医嘱项目字典 |
| ServiceClinicPrice | 医嘱项目与物价项目关联 |
| Operation | 手术项目 |
| OperationApply | 手术申请 |
| BloodApply | 输血申请 |
| ConsultationApply | 会诊申请 |
| AnesthesiaApply | 麻醉申请 |
| DgimgApply | 影像检查申请 |
| TreatmentApply | 治疗申请 |
| NursingItem | 护理项目 |
| EntrustItem | 嘱托项目 |
| ManagementItem | 管理项目 |
| LimitCreateOrg/LimitExecOrg | 科室限制 |

### 主要服务
| 服务 | 说明 |
|------|------|
| ServiceClinicItemService | 医嘱项目字典管理（CRUD、缓存查询）|
| OperationService | 手术项目管理 |
| OperationApplyService | 手术申请管理 |
| BloodApplyService | 输血申请管理 |
| ServiceClinicPriceService | 医嘱物价关联管理 |
| LimitExecOrgService | 执行科室限制 |
| LimitCreateOrgService | 开方科室限制 |

## 依赖服务
- `hip-term-api` - 术语服务
- `hip-org-api` - 组织机构服务
- `hip-base-cis-dict-api` - CIS字典服务
- `hip-base-cis-diagnose-api` - 诊断服务
- `hip-econ-price-api` - 物价服务

## 数据表
- `CIS_SERVICE_CLINIC_ITEM` - 医嘱项目字典
- `CIS_SERVICE_CLINIC_ITEM_PRICE` - 医嘱项目与物价项目关联

## 架构分层图
```
┌─────────────────────────────────────────────────────┐
│                  Other Microservices                │
│                (通过Feign调用)                       │
└─────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────┐
│          hip-base-cis-medicineitem-feign            │
│           (Feign Client 远程调用封装)               │
└─────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────┐
│           hip-base-cis-medicineitem-api             │
│        (接口定义 + DTO + Service Interface)         │
└─────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────┐
│         hip-base-cis-medicineitem-service           │
│  ┌───────────────────────────────────────────────┐  │
│  │     Controller / Service Implementation       │  │
│  ├───────────────────────────────────────────────┤  │
│  │           Entity + Repository                 │  │
│  ├───────────────────────────────────────────────┤  │
│  │     L2 Cache (Redis) + JPA (Database)         │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```
