---
title: "VMS Decision Log (ADR Index)"
status: active
doc_type: adr
project: "global"
owner: "@jlane"
updated: 2025-01-27
tags: ["adr", "decisions", "architecture", "vms"]
summary: "Index of Architecture Decision Records (ADRs) across all VMS projects. Central reference for technical decisions and their rationale."
canonical: "/docs/living/DecisionLog.md"
---

# VMS Decision Log (ADR Index)

## 📋 **Overview**

This document serves as the central index of Architecture Decision Records (ADRs) across all VMS projects.

ADRs are immutable records of significant technical decisions that capture the context, decision, and consequences for future reference.

## 🔍 **ADR Search & Filtering**

### **By Project**
- **Global**: System-wide decisions
- **Validation System**: Data validation and quality decisions
- **GUI Enhancements**: User interface and experience decisions
- **Data Integration**: Salesforce and external system decisions

### **By Decision Type**
- **Technology**: Framework, language, and tool choices
- **Architecture**: System design and structure decisions
- **Data**: Database, storage, and data flow decisions
- **Integration**: External system and API decisions

### **By Status**
- **Accepted**: Decision implemented and in use
- **Proposed**: Decision under consideration
- **Deprecated**: Decision superseded by newer approach
- **Archived**: Decision no longer relevant

## 📚 **ADR Directory**

### **Global System Decisions**

#### **G-001: Flask as Web Framework** ✅ Accepted
- **Date**: 2024-01-15
- **Status**: Accepted
- **Project**: Global
- **Summary**: Choose Flask over Django for lightweight, flexible web development
- **Location**: `/docs/old/projects/global/ADR/G-001-flask-framework.md`
- **Key Points**: Lightweight, Python-native, easy deployment, good for solo development

#### **G-002: SQLite as Primary Database** ✅ Accepted
- **Date**: 2024-01-20
- **Status**: Accepted
- **Project**: Global
- **Summary**: Use SQLite for development and production to simplify deployment
- **Location**: `/docs/old/projects/global/ADR/G-002-sqlite-database.md`
- **Key Points**: File-based, no server setup, good for PythonAnywhere hosting

#### **G-003: Vanilla JavaScript Frontend** ✅ Accepted
- **Date**: 2024-02-01
- **Status**: Accepted
- **Project**: Global
- **Summary**: Avoid JavaScript frameworks in favor of vanilla JS for simplicity
- **Location**: `/docs/old/projects/global/ADR/G-003-vanilla-javascript.md`
- **Key Points**: No build process, easier debugging, better performance

### **Validation System Decisions**

#### **V-001: Comprehensive Validation Architecture** ✅ Accepted
- **Date**: 2024-06-01
- **Status**: Accepted
- **Project**: Validation System
- **Summary**: Implement 5-tier validation system (Count, Completeness, Data Type, Relationship, Business Rules)
- **Location**: `/docs/old/projects/validation/ADR/V-001-validation-architecture.md`
- **Key Points**: Layered approach, configurable rules, comprehensive coverage

#### **V-002: Quality Scoring Algorithm** ✅ Accepted
- **Date**: 2024-08-01
- **Status**: Accepted
- **Project**: Validation System
- **Summary**: Implement weighted penalty system for data quality scoring
- **Location**: `/docs/old/projects/validation/ADR/V-002-quality-scoring.md`
- **Key Points**: Configurable weights, trend analysis, actionable insights

#### **V-003: Business Rule Engine** ✅ Accepted
- **Date**: 2024-09-01
- **Status**: Accepted
- **Project**: Validation System
- **Summary**: Create dynamic business rule validation system with templates
- **Location**: `/docs/old/projects/validation/ADR/V-003-business-rule-engine.md`
- **Key Points**: Dynamic loading, rule templates, versioning support

### **Data Integration Decisions**

#### **D-001: Salesforce API Integration** ✅ Accepted
- **Date**: 2024-03-01
- **Status**: Accepted
- **Project**: Data Integration
- **Summary**: Use Simple-Salesforce library for Salesforce CRM integration
- **Location**: `/docs/old/projects/data-integration/ADR/D-001-salesforce-api.md`
- **Key Points**: Python-native, OAuth 2.0, comprehensive object support

#### **D-002: Google Sheets Integration** ✅ Accepted
- **Date**: 2024-03-15
- **Status**: Accepted
- **Project**: Data Integration
- **Summary**: Implement Google Sheets API for data import/export operations
- **Location**: `/docs/old/projects/data-integration/ADR/D-002-google-sheets.md`
- **Key Points**: Service account authentication, batch operations, error handling

#### **D-003: Data Synchronization Strategy** ✅ Accepted
- **Date**: 2024-04-01
- **Status**: Accepted
- **Project**: Data Integration
- **Summary**: Implement daily automated synchronization with conflict resolution
- **Location**: `/docs/old/projects/data-integration/ADR/D-003-sync-strategy.md`
- **Key Points**: Automated daily sync, conflict detection, audit trail

### **GUI Enhancement Decisions**

#### **U-001: Mobile-First Responsive Design** ✅ Accepted
- **Date**: 2024-05-01
- **Status**: Accepted
- **Project**: GUI Enhancements
- **Summary**: Adopt mobile-first responsive design approach for all interfaces
- **Location**: `/docs/old/projects/gui-enhancements/ADR/U-001-mobile-first.md`
- **Key Points**: Mobile-first, CSS Grid/Flexbox, progressive enhancement

#### **U-002: Custom CSS Design System** ✅ Accepted
- **Date**: 2024-05-15
- **Status**: Accepted
- **Project**: GUI Enhancements
- **Summary**: Develop proprietary CSS design system instead of using frameworks
- **Location**: `/docs/old/projects/gui-enhancements/ADR/U-002-custom-css.md`
- **Key Points**: Brand consistency, performance, maintainability

## 📝 **Creating New ADRs**

### **When to Create an ADR**
- **Technology choices** that affect the entire system
- **Architecture decisions** that impact multiple components
- **Integration decisions** with external systems
- **Data model changes** that affect multiple entities
- **Performance optimizations** that change system behavior

### **ADR Template**
```markdown
---
title: "NNNN: <short decision>"
status: proposed | accepted | deprecated | archived
doc_type: adr
project: "<project_slug>"
owner: "@handle"
date: YYYY-MM-DD
summary: "<one paragraph what/why>"
---

## Context
[What is the issue that we're seeing that is motivating this decision or change?]

## Decision
[What is the change that we're proposing and/or doing?]

## Consequences
[What becomes easier or more difficult to do because of this change?]

## Alternatives considered
[What other options have been considered and why were they rejected?]

## Links
[Links to related decisions, documentation, or discussions]
```

### **ADR Numbering Convention**
- **G-XXX**: Global system decisions
- **V-XXX**: Validation system decisions
- **D-XXX**: Data integration decisions
- **U-XXX**: User interface decisions
- **P-XXX**: Performance decisions
- **S-XXX**: Security decisions

## 🔄 **ADR Lifecycle**

### **States**
1. **Proposed**: Decision under consideration and discussion
2. **Accepted**: Decision approved and being implemented
3. **Deprecated**: Decision superseded by newer approach
4. **Archived**: Decision no longer relevant to current system

### **Review Process**
- **Proposed ADRs**: Review within 1 week
- **Accepted ADRs**: Review annually for relevance
- **Deprecated ADRs**: Create new ADR explaining supersession
- **Archived ADRs**: Move to archive after 2 years

## 🔗 **Related Documents**

- **ADR Template**: `/docs/old/templates/adr.md`
- **System Overview**: `/docs/living/Overview.md`
- **Technology Stack**: `/docs/living/TechStack.md`
- **Project Planning**: `/docs/old/PLANNING.md`

## 📝 **Ask me (examples)**

- "What decisions were made about the validation system architecture?"
- "Why was Flask chosen over Django for the web framework?"
- "What are the current decisions about data integration?"
- "Are there any deprecated decisions that need updating?"
- "What's the process for creating a new ADR?"
