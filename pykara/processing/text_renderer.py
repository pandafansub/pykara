"""Text rendering for template bodies."""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import CodeType

from pykara.engine.variable_context import Environment, set_random_callsite
from pykara.errors import (
    BoundMethodInExpressionError,
    TemplateCodeError,
    TemplateRuntimeError,
    UnknownVariableError,
)
from pykara.specification.expressions import EXPRESSION_PROPERTY_SPECIFICATIONS

_VARIABLE_PATTERN = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
_EXPRESSION_PATTERN = re.compile(r"!(.+?)!", re.DOTALL)
_ALIAS_EXPRESSION_BY_VARIABLE = {
    spec.source_variable: f"{object_name}.{property_name}"
    for (object_name, property_name), spec in (
        EXPRESSION_PROPERTY_SPECIFICATIONS.items()
    )
    if spec.source_variable is not None
}


@dataclass(frozen=True, slots=True)
class _TextToken:
    kind: str
    value: str
    index: int = 0


class TextRenderer:
    """Render template text by expanding variables and expressions."""

    def __init__(self) -> None:
        self._compiled_expression_cache: dict[str, CodeType] = {}
        self._token_cache: dict[str, tuple[_TextToken, ...]] = {}

    def render(self, text: str, env: Environment) -> str:
        """Expand `$var` and `!expr!` in one template string."""

        if "$" not in text and "!" not in text:
            return text

        rendered: list[str] = []
        variables: dict[str, object] | None = None
        namespace: dict[str, object] | None = None
        for token in self._tokens(text):
            if token.kind == "literal":
                rendered.append(token.value)
                continue

            if token.kind == "variable":
                if variables is None:
                    variables = env.variable_dict()
                rendered.append(
                    self._replace_variable(
                        token.value,
                        text,
                        variables,
                    )
                )
                continue

            expression = self._render_expression_variables(
                token.value,
                text,
                env,
            )
            if namespace is None:
                namespace = env.as_dict()
            if env.line is not None:
                env.line.text = "".join(rendered)
            rendered.append(
                self._replace_expression(
                    expression,
                    namespace,
                    (text, token.index),
                )
            )
            variables = None

        return "".join(rendered)

    def _tokens(self, text: str) -> tuple[_TextToken, ...]:
        cached = self._token_cache.get(text)
        if cached is not None:
            return cached

        tokens: list[_TextToken] = []
        literal_start = 0
        position = 0
        while position < len(text):
            variable_match = _VARIABLE_PATTERN.match(text, position)
            if variable_match is not None:
                if literal_start < position:
                    tokens.append(
                        _TextToken("literal", text[literal_start:position])
                    )
                tokens.append(_TextToken("variable", variable_match.group(1)))
                position = variable_match.end()
                literal_start = position
                continue

            expression_match = _EXPRESSION_PATTERN.match(text, position)
            if expression_match is not None:
                if literal_start < position:
                    tokens.append(
                        _TextToken("literal", text[literal_start:position])
                    )
                tokens.append(
                    _TextToken(
                        "expression",
                        expression_match.group(1),
                        expression_match.start(),
                    )
                )
                position = expression_match.end()
                literal_start = position
                continue

            position += 1

        if literal_start < len(text):
            tokens.append(_TextToken("literal", text[literal_start:]))

        cached = tuple(tokens)
        self._token_cache[text] = cached
        return cached

    def evaluate_expression(
        self,
        expression: str,
        env: Environment,
    ) -> object:
        """Evaluate one inline expression in the closed environment."""

        compiled = self._compile_expression(expression)
        return self._evaluate_compiled(
            expression,
            compiled,
            env.as_dict(),
            expression,
        )

    def _replace_variable(
        self,
        variable_name: str,
        template_text: str,
        variables: dict[str, object],
    ) -> str:
        if variable_name not in variables:
            raise UnknownVariableError(variable_name, template_text)
        return str(variables[variable_name])

    def _render_expression_variables(
        self,
        expression: str,
        template_text: str,
        env: Environment,
    ) -> str:
        if "$" not in expression:
            return expression
        variables: dict[str, object] | None = None

        def replace(match: re.Match[str]) -> str:
            nonlocal variables
            variable_name = match.group(1)
            if variable_name in _ALIAS_EXPRESSION_BY_VARIABLE:
                return _ALIAS_EXPRESSION_BY_VARIABLE[variable_name]
            if variables is None:
                variables = env.variable_dict()
            return self._replace_variable(
                variable_name,
                template_text,
                variables,
            )

        return _VARIABLE_PATTERN.sub(
            replace,
            expression,
        )

    def _replace_expression(
        self,
        expression: str,
        namespace: dict[str, object],
        callsite: object,
    ) -> str:
        compiled = self._compile_expression(expression)
        result = self._evaluate_compiled(
            expression,
            compiled,
            namespace,
            callsite,
        )
        if result is None:
            return ""
        try:
            return str(result)
        except Exception as error:  # pragma: no cover - exercised in tests
            raise TemplateRuntimeError(expression, error) from error

    def _compile_expression(self, expression: str) -> CodeType:
        try:
            compiled = self._compiled_expression_cache.get(expression)
            if compiled is None:
                compiled = compile(expression, "<pykara-expression>", "eval")
                self._compiled_expression_cache[expression] = compiled
        except SyntaxError as error:
            raise TemplateCodeError(expression, error) from error
        return compiled

    def _evaluate_compiled(
        self,
        expression: str,
        compiled: CodeType,
        namespace: dict[str, object],
        callsite: object,
    ) -> object:
        set_random_callsite(namespace, callsite)
        try:
            result = eval(  # noqa: S307
                compiled,
                {"__builtins__": {}},
                namespace,
            )
        except Exception as error:  # pragma: no cover - exercised in tests
            raise TemplateRuntimeError(expression, error) from error

        if callable(result):
            raise BoundMethodInExpressionError(
                expression=expression,
                result_type=type(result).__name__,
            )
        return result
