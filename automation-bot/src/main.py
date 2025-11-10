thonimport argparse
import sys
import time
from pathlib import Path

from automation.utils.config_loader import load_settings, load_credentials
from automation.utils.logger import get_logger
from automation.utils.proxy_manager import ProxyManager
from automation.tasks import ModerationTaskRunner
from automation.scheduler import Scheduler

def get_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "config").is_dir() and (parent / "src").is_dir():
            return parent
    # Fallback: assume src/ is directly under project root
    return current.parent.parent

def build_task_runner():
    root = get_project_root()
    settings = load_settings(root / "config" / "settings.yaml")
    credentials = load_credentials(root / "config" / "credentials.env")

    logger = get_logger()
    proxy_manager = ProxyManager(settings.get("proxies", {}), logger=logger)

    output_dir = root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    runner = ModerationTaskRunner(
        settings=settings,
        credentials=credentials,
        proxy_manager=proxy_manager,
        output_dir=output_dir,
        logger=logger,
    )
    return runner, settings

def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Discord Auto Moderator Automation Runner"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single moderation cycle and exit.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Override scheduler interval in seconds.",
    )
    return parser.parse_args(argv)

def run_once():
    runner, _ = build_task_runner()
    runner.run_moderation_cycle()

def run_with_scheduler(interval_override: int | None = None):
    runner, settings = build_task_runner()
    scheduler_cfg = settings.get("scheduler", {})
    enabled = scheduler_cfg.get("enabled", True)
    default_interval = int(scheduler_cfg.get("interval_seconds", 30))

    if not enabled and interval_override is None:
        runner.logger.warning("Scheduler is disabled in settings, running once instead.")
        runner.run_moderation_cycle()
        return

    interval = interval_override or default_interval
    runner.logger.info("Starting scheduler with interval=%s seconds", interval)

    scheduler = Scheduler(
        interval_seconds=interval,
        task=runner.run_moderation_cycle,
        logger=runner.logger,
    )
    scheduler.start()

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)

    try:
        if args.once:
            run_once()
        else:
            run_with_scheduler(args.interval)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        time.sleep(0.2)

if __name__ == "__main__":
    main()