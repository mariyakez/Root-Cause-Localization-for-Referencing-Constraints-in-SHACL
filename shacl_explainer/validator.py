import os
import shlex
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from rdflib import Graph, Namespace

SH = Namespace("http://www.w3.org/ns/shacl#")

DEFAULT_JENA_TIMEOUT = 300.0


def _coerce_graph(graph_or_path, rdf_format: str = "turtle"):
    if isinstance(graph_or_path, Graph):
        return graph_or_path

    path = Path(graph_or_path)
    if path.suffix.lower() in {".pkl", ".pickle"}:
        with open(path, "rb") as handle:
            loaded = handle.read()
        import pickle

        graph = pickle.loads(loaded)
        if not isinstance(graph, Graph):
            raise TypeError(f"Expected an rdflib.Graph in {path}, got {type(graph).__name__}")
        return graph

    return Graph().parse(str(path), format=rdf_format)


def run_validation(
    data_path: str,
    shapes_path: str,
    engine: str = "jena",
    report_path: Optional[str] = None,
    env: Optional[dict] = None,
    data_format: str = "turtle",
    shapes_format: str = "turtle",
    report_format: str = "turtle",
    jena_command: Optional[str] = None,
    data_source: Optional[str] = None,
    shapes_source: Optional[str] = None,
    jena_timeout: Optional[float] = DEFAULT_JENA_TIMEOUT,
):
    """Run SHACL validation with a pluggable backend.

    Jena is the default validator for the top-level conforms/results check.
    pyshacl remains available as an alternate top-level engine, and is also
    a required dependency regardless of engine choice: the explanation tree
    builder (expander.py/fallback.py) uses it to reconstruct nested
    sh:node/sh:property detail that Jena's report doesn't include.

    ``data_path``/``shapes_path`` may be a file path or an already-parsed
    ``Graph``. When the jena engine is used and an in-memory ``Graph`` was
    passed (as the CLI does, since it already parsed the graphs for stats
    and tree-building), ``data_source``/``shapes_source`` let the caller
    supply the original on-disk file so it can be handed to the Jena CLI
    directly instead of being re-serialized to a throwaway temp file.
    """
    effective_env = dict(os.environ)
    if env:
        effective_env.update(env)

    engine_name = (engine or "jena").lower()
    data_graph = _coerce_graph(data_path, rdf_format=data_format)
    shapes_graph = _coerce_graph(shapes_path, rdf_format=shapes_format)

    if engine_name == "pyshacl":
        try:
            import pyshacl
        except ImportError as exc:
            raise RuntimeError(
                "The pyshacl engine was requested, but the 'pyshacl' package is not installed. "
                "Install it with: pip install -r requirements.txt"
            ) from exc

        start = time.perf_counter()
        conforms, report_graph, _ = pyshacl.validate(
            data_graph,
            shacl_graph=shapes_graph,
            inference="none",
            abort_on_first=False,
            serialize_report_graph=False,
        )
        elapsed = time.perf_counter() - start
        return conforms, report_graph, {"validate": elapsed, "pyshacl": elapsed}

    if engine_name == "jena":
        data_input = _resolve_jena_input(data_path, data_source, data_graph, data_format)
        shapes_input = _resolve_jena_input(shapes_path, shapes_source, shapes_graph, shapes_format)
        return run_jena_validation(
            data_path=data_input,
            shapes_path=shapes_input,
            report_path=report_path,
            env=effective_env,
            jena_command=jena_command,
            timeout=jena_timeout,
        )

    raise ValueError(f"Unsupported validation engine: {engine}")


def _resolve_jena_input(original, source_path, graph: Graph, rdf_format: str) -> str:
    """Pick the file to hand to the Jena CLI, avoiding a parse/serialize round-trip when possible.

    Only turtle on-disk files are passed through as-is, since that's the only
    format the Jena command line is assumed to auto-detect here; anything
    else (a different declared format, a pickle, or data that only exists as
    an in-memory Graph) falls back to serializing the already-parsed graph to
    a throwaway turtle temp file, exactly as before.
    """
    if rdf_format == "turtle":
        for candidate in (source_path, original):
            if not isinstance(candidate, (str, Path)):
                continue
            candidate_path = Path(candidate)
            if candidate_path.suffix.lower() not in {".pkl", ".pickle"} and candidate_path.is_file():
                return str(candidate)

    return _write_temp_graph(graph, suffix=".ttl")


def _write_temp_graph(graph: Graph, suffix: str = ".ttl") -> str:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        graph.serialize(destination=handle.name, format="turtle")
        return handle.name


def run_jena_validation(
    data_path: str,
    shapes_path: str,
    report_path: Optional[str] = None,
    env: Optional[dict] = None,
    jena_command: Optional[str] = None,
    timeout: Optional[float] = DEFAULT_JENA_TIMEOUT,
):
    effective_env = dict(os.environ)
    if env:
        effective_env.update(env)

    command = jena_command or effective_env.get("JENA_SHACL_COMMAND")
    if not command:
        raise RuntimeError(
            "Jena validation requested, but no executable was provided. Set --jena-command or "
            "JENA_SHACL_COMMAND to a command such as '/opt/homebrew/opt/jena/bin/shacl validate "
            "--data {data} --shapes {shapes}'."
        )

    if not report_path:
        with tempfile.NamedTemporaryFile(suffix=".ttl", delete=False) as handle:
            report_path = handle.name

    effective_env["REPORT"] = report_path

    start = time.perf_counter()
    try:
        argv = build_jena_command(command, data_path, shapes_path, report_path)
        completed = subprocess.run(
            argv, check=True, env=effective_env, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Jena validation failed because the command could not be started: {exc}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Jena validation command timed out after {timeout}s. Pass a larger --jena-timeout "
            "for big graphs, or check whether the command is hanging on input."
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        raise RuntimeError(f"Jena validation command failed: {stderr or exc}") from exc
    finally:
        elapsed = time.perf_counter() - start

    output_text = (completed.stdout or "") if "completed" in locals() else ""
    report_graph = _build_report_graph_from_output(output_text, report_path)
    conforms_value = report_graph.value(predicate=SH.conforms)
    if conforms_value is not None:
        conforms = bool(conforms_value.toPython())
    else:
        conforms = False
    return conforms, report_graph, {"validate": elapsed, "jena": elapsed}


def _build_report_graph_from_output(output_text: str, report_path: str) -> Graph:
    """Load the SHACL validation report Jena produced.

    Only real RDF is accepted here. Earlier versions fell back to scraping
    Jena's free-text console output with regexes, which only ever captured the
    first violation and silently reported ``sh:conforms true`` whenever the
    text didn't match the guessed format -- both of which can hide real
    violations from the explainer. If Jena didn't produce a parseable report,
    that's a configuration error the caller needs to fix, not something to
    paper over.
    """
    if report_path and Path(report_path).exists() and Path(report_path).stat().st_size > 0:
        try:
            return Graph().parse(report_path, format="turtle")
        except Exception as exc:
            raise RuntimeError(
                f"Jena wrote a report to {report_path}, but it could not be parsed as an "
                f"RDF/Turtle SHACL validation report: {exc}"
            ) from exc

    if output_text and any(marker in output_text for marker in ["@prefix", "PREFIX ", "sh:ValidationReport"]):
        graph = Graph()
        graph.parse(data=output_text, format="turtle")
        if report_path:
            graph.serialize(destination=report_path, format="turtle")
        return graph

    raise RuntimeError(
        "Jena validation produced no parseable RDF report: no report file was written to "
        f"{report_path!r}, and stdout was not RDF/Turtle. Configure --jena-command (or "
        "JENA_SHACL_COMMAND) so the report is written to the {output}/{report} path, or so "
        "the SHACL validation report is emitted as Turtle on stdout."
    )


def build_jena_command(command: str, data_path: str, shapes_path: str, report_path: str):
    command_template = command.strip()
    if "{" in command_template:
        rendered = command_template.format(
            data=data_path,
            shapes=shapes_path,
            output=report_path,
            report=report_path,
        )
        argv = shlex.split(rendered)
    else:
        argv = shlex.split(command_template)

    if not argv:
        raise ValueError("Jena command is empty")

    executable = argv[0]
    executable_name = Path(executable).name.lower()
    if executable_name == "shacl" and argv[1:2] != ["validate"]:
        argv = [executable, "validate", *argv[1:]]

    if any(token in argv for token in ["--data", "--shapes"]):
        return argv

    if executable_name == "shacl":
        argv.extend(["--data", data_path, "--shapes", shapes_path])
        return argv

    return [*argv, data_path, shapes_path, report_path]
