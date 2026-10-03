"""Checking authored code before it may join a configuration.

A configuration's rules and quests are Python files, and the product runs them. That is
deliberate — it is the only way to express logic no rule set ships — and it is bounded: code
loads from inside the configuration directory being edited and nowhere else.

Being bounded is not the same as being safe to load. A rule file with a syntax error, a typo
in an import, or a class that is not a rule at all loads at game start and fails there, in
the middle of a game, with the player holding no idea why. So the editor checks a module
before it is allowed to join the configuration, and this module is that check: parse it, run
it, and confirm it exposes the interface the framework calls.

What a check here can and cannot do is worth stating plainly. It confirms the module parses,
imports without raising, and declares something the rule or quest framework can use. It
cannot confirm the logic is *right* — a rule that forbids every move parses, imports and
declares `permits_move`, and is still wrong. That is what playing it is for.
"""

import ast
import importlib.abc
import importlib.machinery
import inspect
import os
from typing import Any, Dict, List, Optional, Tuple

from model.game.field import Field
from model.game.quest import WHENS, Quest
from model.game.rule import Rule

#: The parent class a rule module must expose a subclass of.
RULE_BASE = Rule

#: The parent class a quest module must expose a subclass of.
QUEST_BASE = Quest

#: The hook names a rule may override. A rule that overrides none of them changes nothing,
#: which is legal but almost certainly a mistake, so it is reported as a warning rather than
#: an error.
RULE_HOOKS = ("permits_move", "available_moves", "outcome", "on_move_made", "status")

#: The methods the rule framework calls on every rule. The parent class declares all of them,
#: so a subclass inherits them whether it wants them or not — what the check catches is a
#: subclass replacing one with something the framework cannot call.
RULE_METHODS = ("value_fields", "parameters", "permits_move", "outcome", "reset")

#: The attributes a rule carries that are read rather than called: its name, which the
#: settings form tab and the configuration file are keyed on.
RULE_ATTRIBUTES = ("default_name",)

#: The methods the quest framework calls on every quest.
QUEST_METHODS = ("parameters", "validate", "progress", "observe_move", "observe_result", "reset")

#: The attributes a quest carries that are read rather than called: its name, its description
#: and the moment it is judged at.
QUEST_ATTRIBUTES = ("default_name", "default_description", "when")


class _SourceLoader(importlib.abc.Loader):
    """A loader standing in for a module being checked rather than imported.

    A relative import inside a module needs the module to look like a real one: a `__name__`
    inside its package and a `__loader__` that can produce a spec for its siblings. This
    provides the loader without providing the module, so the check never registers the
    player's unsaved code in `sys.modules` — where it would shadow the file on disk from the
    moment they pressed Check until the program exited.

    Args:
        path: The path of the module being checked.
    """

    def __init__(self, path: str):
        """Stand in for the module at a path.

        Args:
            path: The path of the module being checked.
        """
        self.path = path

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> Optional[Any]:
        """Return the module to use, which is a fresh empty one.

        Args:
            spec: The spec being fulfilled.

        Returns:
            Optional[Any]: None, which asks the import machinery to create the module itself.
        """
        return None

    def exec_module(self, module: Any) -> None:
        """Do nothing: the module was executed by the check itself.

        Args:
            module: The module the machinery built.

        Returns:
            None
        """


class SourceReport:
    """What checking an authored module found.

    Attributes:
        ok: Whether the module may join the configuration.
        errors: Reasons it may not. Empty when `ok` is True.
        warnings: Things worth saying that do not prevent the module joining — a rule that
            overrides no hook, for instance, which is legal and useless.
        line: The 1-based line an error is about, when the error has one. A syntax error
            does; a missing class does not.
    """

    def __init__(
        self,
        ok: bool = True,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        line: Optional[int] = None,
    ):
        """Record what checking a module found.

        Args:
            ok: Whether the module may join the configuration.
            errors: Reasons it may not.
            warnings: Things worth saying that do not prevent the module joining.
            line: The 1-based line an error is about, when it has one.
        """
        self.ok = ok
        self.errors: List[str] = list(errors or [])
        self.warnings: List[str] = list(warnings or [])
        self.line = line

    def __bool__(self) -> bool:
        """Report whether the module may join the configuration.

        Returns:
            bool: True when `ok` is True.
        """
        return self.ok

    def message(self) -> str:
        """Return everything found, as one line a player can read.

        Returns:
            str: The errors followed by the warnings, or a statement that the module is
            sound when there was nothing to report.
        """
        parts = list(self.errors) + list(self.warnings)
        if not parts:
            return "No problems found."
        return " ".join(parts)

    def __repr__(self) -> str:
        """Return a debugging representation naming the verdict.

        Returns:
            str: Whether the module passed, and how many errors and warnings there were.
        """
        return f"SourceReport(ok={self.ok!r}, errors={len(self.errors)}, warnings={len(self.warnings)})"


def _declared_classes(tree: ast.Module) -> List[ast.ClassDef]:
    """Return the classes a module declares at its top level.

    Only top-level classes count. A class nested inside a function or another class is
    reachable by nobody the configuration composes, and the configuration composes by name.

    Args:
        tree: The parsed module.

    Returns:
        List[ast.ClassDef]: Every top-level class definition, in source order.
    """
    return [node for node in tree.body if isinstance(node, ast.ClassDef)]


def _base_names(node: ast.ClassDef) -> List[str]:
    """Return the names a class definition derives from.

    Args:
        node: The class definition.

    Returns:
        List[str]: Each base as written. Attribute bases (`module.Rule`) are reduced to their
        last part, because that is how they are usually imported.
    """
    names: List[str] = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
    return names


def _overrides(node: ast.ClassDef, names: Tuple[str, ...]) -> List[str]:
    """Return which of `names` a class defines for itself.

    Args:
        node: The class definition.
        names: The member names to look for.

    Returns:
        List[str]: The names the class body defines at class level.
    """
    defined = {
        child.name
        for child in node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assigned = {
        target.id
        for child in node.body
        if isinstance(child, ast.Assign)
        for target in child.targets
        if isinstance(target, ast.Name)
    }
    return [name for name in names if name in defined or name in assigned]


def _implements(namespace: Dict[str, Any], base: type) -> List[type]:
    """Return the classes a module's namespace holds that are usable framework classes.

    The class found by executing the module is authoritative, because the text says what was
    meant and the executed module says what there is.

    Args:
        namespace: The module's namespace after execution.
        base: The parent class a usable class must derive from.

    Returns:
        List[type]: The usable classes, in the order the namespace holds them.
    """
    return [
        value
        for value in namespace.values()
        if isinstance(value, type) and value is not base and issubclass(value, base)
    ]


def _where(candidate: type, node: Optional[ast.ClassDef]) -> str:
    """Return how to name a class and where it is, for a message about it.

    Args:
        candidate: The class being reported on.
        node: Its parsed definition, or None when it was not declared in this file.

    Returns:
        str: `Name (line N)` when the line is known, otherwise just the name.
    """
    line = node.lineno if node is not None else None
    return f"{candidate.__name__} (line {line})" if line else candidate.__name__


def _interface_errors(
    candidate: type,
    node: Optional[ast.ClassDef],
    methods: Tuple[str, ...],
    attributes: Tuple[str, ...],
) -> List[str]:
    """Report what a candidate class has replaced with something unusable.

    The parent class declares every member the framework uses, so a subclass normally inherits
    all of them. What can go wrong is a subclass replacing one with something the framework
    cannot use: a `value_fields` that is not callable, a `default_name` that is not a string,
    a `when` that is not one of the moments the engine dispatches on. Inheritance itself is
    not a fault and is not reported.

    Args:
        candidate: The class to check.
        node: The parsed class definition, used for the reported line.
        methods: The member names the framework calls on this kind of object.
        attributes: The member names the framework reads on this kind of object.

    Returns:
        List[str]: One message per member that is present but unusable, or absent. Empty when
        the class exposes an interface the framework can use.
    """
    where = _where(candidate, node)
    problems: List[str] = []
    for name in methods:
        member = getattr(candidate, name, None)
        if member is None:
            problems.append(f"{where} does not expose {name}().")
        elif not callable(member):
            problems.append(f"{where}.{name} is {type(member).__name__}, which cannot be called.")
    for name in attributes:
        member = getattr(candidate, name, None)
        if member is None:
            problems.append(f"{where} does not expose {name}.")
        elif not isinstance(member, str):
            problems.append(f"{where}.{name} is {type(member).__name__}, not the text it must be.")
    return problems


def _takes_required_arguments(candidate: type) -> bool:
    """Report whether a class must be built with an argument.

    A configuration composes its rules and quests explicitly, so a quest may quite properly
    demand the piece type it judges — chess's `CaptureOfType("queen")` does exactly that. What
    cannot be checked is whether the configuration supplies it, so a class that requires an
    argument is left alone: the check has nothing to say about it.

    Args:
        candidate: The class to inspect.

    Returns:
        bool: True when building it with no arguments would fail for want of an argument.
    """
    try:
        signature = inspect.signature(candidate)
    except (TypeError, ValueError):  # pragma: no cover - a class whose signature is unreadable
        return True
    return any(
        parameter.default is inspect.Parameter.empty
        and parameter.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        for parameter in signature.parameters.values()
    )


def _instantiation_problem(candidate: type, node: Optional[ast.ClassDef]) -> Optional[str]:
    """Report why a candidate class cannot be built, if it cannot be built at all.

    A class taking no required arguments can be built here, and a constructor that raises is
    a fault worth reporting now rather than at game start. A class that requires an argument
    is not built: the configuration passes it, and refusing it here would refuse every quest
    that names a piece.

    Args:
        candidate: The class to try to build.
        node: The parsed class definition, used for the reported line.

    Returns:
        Optional[str]: Why it cannot be built, or None when it can or need not be.
    """
    if _takes_required_arguments(candidate):
        return None
    try:
        candidate()
    except Exception as error:  # noqa: BLE001 - any constructor failure is the player's code
        return f"{_where(candidate, node)} raised {type(error).__name__} when built: {error}"
    return None


def _declaration_problem(candidate: type, node: Optional[ast.ClassDef]) -> Optional[str]:
    """Report why a candidate class's field declaration is unusable, if it is.

    The settings form renders exactly what a rule declares, so a declaration that is not a
    list of `Field` breaks the form for the whole configuration rather than for one rule. It
    can only be asked of a class that builds with no arguments; one that does not is left to
    the configuration that knows how to build it.

    Args:
        candidate: The rule class to ask.
        node: The parsed class definition, used for the reported line.

    Returns:
        Optional[str]: Why the declaration is unusable, or None when it is fine or was not
        asked for.
    """
    if _takes_required_arguments(candidate):
        return None
    try:
        declared = candidate().value_fields()
    except Exception as error:  # noqa: BLE001 - any failure here is the player's code
        return (
            f"{_where(candidate, node)}.value_fields() raised " f"{type(error).__name__}: {error}"
        )
    if not isinstance(declared, list):
        return (
            f"{_where(candidate, node)}.value_fields() returned "
            f"{type(declared).__name__}, not a list"
        )
    for entry in declared:
        if not isinstance(entry, Field):
            return (
                f"{_where(candidate, node)}.value_fields() declared "
                f"{type(entry).__name__}, which is not a Field"
            )
    return None


def validate_source(source: str, path: str, kind: str = "rule", package: str = "") -> SourceReport:
    """Check an authored module before it may join a configuration.

    The check is: it parses; importing it does not raise; and it exposes at least one class
    the framework can build and use. That is the declared interface, and it is what the
    editor is required to confirm before code is allowed to join (FR-34).

    A module inside a configuration imports its siblings relatively, which is what makes a
    copy compose its own rules rather than the original's. Executing one therefore needs the
    package it belongs to, so `package` is the configuration's registered module name and the
    check resolves relative imports against it. Without it, a file doing `from .helpers
    import thing` reports an ImportError that is an artefact of checking rather than a fault
    in the code.

    Args:
        source: The module's text, as the player wrote it.
        path: The path it will be written to. Used in messages and as the filename the code
            is compiled under, so a traceback names the file the player wrote rather than
            `<string>`.
        kind: `"rule"` to require a `Rule` subclass, `"quest"` to require a `Quest` subclass.
        package: The configuration's registered module name, or "" when the module is not
            inside one and must import absolutely.

    Returns:
        SourceReport: The verdict, with every reason rather than only the first.

    Raises:
        ValueError: If `kind` is neither `"rule"` nor `"quest"`.
    """
    if kind not in ("rule", "quest"):
        raise ValueError(f"unknown source kind {kind!r}; expected 'rule' or 'quest'")
    base = RULE_BASE if kind == "rule" else QUEST_BASE
    methods = RULE_METHODS if kind == "rule" else QUEST_METHODS
    attributes = RULE_ATTRIBUTES if kind == "rule" else QUEST_ATTRIBUTES

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as error:
        message = error.msg or "the code does not parse"
        line = error.lineno
        where = f"line {line}" if line else "the file"
        return SourceReport(ok=False, errors=[f"{where}: {message}."], line=line)

    stem = os.path.basename(path)
    if stem.endswith(".py"):
        stem = stem[: -len(".py")]
    section = os.path.basename(os.path.dirname(path))
    namespace: Dict[str, Any] = {
        "__name__": f"{package}.{section}.{stem}" if package else stem,
        "__file__": path,
        "__doc__": None,
    }
    if package:
        namespace["__package__"] = f"{package}.{section}"
        namespace["__loader__"] = _SourceLoader(path)
    try:
        code = compile(tree, path, "exec")
        exec(code, namespace)  # noqa: S102 - running authored code is the product
    except Exception as error:  # noqa: BLE001 - every failure here is the player's code
        line = getattr(error, "lineno", None)
        message = f"{type(error).__name__}: {error}"
        where = f"line {line}: " if line else ""
        return SourceReport(ok=False, errors=[f"{where}{message}."], line=line)

    by_name = {node.name: node for node in _declared_classes(tree)}
    candidates = _implements(namespace, base)
    if not candidates:
        declared = ", ".join(sorted(by_name)) or "none"
        return SourceReport(
            ok=False,
            errors=[
                f"The module declares no class inheriting {base.__name__}. "
                f"It declares: {declared}."
            ],
        )

    errors: List[str] = []
    warnings: List[str] = []
    line: Optional[int] = None
    for candidate in candidates:
        # A class the file did not declare was imported from elsewhere inside the
        # configuration. That is legal — a variant may share a rule — and it is still held
        # to the same interface; it simply has no line in this file to report.
        node = by_name.get(candidate.__name__)
        problems = _interface_errors(candidate, node, methods, attributes)
        if node is not None and not problems and node.lineno:
            line = node.lineno
        built = _instantiation_problem(candidate, node)
        if built is not None:
            problems.append(built)
        if kind == "rule":
            fields_problem = _declaration_problem(candidate, node)
            if fields_problem is not None:
                problems.append(fields_problem)
            elif node is not None and not _overrides(node, RULE_HOOKS + ("value_fields",)):
                warnings.append(
                    f"{_where(candidate, node)} overrides no rule hook, so it changes nothing."
                )
        if kind == "quest" and getattr(candidate, "when", None) not in WHENS:
            problems.append(
                f"{_where(candidate, None)} declares "
                f"when={getattr(candidate, 'when', None)!r}, "
                f"which is not one of {', '.join(WHENS)}."
            )
        errors.extend(problems)

    if errors:
        return SourceReport(ok=False, errors=errors, warnings=warnings, line=line)
    return SourceReport(ok=True, warnings=warnings)
