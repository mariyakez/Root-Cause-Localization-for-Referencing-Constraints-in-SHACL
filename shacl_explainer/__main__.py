import sys
from .cli import parse_args, run

args = parse_args(sys.argv[1:])
run(
    args.data_path,
    args.shapes_path,
    fmt=args.format or args.legacy_format or "text",
    summary=args.summary,
    limit=args.limit,
    focus=args.focus,
    csv_path=args.csv_path,
    timing=args.timing,
    top=args.top,
    path=args.path,
    component=args.component,
    reference_path=args.reference_path,
    hints=args.hints,
    save_report=args.save_report,
    timing_csv=args.timing_csv,
    report_path=args.report_path,
    data_format=args.data_format,
    shapes_format=args.shapes_format,
    report_format=args.report_format,
    output=args.output,
    color=args.color,
)
