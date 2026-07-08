# About GTF
GTF is a Google Test Framework tool developed internally to assist in creating and managing unit tests for embedded software projects in automotive. It is not affiliated with Google LLC or the official Google Test Framework.
GTF is an advanced extension to Google Test, incorporating automated report generation and comprehensive coverage analysis. This framework elevates testing capabilities by providing detailed insights into test outcomes and code coverage, ensuring thorough evaluation and robust software quality assessment.

# GTF in VS Code
This extension integrates GTF functionalities directly into Visual Studio Code, enabling developers to leverage GTF's powerful features within their preferred development environment. With this extension, users can easily generate, run, and analyze unit tests using GTF, streamlining the testing process and enhancing productivity.

# GTF VS Code Extension tools for AI Agent
This extension provides several tools for AI Agents to assist developers in generating and managing unit tests using GTF:

- `gtf-get-info`:  
  Retrieve GTF tool information, including version, Conan usage, available build variants, and installation path.

- `gtf-run-tests`:  
  Run Google Test tests using GTF, specifying the test folder and build variant. Returns error, stderr, and stdout details.

- `gtf-build-clean`:  
  Clean the GTF build environment by removing temporary build files and resetting the build state.

- `gtf-get-test-results`:  
  Get parsed GTF test results, filtered by status (all, passed, or failed).

- `gtf-install`:  
  Install the GTF tool in your current VS Code environment.

# GTF Test-Harness Structure
In GTF, the test-harness is the `gtest` folder inside each software component/unit. This folder is mandatory for GTF-based unit testing and contains the full test setup. The typical location is `test/gtest`, but it can also be nested (e.g., `test/sw-unit/gtest`). Every component/unit tested with GTF should have a `gtest` folder.
Key elements of the test-harness:

- **gtest/CMakeLists.txt**:  
  Main configuration file. Defines test files, source files, mocks, stubs, and build variants. The `module_name` variable specifies the actual component/unit name.

- **gtest/unitest_configs.cmake**:  
  Controls coverage settings (high/medium level, decision/MCDC coverage), and file exclusions for coverage.

- **gtest/prj/**:  
  Contains folders for each build variant, each with its own `CMakeLists.txt` for executable and variant-specific configuration.

- **gtest/prj/tfr/**:  
  Holds files for dependency solving (stubs/mocks) to isolate the unit under test. The location of these files can be changed in the main `gtest/CMakeLists.txt`, similar to the tests folder.

- **gtest/adapt/**:  
  Contains configuration files like `GTFconfig.xml` for GTF and report settings (coverage justification, test spec config). Also includes `conanfile.txt`, which specifies the GTF version to use when running GTF manually from the command line (outside VS Code). In VS Code, the extension manages the GTF version automatically.

- **gtest/tests/**:  
  Default location for test files (can be changed via `gtest/CMakeLists.txt`).

The test-harness links the software component/unit to GTF, enabling configuration and execution of unit tests using GTF (Conan package). The structure and files above are essential for proper GTF operation and unit testing support.

# Dependency Isolation in GTF: Mocks, Wrappers, and Stubs

For C/C++ unit testing with GTF, dependency isolation is achieved using mocks, wrappers, and stubs:

- **Mocks**:  
  Implemented as C++ classes using Google Mock (`gmock/gmock.h`).  
  Use `MOCK_METHOD` macros to declare mockable methods for each dependency.  
  Mocks are typically placed in dedicated source and header files within the test-harness (e.g., in a `mocks` folder).  
  For proper test isolation, use a singleton pointer and provide explicit constructors and destructors for each mock class. This ensures that each test initializes and cleans up its mock instance, preventing cross-test contamination.

- **Wrappers**:  
  C functions are implemented in C++ source files as wrappers.  
  Each wrapper function calls the corresponding mock method on a singleton mock object.  
  This allows C code to interact with C++ mocks: C code calls the wrapper, which calls the mock.

- **Stubs**:  
  Declared in header files (e.g., in a `stub` folder).  
  Provide prototypes for wrapper functions and any missing datatypes or function prototypes needed for isolation.

**How it works:**  
- The C code under test calls a dependency function.  
- The function is implemented as a wrapper in C++ that calls the mock method.  
- The mock method is defined in a Google Mock class, allowing flexible test behavior.  
- Stubs ensure all necessary prototypes and types are available for compilation.

**Note:**
- The locations of mocks, wrappers, and stubs are configurable in the main `CMakeLists.txt`.
- Users can add compiler definitions, includes, and other build settings for dependency solving in the main and variant CMake files. Build variants in CMake are for build configuration and should not be confused with the `@Variant` field in test comment blocks.

# Working with GoogleTest Tests in GTF

When working with GoogleTest tests in GTF, follow these rules for documentation, grouping, and handling mocks and external interfaces to ensure traceability, compliance, and proper test isolation:

## Test Documentation

- **Each test must have a comment block directly above it.**
- Use the following template for each test:

```cpp
/**
* @Trace: Requirement or SWDD id taken from Module Specification
* @Variant: Imported from specification (can have multiple entries)
* @Description: Description/notes/comments of the test. List test steps here.
* <br>TestStep1: {test step 1}
* <br>TestStep2: {test step 2}
* <br>{more test steps here}
* @DesignTechnique: N/A
* @Input: Input values used by the test
* @Result: Expected output/result from the test
* <br>{expected result line 2}
* <br>{more expected result lines here}
* @FunctionSafety: yes/no
* @Security: non-SPR
* @TestMaturity: Draft
* @TechnicalRegulation: non-LTR
* @ChangeRequest: N/A
*/
```

## Test Comment Block Field Explanations

- **Trace**: Requirement or SWDD ID from the Module Specification or SWDD.
- **Variant**: Info from Requirement Management tool or SWDD.
- **Description**: Short description of the test (custom user information).
- **Input**: Input(s) for the test (custom user information).
- **DesignTechnique**: The design technique used.
- **Result**: Expected result from the test (custom user information).
- **FunctionalSafety**: "yes" or "no" (any other value is invalid).
- **Security**: "non-SPR" or "SPR" (optional; if missing, defaults to "non-SPR").
- **TestMaturity**: "draft", "review-ready", or "released" (optional; if missing, defaults to "draft").
- **TechnicalRegulation**: "non-LTR" or "LTR" (optional; if missing, defaults to "non-LTR").
- **ChangeRequest**: "N/A" or link to Jira ticket (optional; if missing, defaults to "N/A").

## Test Grouping

- **Tests can be grouped using a group comment block placed above them.**
- All tests following a group comment block (until the next group block) will be part of that group in the generated testspec.
- Use the following template for each group:

```cpp
/**
* @GroupName: Function Name, Objective, Fixture Name, or other group name
* @Description: Description/notes/comments of the group
* @Order: -1
*/
```

- Multiple groups can be defined in the same test file. The order of groups and tests in the file determines their grouping in the generated testspec.

## Mocks and External Interfaces

- **Always check for external interfaces and dependencies when writing tests.**
- If mocks exist for these interfaces, use them in your tests to ensure proper isolation.
- If mocks do not exist, create appropriate mocks for external dependencies before writing the test.
- Never interact directly with external interfaces in unit tests—always use mocks or stubs to isolate the unit under test.

## Summary

- Always document each test and group using the provided templates.
- Ensure traceability to requirements and clear description of test steps and expected results.
- Proper grouping helps organize tests and improves the quality of generated documentation.

# GTF Unit-Testing Compliance and Best Practices

- **Follow MISRA guidelines for all code and tests.**
- **Apply best practices for automotive unit testing.**
- **Ensure compliance with ASPICE 4.0 for all test activities.**

# GTF Unit-Testing Common Test Techniques

Use the following standard techniques when designing tests (examples included):

- **Equivalence Partitioning:**  
  Divide input data into valid and invalid partitions, and test one value from each.
  - Example: For a function accepting values 1–100, test with 0, 1, 50, 100, 101.

- **Boundary Value Analysis:**  
  Test at the edges of input ranges.
  - Example: For a range 1–100, test with 1, 100, and values just outside (0, 101).

- **State Transition Testing:**  
  Test all possible states and transitions in state machines.
  - Example: For a login system, test transitions between "logged out", "logging in", "logged in", "logging out".

- **Error Guessing:**  
  Use experience to guess likely error-prone areas.
  - Example: Test with null pointers, empty strings, or unexpected input formats.

- **Decision Table Testing:**  
  Use tables to cover combinations of conditions and actions.
  - Example: For a payment system, test combinations of payment method, amount, and user status.

# GTF Troubleshooting and Tips

- **Missing Coverage Files:**  
  If tests run but coverage files are not generated, it often indicates a hidden runtime error such as memory corruption, segmentation fault, or abnormal process termination. These errors may not be displayed directly in the test output, especially if the coverage tool relies on post-execution data collection.

- **SEH Error in Test Output:**  
  An SEH (Structured Exception Handling) error in the test error message usually indicates memory problems, such as accessing an uninitialized pointer or memory corruption.
