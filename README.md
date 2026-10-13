*This activity has been created as part of the 42 curriculum by Safa Osama "salfaraw".*

# call_me_maybe

## Description

`call_me_maybe` is a function-calling project that explores how a small
Language Model (LLM) can translate natural-language requests into structured
function calls.

Instead of directly answering a request such as:

```text
What is the sum of 40 and 2?
```

the system must identify the appropriate function and generate its arguments
in a structured format:

```json
{
  "name": "fn_add_numbers",
  "parameters": {
    "a": 40,
    "b": 2
  }
}
```

The project uses the `Qwen/Qwen3-0.6B` model provided through the supplied
`llm_sdk` package.

The main challenge is to use **constrained decoding** so that the model
generates output that follows the required JSON structure and the function
schema, rather than relying only on prompting the model to produce valid
JSON.

The project demonstrates how token-level constraints can be applied to the
logits produced by a language model.

---

## Instructions

### Requirements

The project requires:

* Python 3.10 or later
* `uv`
* provided `llm_sdk`
* Pydantic

The project uses the Qwen/Qwen3-0.6B model through the provided SDK.

The activity must be executed through the following command:

```bash
uv run python -m src
```

### Installation

Install the project dependencies using:

```bash
make install
```

This runs:

```bash
uv sync
```

The reviewer and Moulinette are expected to install the project using
`uv sync`.

### Run

The default command is:

```bash
make run
```

which is equivalent to:

```bash
uv run python -m src
```

By default, the program reads:

```text
data/input/functions_definition.json
data/input/function_calling_tests.json
```

and writes:

```text
data/output/function_calling_results.json
```

### Custom Files

Custom input, output, and function-definition files can be supplied:

```bash
uv run python -m src \
    --functions_definition data/input/functions_definition.json \
    --input data/input/function_calling_tests.json \
    --output data/output/function_calling_results.json
```

### Debugging

The project provides a Makefile target for debugging:

```bash
make debug
```

This runs the program with Python's built-in debugger:

```bash
uv run python -m pdb -m src
```

### Linting

Run the required linting and type-checking commands with:

```bash
make lint
```

The project uses:

* `flake8`
* `mypy`
* `--warn-return-any`
* `--warn-unused-ignores`
* `--ignore-missing-imports`
* `--disallow-untyped-defs`
* `--check-untyped-defs`

An optional stricter check is available with:

```bash
make lint-strict
```

which uses:

```bash
mypy . --strict
```

### Cleaning

Temporary Python and type-checking caches can be removed with:

```bash
make clean
```

---

## Project Structure

```text
call_me_maybe/
├── data/
│   └── input/
│        ├── functions_definition.json
│        └── function_calling_tests.json
│   
│
├── llm_sdk/
│   ├── llm_sdk/
│   │    └── __init__.py
│   ├── pyproject.toml
│   └── uv.lock
│
├── src/
│   ├── __init__.py
│   ├── __main__.py
│   ├── constrained.py
│   ├── loader.py
│   ├── models.py
│   ├── pipeline.py
│   └── vocab.py
│
├── .gitignore
├── Makefile
├── pyproject.toml
└── README.md
```

The `output/` directory is generated when the program runs and should not be
included in the submitted repository.

---

# Input Files

## functions_definition.json

This file describes the functions that are available to the system.

Each function contains:

* `name`
* `description`
* `parameters`
* `returns`

For example:

```json
{
  "name": "fn_add_numbers",
  "description": "Add two numbers together and return their sum.",
  "parameters": {
    "a": {
      "type": "number"
    },
    "b": {
      "type": "number"
    }
  },
  "returns": {
    "type": "number"
  }
}
```

The implementation loads these definitions dynamically instead of
hardcoding the available functions.

This is important because the subject states that the function definitions
and test prompts may change during peer review.

---

## function_calling_tests.json

This file contains the natural-language prompts that must be processed.

Example:

```json
[
  {
    "prompt": "What is the sum of 2 and 3?"
  },
  {
    "prompt": "Greet John"
  },
  {
    "prompt": "Reverse the string 'hello'"
  }
]
```

The implementation must process the supplied prompts without hardcoding
solutions for the examples.

---

# Output Format

The program produces:

```text
data/output/function_calling_results.json
```

The output is a JSON array containing one object for each successfully
processed prompt.

Each object must contain exactly:

* `prompt`
* `name`
* `parameters`

Example:

```json
[
  {
    "prompt": "What is the sum of 2 and 3?",
    "name": "fn_add_numbers",
    "parameters": {
      "a": 2,
      "b": 3
    }
  }
]
```

The output must satisfy the function definition used for that request.

The following rules apply:

* The output must be valid JSON.
* No comments or trailing commas are allowed.
* No additional keys or prose are allowed.
* The function name must correspond to the available function definitions.
* All required parameters must be present.
* Parameter names must match the function definition.
* Parameter types must match the types specified in the function definition.

The implementation must not hardcode the examples provided in the subject.

---

# Algorithm

## Function Calling Pipeline

The project follows this general pipeline:

```text
Natural-language prompt
        |
        v
     Tokenizer
        |
        v
     Input IDs
        |
        v
   Qwen3-0.6B
        |
        v
      Logits
        |
        v
Constrained decoding
        |
        v
   Next token
        |
        v
Repeat until complete
        |
        v
Structured function call
```

The model generates one token at a time.

At each generation step, the model produces logits representing its score for
the possible next tokens.

The constrained decoder uses these logits but restricts which tokens are
allowed before selecting the next token.

---

## Constrained Decoding

The central idea of this project is to prevent the model from generating
tokens that would violate the required output structure.

The process is:

1. Run the model and obtain logits for the next token.
2. Determine which tokens are valid according to the current generation
   state.
3. Remove or ignore tokens that cannot satisfy the required structure.
4. Select the highest-scoring valid token.
5. Add the selected token to the generated sequence.
6. Repeat until the complete function call has been generated.

Conceptually:

```text
Model logits
     |
     v
Identify valid tokens
     |
     v
Reject invalid tokens
     |
     v
Select highest-scoring valid token
     |
     v
Append token
     |
     v
Repeat
```

The purpose is to guarantee that the generated sequence follows the required
grammar and schema rather than relying only on the model's natural ability to
produce JSON.

---

## Literal Constraints

Some parts of the output are known in advance.

For example:

```text
{"name": "
```

and:

```text
", "parameters": {
```

For these parts, the implementation checks the decoded representation of
vocabulary tokens and only permits tokens that can continue the expected
literal.

This is important because a token may represent multiple characters.

The implementation therefore works with decoded token text rather than
assuming that one token corresponds to one character.

---

## Function Selection

The function name must correspond to one of the functions supplied in
`functions_definition.json`.

The implementation builds a list of candidate function names and uses the
LLM's logits to choose between them.

At every generation step, tokens that cannot continue any remaining function
name are rejected.

For example, if the available functions are:

```text
fn_add_numbers
fn_greet
fn_reverse_string
```

the decoder progressively restricts the possible next tokens until a
function name has been selected.

This ensures that the generated function name is taken from the supplied
function definitions rather than being freely generated text.

---

## Parameter Generation

After selecting the function, the implementation generates its parameters
according to the parameter definitions.

### Number Parameters

Number parameters are generated using token-level restrictions intended to
allow numeric characters such as:

```text
0 1 2 3 4 5 6 7 8 9
.
-
e
E
```

The generated value is then converted to the corresponding Python numeric
type.

The function definition determines whether the parameter is treated as an
`integer` or a `number`.

### String Parameters

String parameters are generated while preventing characters that would
prematurely terminate the JSON string, such as quotation marks and raw
newlines.

The resulting value is stored as a string parameter in the generated
function call.

---

# Design Decisions

## Pydantic

Pydantic is used to validate structured input data.

The project defines models for:

* function definitions
* parameter definitions
* return definitions
* test prompts
* generated function-call results

This provides a clear schema for the data processed by the program.

---

## Vocabulary Handling

The provided vocabulary file is loaded directly by the project.

The implementation converts vocabulary entries into decoded text so that
the constrained decoder can reason about what each token represents.

This is necessary because the decoder operates at token level.

---

## Provided LLM SDK

The project uses the public functionality exposed by the provided
`Small_LLM_Model` class.

The implementation uses methods such as:

```text
get_logits_from_input_ids()
get_path_to_vocab_file()
encode()
```

Private methods or private attributes of the SDK are not used.

---

## Token-Level Generation

The implementation does not assume that characters and tokens have a
one-to-one relationship.

A single token can represent multiple characters, so literal constraints
compare the decoded token text with the remaining expected output.

This is particularly important when constraining JSON syntax and function
names.

---

# Performance and Reliability

The subject defines the following target requirements:

* **90%+** correct function selection and argument extraction
* **100%** valid and schema-compliant JSON output
* Processing all test prompts in **under 5 minutes** on standard hardware
* Graceful handling of malformed input, missing files, and edge cases

These are project requirements and targets. Actual measured performance
should be reported only after running the final implementation and recording
the results.

Performance depends on factors such as:

* hardware
* model loading time
* number of prompts
* number of available functions
* length of prompts
* number and type of parameters

---

# Challenges

## Small Language Model

The project uses a small language model, `Qwen/Qwen3-0.6B`.

Small models can be less reliable when asked to produce strict structured
output.

Constrained decoding addresses this problem by restricting the available
tokens instead of relying entirely on prompting.

---

## Tokenization

A token is not necessarily a single character.

For example, a token may represent several characters or include spacing
information.

Therefore, the implementation compares decoded token text against the
required output rather than assuming character-by-character generation.

---

## Function Name Selection

The model must select an appropriate function from a dynamically supplied
set of function definitions.

The implementation handles this by maintaining possible function-name
candidates and restricting the next token to candidates that remain possible.

---

## Malformed Input

The subject explicitly requires robust handling of malformed or missing
input files.

The loaders therefore handle cases such as:

* missing files
* invalid JSON
* invalid Pydantic structures

Clear error messages are produced instead of allowing these input errors to
cause unexplained failures.

---

# Testing Strategy

Testing should verify both normal behavior and edge cases.

## Provided Test Data

The implementation should be tested using:

```text
data/input/function_calling_tests.json
```

and:

```text
data/input/functions_definition.json
```

The function names and generated parameter structures should be checked
against the supplied definitions.

---

## Edge Cases

Testing should include:

* empty strings
* large numbers
* special characters
* ambiguous prompts
* multiple parameters
* different function sets
* malformed JSON
* missing input files
* invalid parameter definitions
* prompts requiring different parameter types

The goal is to verify that the implementation does not depend on the
specific examples included with the project.

---

## Schema Validation

Generated results should be validated against the expected function
definition.

The following should be checked:

* function name
* parameter names
* parameter count
* parameter types
* required fields
* JSON syntax

---

## Linting and Type Checking

The project should be checked using:

```bash
make lint
```

and, when appropriate:

```bash
make lint-strict
```

The implementation uses type hints and Pydantic models to make the data
flow easier to validate.

---

# Example Usage

## Default Execution

```bash
uv run python -m src
```

or:

```bash
make run
```

The program reads the default input files and creates:

```text
data/output/function_calling_results.json
```

---

## Custom Execution

```bash
uv run python -m src \
    --functions_definition data/input/functions_definition.json \
    --input data/input/function_calling_tests.json \
    --output data/output/function_calling_results.json
```

---

# Resources

The following resources are relevant to the project:

* 42 `call_me_maybe` subject documentation
* Python documentation
* Pydantic documentation
* `uv` documentation
* Qwen/Qwen3-0.6B documentation
* Documentation and references related to tokenization
* Documentation and references related to constrained decoding
* JSON specification and documentation

The subject matter itself serves as the primary reference for the project requirements.

---

# AI Usage

AI tools were used as a learning and development assistant during this
activity.

AI was used for tasks such as:

* explaining function calling concepts
* explaining constrained decoding
* discussing tokenization concepts
* debugging implementation issues
* improving documentation
* helping organize the README

---