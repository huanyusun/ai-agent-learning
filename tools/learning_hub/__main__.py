"""python3 -m tools.learning_hub:统一课程中心命令行入口。

命令契约见 docs/superpowers/plans/2026-10-28-learning-hub.md 第 4 节。
退出码:成功 0;数据非法/程序错误/无法写结果 1;参数冲突 2。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "learning" / "data"
CATALOG_PATH = DATA_DIR / "catalog.json"
OBSERVATIONS_PATH = DATA_DIR / "observations.json"
CANDIDATES_PATH = DATA_DIR / "candidates.json"
SOURCES_PATH = DATA_DIR / "sources.json"
DEFAULT_RUNTIME_DIR = ".runtime/learning-hub"


def _load_json_or_fail(path: Path, required: bool) -> dict | None:
    if not path.exists():
        if required:
            print(f"错误:找不到 {path}", file=sys.stderr)
            raise SystemExit(1)
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        print(f"错误:{path} 不是合法 JSON:{exc}", file=sys.stderr)
        raise SystemExit(1)


def _load_catalog_or_fail() -> dict:
    catalog = _load_json_or_fail(CATALOG_PATH, required=True)
    assert catalog is not None
    return catalog


def _validate_or_fail(catalog: dict) -> None:
    from tools.learning_hub.catalog import validate_catalog

    errors = validate_catalog(catalog, REPO_ROOT)
    if errors:
        print(f"catalog 校验失败,共 {len(errors)} 项:")
        for error in errors:
            print(f"  - {error}")
        raise SystemExit(1)


def _cmd_validate(_args: argparse.Namespace) -> int:
    catalog = _load_catalog_or_fail()
    _validate_or_fail(catalog)
    print(
        "catalog 校验通过:"
        f"课程 {len(catalog['courses'])}、阶段 {len(catalog['stages'])}、周 {len(catalog['weeks'])}。"
    )
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    from tools.learning_hub.render import build_outputs, check_outputs, write_outputs

    catalog = _load_catalog_or_fail()
    _validate_or_fail(catalog)
    observations = _load_json_or_fail(OBSERVATIONS_PATH, required=False) or {}
    candidates = _load_json_or_fail(CANDIDATES_PATH, required=False) or {}
    outputs = build_outputs(catalog, observations, candidates)

    if args.check:
        drift = check_outputs(outputs, REPO_ROOT)
        if drift:
            print(f"检测到 {len(drift)} 处生成漂移:")
            for item in drift:
                print(f"  - {item}")
            print("请运行 python3 -m tools.learning_hub build 重新生成。")
            return 1
        print("生成文件与 catalog 一致,无漂移。")
        return 0

    write_outputs(outputs, REPO_ROOT)
    remaining = check_outputs(outputs, REPO_ROOT)
    if remaining:
        print("错误:写入后校验未通过:", file=sys.stderr)
        for item in remaining:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print(f"已生成 {len(outputs)} 个文件:")
    for rel in outputs:
        print(f"  - {rel}")
    return 0


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _build_fetch():
    """refresh/discover 使用的单次请求函数(不跟随重定向,便于逐跳检查)。"""
    from tools.learning_hub.fetch import _http_transport

    return _http_transport


def _print_refresh_summary(courses: dict) -> None:
    counts: dict[str, int] = {}
    for record in courses.values():
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    summary = ", ".join(f"{status} {count}" for status, count in sorted(counts.items()))
    anomalies = sum(count for status, count in counts.items() if status not in ("reachable", "redirected"))
    print(f"检查 {len(courses)} 门课程:{summary}。")
    if anomalies:
        print(f"其中异常/需关注 {anomalies} 项;退出码 0 不代表全部课程正常,详见记录与报告。")


def _cmd_refresh(args: argparse.Namespace) -> int:
    if args.apply and args.output_dir:
        print("参数冲突:--apply 与 --output-dir 不能同时使用。")
        return 2
    from tools.learning_hub.refresh import refresh_courses
    from tools.learning_hub.render import build_outputs, write_outputs

    catalog = _load_catalog_or_fail()
    _validate_or_fail(catalog)
    sources = _load_json_or_fail(SOURCES_PATH, required=False) or {}
    previous = _load_json_or_fail(OBSERVATIONS_PATH, required=False) or {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = "r" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)
    try:
        courses = refresh_courses(catalog, previous, fetch=_build_fetch(), now=now, run_id=run_id, sources=sources)
    except Exception as exc:  # 程序错误而非单站异常
        print(f"错误:refresh 执行失败:{exc}", file=sys.stderr)
        return 1
    payload = {"schema_version": 1, "last_run_at": now, "courses": courses}

    if args.apply:
        catalog_sha_before = _file_sha256(CATALOG_PATH)
        _atomic_write_json(OBSERVATIONS_PATH, payload)
        candidates = _load_json_or_fail(CANDIDATES_PATH, required=False) or {}
        outputs = build_outputs(catalog, payload, candidates)
        write_outputs(outputs, REPO_ROOT)
        if _file_sha256(CATALOG_PATH) != catalog_sha_before:
            print("错误:--apply 过程中 catalog 发生变化,已中止(观测数据已写入,请人工检查)。", file=sys.stderr)
            return 1
        print(f"已应用:写入 {OBSERVATIONS_PATH} 并重建 {len(outputs)} 个生成文件。")
    else:
        out_dir = Path(args.output_dir or DEFAULT_RUNTIME_DIR)
        out_path = out_dir / "observations.json"
        try:
            _atomic_write_json(out_path, payload)
        except OSError as exc:
            print(f"错误:无法写入结果 {out_path}:{exc}", file=sys.stderr)
            return 1
        print(f"结果已写入 {out_path}(未应用;使用 --apply 更新 tracked 数据并重建页面)。")
    _print_refresh_summary(courses)
    return 0


def _cmd_discover(args: argparse.Namespace) -> int:
    if args.apply and args.output_dir:
        print("参数冲突:--apply 与 --output-dir 不能同时使用。")
        return 2
    from tools.learning_hub.discover import discover_candidates
    from tools.learning_hub.render import build_outputs, write_outputs

    catalog = _load_catalog_or_fail()
    _validate_or_fail(catalog)
    sources = _load_json_or_fail(SOURCES_PATH, required=False) or {"schema_version": 1, "sources": [], "course_rules": {}}
    previous = _load_json_or_fail(CANDIDATES_PATH, required=False) or {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        payload = discover_candidates(catalog, sources, previous, fetch=_build_fetch(), now=now)
    except Exception as exc:
        print(f"错误:discover 执行失败:{exc}", file=sys.stderr)
        return 1

    if args.apply:
        catalog_sha_before = _file_sha256(CATALOG_PATH)
        _atomic_write_json(CANDIDATES_PATH, payload)
        observations = _load_json_or_fail(OBSERVATIONS_PATH, required=False) or {}
        outputs = build_outputs(catalog, observations, payload)
        write_outputs(outputs, REPO_ROOT)
        if _file_sha256(CATALOG_PATH) != catalog_sha_before:
            print("错误:--apply 过程中 catalog 发生变化,已中止。", file=sys.stderr)
            return 1
        print(f"已应用:写入 {CANDIDATES_PATH} 并重建 {len(outputs)} 个生成文件。")
    else:
        out_dir = Path(args.output_dir or DEFAULT_RUNTIME_DIR)
        out_path = out_dir / "candidates.json"
        try:
            _atomic_write_json(out_path, payload)
        except OSError as exc:
            print(f"错误:无法写入结果 {out_path}:{exc}", file=sys.stderr)
            return 1
        print(f"结果已写入 {out_path}(未应用;使用 --apply 更新 tracked 数据并重建页面)。")

    statuses: dict[str, int] = {}
    for item in payload.get("candidates") or []:
        statuses[item.get("status", "?")] = statuses.get(item.get("status", "?"), 0) + 1
    print(f"候选 {len(payload.get('candidates') or [])} 条:" + (", ".join(f"{k} {v}" for k, v in sorted(statuses.items())) or "无"))
    for source_id, check in (payload.get("source_checks") or {}).items():
        note = f"({check.get('note')})" if check.get("note") else ""
        print(f"  来源 {source_id}:{check.get('status')}{note}")
    failed = [sid for sid, check in (payload.get("source_checks") or {}).items() if check.get("status") != "ok"]
    if failed:
        print(f"注意:{len(failed)} 个来源异常(退出码 0 不代表全部来源正常)。")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m tools.learning_hub",
        description="统一课程中心:数据校验、生成、来源检查与候选发现",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="离线校验 catalog 数据结构")
    validate_parser.set_defaults(func=_cmd_validate)

    build_parser = subparsers.add_parser(
        "build", help="从 catalog 生成 Markdown 与静态页面"
    )
    build_parser.add_argument(
        "--check",
        action="store_true",
        help="只比较不写文件;一致退出 0,存在漂移退出 1",
    )
    build_parser.set_defaults(func=_cmd_build)

    refresh_parser = subparsers.add_parser(
        "refresh", help="检查课程链接与正文,生成观测数据(默认访问真实网络)"
    )
    refresh_parser.add_argument(
        "--apply",
        action="store_true",
        help="写入 learning/data/observations.json 并重建生成文件",
    )
    refresh_parser.add_argument(
        "--output-dir",
        help="结果输出目录(默认 .runtime/learning-hub);与 --apply 互斥",
    )
    refresh_parser.set_defaults(func=_cmd_refresh)

    discover_parser = subparsers.add_parser(
        "discover", help="从已配置官方目录发现候选课程(默认访问真实网络)"
    )
    discover_parser.add_argument(
        "--apply",
        action="store_true",
        help="写入 learning/data/candidates.json 并重建生成文件",
    )
    discover_parser.add_argument(
        "--output-dir",
        help="结果输出目录(默认 .runtime/learning-hub);与 --apply 互斥",
    )
    discover_parser.set_defaults(func=_cmd_discover)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
