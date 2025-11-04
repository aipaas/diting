## ADDED Requirements

### Requirement: Optimizer Package Documentation
The diting-optimizer package SHALL provide comprehensive documentation that explains its optimization capabilities, algorithms, and usage patterns.

#### Scenario: Developer discovers optimizer package
- **WHEN** a developer navigates to packages/diting-optimizer/
- **THEN** they find a README.md that clearly explains the package's purpose and capabilities
- **AND** the README provides a quickstart guide with working examples

#### Scenario: User wants to understand optimization algorithms
- **WHEN** a user reads the documentation
- **THEN** they find detailed explanations of TPE and Hierarchical Reflective optimization
- **AND** each algorithm includes use cases and configuration examples

#### Scenario: Developer integrates optimizer
- **WHEN** a developer wants to integrate the optimizer into their project
- **THEN** the documentation provides clear API interface examples
- **AND** shows integration patterns with diting-core components

#### Scenario: Contributor wants to extend optimizer
- **WHEN** a contributor examines the package structure
- **THEN** the documentation explains the architecture patterns
- **AND** provides guidance for adding new optimization algorithms

### Requirement: Documentation Consistency
The optimizer documentation SHALL maintain consistency with existing diting-core documentation patterns.

#### Scenario: Cross-package reference
- **WHEN** a user reads both diting-core and diting-optimizer documentation
- **THEN** they find consistent formatting, terminology, and structure
- **AND** cross-references between packages are clearly indicated

#### Scenario: Documentation maintenance
- **WHEN** the codebase evolves
- **THEN** the documentation structure supports easy updates
- **AND** examples remain technically accurate with current APIs