# Pluggable parsers

Parsing is a **strategy**, not a fixed pipeline. By default CLInch uses a
line-by-line regex engine built from your model's `_field_patterns`, but any
object conforming to the `Parser` protocol can be dropped in — either to reuse
a battle-tested parser from [jc](https://github.com/kellyjonbrazil/jc), or to
parse output the regex engine cannot express.

The whole contract is one method:

```python
from clinch.parsing import Parser, ParserOutput

class MyParser:
    def parse(self, output: str) -> ParserOutput:
        ...
```

The engine takes whatever `ParserOutput.records` you return, constructs
`model(**record)` for each, and collects Pydantic validation errors into
`ParsingResult.failures` — exactly as it does for regex-parsed records.

## Binding a parser to a model

Set `_cli_parser` on your response model. When it is `None` (the default),
the regex engine is used, so existing code is unaffected:

```python
from clinch import BaseCLIResponse, CLIWrapper
from clinch.parsing import JCParser

class DigAnswer(BaseCLIResponse):
    _cli_parser = JCParser("dig")

    name: str
    ttl: int
    data: str

class DigWrapper(CLIWrapper):
    command = "dig"

    def answers(self, host: str) -> ParsingResult[DigAnswer]:
        return self._execute("+noall", "+answer", host, response_model=DigAnswer)
```

You can also pass a parser explicitly instead of binding it to the model:

```python
from clinch.parsing import parse_output

result = parse_output(DigAnswer, raw_output, parser=JCParser("dig"))
```

## Using jc

jc ships 170+ parsers (`ps`, `df`, `dig`, `ifconfig`, `netstat`, ...). Install
the optional extra and wrap any of them with `JCParser`:

```bash
pip install clinch[jc]
```

```python
from clinch.parsing import JCParser

class PsEntry(BaseCLIResponse):
    _cli_parser = JCParser("ps")

    pid: int
    command: str
```

Extra keyword arguments are forwarded to `jc.parse()` (e.g.
`JCParser("ps", quiet=True)`). If jc is not installed, `JCParser.parse()` raises
an `ImportError` with install instructions.

## Writing a custom parser

For output no existing parser handles, implement the protocol directly:

```python
from clinch.parsing import Parser, ParserOutput

class StatsParser:
    """Parse a stanza like 'cpu: 42' / 'mem: 128' into records."""

    def parse(self, output: str) -> ParserOutput:
        records = []
        for line in output.splitlines():
            key, _, value = line.partition(":")
            if key and value.strip():
                records.append({"key": key.strip(), "value": value.strip()})
        return ParserOutput(records=records)

class StatResponse(BaseCLIResponse):
    _cli_parser = StatsParser()

    key: str
    value: str
```

## Responsibilities

* **Input**: a single string containing the full output. The engine normalizes
  iterables of lines to a string before calling `parse`.
* **Output**: raw dicts whose keys match model field names. Type coercion and
  validation are the engine's job, not yours.
* **Failures**: report lines you cannot parse via `ParserOutput.failures` (a
  `list[ParsingFailure]`). Exceptions raised from `parse` are caught by the
  engine and recorded as a failure, so a flaky parser never crashes the call.
