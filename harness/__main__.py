import argparse
import json
import sys

from .agent import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trassa agent runner for qwen/qwen3.8-27b")
    parser.add_argument("-p", "--print", dest="prompt", help="task prompt; '-' reads stdin")
    parser.add_argument("--agent", help="path to agents/<id>")
    parser.add_argument("--output-format", choices=("json", "text"), default="json")
    parser.add_argument("--max-turns", type=int)
    parser.add_argument("--max-tokens", type=int, default=0)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--no-tools", action="store_true")
    args = parser.parse_args(argv)
    prompt = sys.stdin.read() if args.prompt in (None, "-") else args.prompt
    result = run(
        prompt,
        cwd=args.cwd,
        agent=args.agent,
        max_turns=args.max_turns,
        max_tokens=args.max_tokens,
        tools=[] if args.no_tools else None,
    )
    public = {key: value for key, value in result.items() if key != "messages"}
    if args.output_format == "json":
        json.dump(public, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(result["result"])
    return 0 if result["subtype"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
